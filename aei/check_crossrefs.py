#!/usr/bin/env python3
"""Fail the build when a cross-reference points at something that is not there.

Five times while drafting, a renumbering left a pointer behind: a section folded
into another, tables shifted, and prose or a replication map still named the old
number. Once it was in the repository README rather than the paper, where a
reviewer following the reproducibility claim would have hit it first.

This reads the built document, recovers the structure it actually has, and checks
that every "Section N", "Table N", "Figure N" and "Appendix X" in the paper and in
the replication maps resolves to something that exists. Exits 2 on any failure.

What it catches, exactly:
  - a reference to a section, table, figure or appendix that does not exist
  - a replication-map row whose subject is absent from the section it names, which
    is the failure that actually shipped: the map sent readers to Section 5 for the
    checkability coefficients after that section was folded into Section 4
  - a table or figure that is captioned but never referred to

What it does not catch: a prose reference pointing at a wrong but plausibly related
section. Scoring each section by vocabulary overlap and requiring the named one to
win was tried and produces false positives on correct text, because neighbouring
sections share vocabulary. Prose references are only checked for zero overlap. The
map rows are the ones that matter, since the map is what a reviewer follows.

  python3 analysis/check_crossrefs.py [paper.docx]
"""
import re, subprocess, sys, os, pathlib

DOC = sys.argv[1] if len(sys.argv) > 1 else "paper/liability-delegation-v4.docx"
MAPS = ["README.md", "sba-7a/aei/README.md", "sba-7a/README.md"]

if not os.path.exists(DOC):
    sys.exit(f"missing {DOC}")
text = subprocess.run(["pandoc", "-t", "plain", DOC],
                      capture_output=True, text=True).stdout
flat = re.sub(r"\s+", " ", text)

# --- what the document actually contains
sections = {int(n) for n in re.findall(r"(?m)^(\d{1,2})\.\s+[A-Z]", text) if int(n) <= 20}
appendices = set(re.findall(r"(?m)^Appendix ([A-C])\.", text))
tables = set(re.findall(r"(?m)^Table (B?\d+)\.", text))
figures = set(re.findall(r"(?m)^Figure (B?\d+)\.", text))

print(f"structure: sections {sorted(sections)}  appendices {sorted(appendices)}")
print(f"           tables {sorted(tables)}  figures {sorted(figures)}")

fails = []

def check(where, body, allow_tables=True):
    for n in sorted({int(x) for x in re.findall(r"\bSection (\d+)\b", body)}):
        if n not in sections:
            fails.append(f"{where}: 'Section {n}' but the paper has {sorted(sections)}")
    for a in sorted(set(re.findall(r"\bAppendix ([A-Z])\b", body))):
        if a not in appendices:
            fails.append(f"{where}: 'Appendix {a}' but the paper has {sorted(appendices)}")
    if not allow_tables:
        return
    for t in sorted(set(re.findall(r"\bTable (B?\d+)\b", body))):
        if t not in tables:
            fails.append(f"{where}: 'Table {t}' but the paper has {sorted(tables)}")
    for f in sorted(set(re.findall(r"\bFigure (B?\d+)\b", body))):
        if f not in figures:
            fails.append(f"{where}: 'Figure {f}' but the paper has {sorted(figures)}")

check("paper", flat)
for m in MAPS:
    if os.path.exists(m):
        check(m, pathlib.Path(m).read_text(encoding="utf-8"))
    else:
        print(f"  (skipped {m}, not present)")

# every table and figure that exists should be referred to somewhere
for t in sorted(tables):
    if not re.search(rf"\bTable {t}\b(?!\.)", flat):
        fails.append(f"paper: Table {t} is captioned but never referenced")
for f in sorted(figures):
    if not re.search(rf"\bFigure {f}\b(?!\.)", flat):
        fails.append(f"paper: Figure {f} is captioned but never referenced")

# --- a reference can resolve and still be wrong. The failure that shipped pointed at
# Section 5, which exists, but which no longer discusses checkability. So for every row
# of a replication map, check that the section it names actually contains the subject
# the row claims for it.
STOP = set("""about above across after against and are because been before being between
both could does during each from have into more most only other over should some such
than that their them then there these they this those through under until were what when
where which while will with would paper section table figure appendix across coefficients
checks reports gives shows lists every""".split())

def spans(txt):
    out, heads = {}, []
    for m in re.finditer(r"(?m)^(?:(\d{1,2})\.|Appendix ([A-C])\.)\s+\S", txt):
        heads.append((m.start(), m.group(1) or m.group(2)))
    for k, (pos, key) in enumerate(heads):
        end = heads[k+1][0] if k+1 < len(heads) else len(txt)
        out[key] = txt[pos:end].lower()
    return out

BODY = spans(text)
# captions, so a map row naming a table can be checked against what that table is
# keyed by kind as well as number: Table B1 and Figure B1 both exist
CAPTIONS = {(m.group(1), m.group(2)): m.group(3).lower()
            for m in re.finditer(r"(?m)^(Table|Figure) (B?\d+)\. (.+)$", text)}

def check_subject(where, body):
    for line in body.splitlines():
        if not line.startswith("|") or line.count("|") < 3:
            continue
        cell = line.split("|")[1].strip()
        refs = re.findall(r"\b(?:Section (\d{1,2})|Appendix ([A-C]))\b", cell)
        caps = re.findall(r"\b(Table|Figure) (B?\d+)\b", cell)
        if not refs and not caps:
            continue
        desc = re.sub(r"\b(?:Section \d{1,2}|Appendix [A-C]|Table B?\d+|Figure B?\d+)\b", " ", cell)
        words = {w for w in re.findall(r"[a-z]{6,}", desc.lower()) if w not in STOP}
        if not words:
            continue
        for sec, app in refs:
            key = sec or app
            span = BODY.get(key)
            if span is None:
                continue
            if not any(w in span for w in words):
                fails.append(f"{where}: row names {'Section' if sec else 'Appendix'} {key} "
                             f"but none of {sorted(words)[:4]} appears there")
        # A table reference is tighter than a section one: the caption is short and
        # specific, so a row naming the wrong table almost never overlaps its caption.
        for kind, t in caps:
            cap = CAPTIONS.get((kind, t))
            if cap is None:
                continue
            if not any(w in cap for w in words):
                fails.append(f"{where}: row names {kind} {t}, captioned "
                             f"\u201c{cap[:44]}\u201d, but claims {sorted(words)[:4]}")

def check_prose(where, body):
    # Paragraph scope, not sentence: a reference often sits mid-sentence with the
    # subject on either side of it, and splitting on punctuation drops half of it.
    prose = "\n".join(l for l in body.splitlines() if not l.startswith(("|", "#", "`")))
    for para in re.split(r"\n\s*\n", prose):
        refs = sorted({r for r in re.findall(r"\bSection (\d{1,2})\b", para)})
        if not refs:
            continue
        desc = re.sub(r"\bSection \d{1,2}\b", " ", para)
        words = {w for w in re.findall(r"[a-z]{6,}", desc.lower()) if w not in STOP}
        if len(words) < 3:
            continue
        # Weak guard only: flag a paragraph whose named section shares no vocabulary
        # with it at all. Requiring the named section to be the BEST match was tried
        # and rejected: on correct text it loses to sections that merely share more
        # words, which produced three false positives. See the limitation noted above.
        for sec in refs:
            span = BODY.get(sec)
            if span is None:
                continue
            if not any(w in span for w in words):
                fails.append(f"{where}: paragraph names Section {sec} but none of "
                             f"{sorted(words)[:5]} appears there")

for m in MAPS:
    if os.path.exists(m):
        body = pathlib.Path(m).read_text(encoding="utf-8")
        check_subject(m, body)
        check_prose(m, body)

print()
if fails:
    for f in fails: print("  FAIL", f)
    sys.exit(2)
print(f"all cross-references resolve, in the paper and in {len([m for m in MAPS if os.path.exists(m)])} replication maps")
