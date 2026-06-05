def test_main_module_imports_without_error():
    import importlib
    mod = importlib.import_module("engine.__main__")   # must not raise ImportError
    assert hasattr(mod, "main")
