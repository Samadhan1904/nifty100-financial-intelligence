"""
Day 1 sanity check.
Run: pytest tests/test_setup.py -v
"""

import sys
import importlib


def test_python_version():
    assert sys.version_info >= (3, 10), (
        f"Need Python 3.10+, got {sys.version_info.major}.{sys.version_info.minor}"
    )


def test_all_libraries_installed():
    libraries = [
        "pandas", "numpy", "openpyxl",
        "scipy", "sklearn",
        "matplotlib", "plotly",
        "streamlit",
        "fastapi", "uvicorn",
        "reportlab", "nltk",
        "dotenv", "yaml",
        "requests", "pytest",
    ]
    missing = []
    for lib in libraries:
        try:
            importlib.import_module(lib)
        except ImportError:
            missing.append(lib)

    assert not missing, (
        f"Missing: {missing}\nFix: pip install -r requirements.txt"
    )


def test_config_loads():
    from src.config import DB_PATH, RAW_DATA_PATH, OUTPUT_PATH, REPORTS_PATH
    assert DB_PATH is not None
    assert RAW_DATA_PATH is not None
    assert OUTPUT_PATH is not None
    assert REPORTS_PATH is not None


def test_output_directories_exist():
    from src.config import OUTPUT_PATH, REPORTS_PATH
    assert OUTPUT_PATH.exists(),                   "output/ missing"
    assert REPORTS_PATH.exists(),                  "reports/ missing"
    assert (REPORTS_PATH / "tearsheets").exists(), "reports/tearsheets/ missing"
    assert (REPORTS_PATH / "sector").exists(),     "reports/sector/ missing"
    