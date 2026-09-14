from __future__ import annotations

import importlib
import importlib.util
import sys


def _lazy_import(name: str):
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.find_spec(name)
    if spec is None:
        raise ImportError(f"Module {name!r} is not installed.")
    loader = importlib.util.LazyLoader(spec.loader)
    spec.loader = loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    loader.exec_module(module)
    return module
