# Trap 3 — the `BusinessAge` vocabulary changes *inside* one file

**Reproduce:** `src/vocab.py` · **Test:** `tests/test_vocab.py`

The FY2010–2019 extract uses **two different vocabularies for the same variable**, and the switch
happens partway through the file rather than at a file boundary:

| graduated vocabulary | coarse vocabulary |
|---|---|
| `Startup, Loan Funds will Open Business` | `Startup, Loan Funds will Open Business` |
| `New, Less than 1 Year old` | `New Business or 2 years or less` |
| `Less than 3 years old but at least 2` | `Existing or more than 2 years old` |
| `Less than 4 years old but at least 3` | |
| `Less than 5 years old but at least 4` | |
| `Existing, 5 or more years` | |

`Startup, Loan Funds will Open Business` is the **only** label the two share. That is what makes
this dangerous rather than merely annoying: a filter written against one vocabulary still matches
on `Startup`, still returns a plausible-looking number, and silently drops everything else.

Mine did. It encoded only the labels I had seen in the FY2020+ file and dropped **42,936** loans
labelled `New, Less than 1 Year old`. The consequences:

| | buggy | correct |
|---|---|---|
| greenfield share | 14.8% | **24.8%** |
| annual cohort | 3,068 | **6,258** |
| charge-off rate | 8.92% | **9.24%** |

A claim in an earlier draft — that a particular ranking inverted — did not survive the correction.
9.24% and 9.46% are not distinguishable.

Note also that **there is no `[1,2)` year band in either vocabulary.** The graduated one jumps from
"less than 1 year" to "at least 2"; the coarse one lumps everything under 2 years together. Any
attempt to construct a consistent "1–2 years old" category across the file is constructing
something that does not exist in the data.

`vocab.harmonise()` maps both vocabularies onto one set of labels; `vocab.unmapped()` returns any
label it does not recognise, and the test asserts that list is empty against the raw CSV. If SBA
introduces a third vocabulary, that test fails rather than silently bucketing it.

## And a caveat on the variable itself

**9.2% of FY2010–2019 loans have no `BusinessAge` answer at all** — the raw code is literally
`"Unanswered"` — and the share rises from 9.1% in FY2010 to **18.7% in FY2019** `[V1]`. That is not
a crosswalk gap; the crosswalk is complete. It is genuine non-response, doubling across the decade
and concentrated in exactly the recent years most analyses focus on. Every share computed on this
variable rests on an eroding base.
