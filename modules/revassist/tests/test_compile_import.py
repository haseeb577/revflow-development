import py_compile
import importlib.util
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SERVER_PY = PROJECT_ROOT / "server.py"

def test_compiles():
    py_compile.compile(str(SERVER_PY), doraise=True)

def test_imports_app():
    spec = importlib.util.spec_from_file_location("revhome_server", str(SERVER_PY))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert hasattr(module, "app"), "server.py must export 'app' (FastAPI app)"
