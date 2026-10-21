import importlib


def test_package_imports() -> None:
    assert importlib.import_module("magaza_core").__version__ == "0.1.0"
