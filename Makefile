.PHONY: quick fast all test clean data figures
PY := python3

quick:           ## ranking, incidence, break-even from the committed panel (~45s)
	$(PY) -m src.ranking
	$(PY) -m src.incidence
	$(PY) -m src.breakeven

fast: quick      ## everything, including the three backfits in trap 1 (~6 min)
	$(PY) -m src.lender

figures:         ## regenerate the two figures in output/figures
	$(PY) -m src.figures

all: data        ## re-download the FOIA extracts, rebuild the panel, then run everything
	$(PY) -m src.build
	$(MAKE) fast

data:
	$(PY) data/get_data.py

test:            ## re-derive every tagged claim (22 tests, ~15s)
	$(PY) -m pytest tests -q

clean:
	rm -rf output/tables/*.csv __pycache__ src/__pycache__ tests/__pycache__ .pytest_cache
