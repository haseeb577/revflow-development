"""
server.py - shim for tests that expect server.py

Loads revhome_api.py by absolute path, ensuring the repo root is in sys.path
so that relative imports like 'from app.health import ...' work correctly.
"""
from importlib import util
from pathlib import Path
import sys

BASE = Path(__file__).resolve().parent
ENTRYPOINT = BASE / "revhome_api.py"

# Add repo root to sys.path so 'app' package can be imported
if str(BASE) not in sys.path:
    sys.path.insert(0, str(BASE))

spec = util.spec_from_file_location("revhome_api_module", str(ENTRYPOINT))
module = util.module_from_spec(spec)
spec.loader.exec_module(module)
app = module.app

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="0.0.0.0", port=8081)
