import pytest, pathlib
from src.build import load

ROOT = pathlib.Path(__file__).resolve().parents[1]
need = pytest.mark.skipif(not (ROOT/"data/panel_fy2010_2019.parquet").exists(),
                          reason="panel not built - run `make fast`")

@pytest.fixture(scope="session")
def old(): return load()

@pytest.fixture(scope="session")
def new(): return load("fy2020_present")
