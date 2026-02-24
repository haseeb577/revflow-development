import importlib.util
from pathlib import Path
from fastapi.testclient import TestClient

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SERVER_PY = PROJECT_ROOT / "server.py"

def load_app():
    spec = importlib.util.spec_from_file_location("revhome_server", str(SERVER_PY))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return getattr(module, "app")

def test_health_endpoint():
    app = load_app()
    client = TestClient(app)
    r = client.get("/health")
    assert r.status_code == 200
    data = r.json()
    assert "status" in data and data["status"] == "ok"
