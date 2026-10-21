import importlib


def test_package_imports() -> None:
    assert importlib.import_module("magaza_jobs").__version__ == "0.1.0"
