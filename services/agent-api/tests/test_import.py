import importlib


def test_package_imports() -> None:
    assert importlib.import_module("agent_api").__version__ == "0.1.0"
