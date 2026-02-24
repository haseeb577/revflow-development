#!/usr/bin/env python3
import os
import sys
import subprocess
import logging
import time
import shlex
from pathlib import Path
from typing import Optional

# ------------- CONFIG (adjust to your paths) -------------
REPORT_DIR = Path("/root/revhome_assessment_engine_v2/reports")
PROJECT_ROOT = Path("/root/revhome_assessment_engine_v2")
REQUIREMENTS = PROJECT_ROOT / "requirements.txt"
API_PY_PATH = Path("/root/traefik/backend/api.py")  # if Traefik/Nginx proxies to Uvicorn behind this
UVICORN_LOG = PROJECT_ROOT / "uvicorn.log"
PYTHON_MIN_VER = (3, 10)
UVICORN_HOST = "0.0.0.0"
UVICORN_PORT = 5000
UVICORN_APP = "revhome_api:app"  # change if needed e.g., "backend.api:app"
USE_SYSTEMD = False  # set to True if you manage uvicorn via systemd unit
SYSTEMD_SERVICE = "uvicorn.service"  # your service name if using systemd
# ---------------------------------------------------------

def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(UVICORN_LOG, mode="a", encoding="utf-8"),
        ],
    )
    logging.info("Logger initialized. Writing to %s", UVICORN_LOG)

def fail(msg: str, code: int = 1):
    logging.error(msg)
    sys.exit(code)

def warn(msg: str):
    logging.warning(msg)

def run(cmd: str, check: bool = True, capture_output: bool = True, shell: bool = False) -> subprocess.CompletedProcess:
    logging.debug("Running: %s", cmd)
    if shell:
        result = subprocess.run(cmd, shell=True, text=True,
                                capture_output=capture_output, check=False)
    else:
        result = subprocess.run(shlex.split(cmd), text=True,
                                capture_output=capture_output, check=False)
    if check and result.returncode != 0:
        logging.error("Command failed (%s): %s", result.returncode, cmd)
        logging.error("stdout: %s", result.stdout.strip())
        logging.error("stderr: %s", result.stderr.strip())
        raise subprocess.CalledProcessError(result.returncode, cmd, result.stdout, result.stderr)
    return result

def ensure_dirs():
    if not REPORT_DIR.exists():
        logging.info("Creating REPORT_DIR: %s", REPORT_DIR)
        REPORT_DIR.mkdir(parents=True, exist_ok=True)
    else:
        logging.info("REPORT_DIR exists: %s", REPORT_DIR)
    if not PROJECT_ROOT.exists():
        fail(f"PROJECT_ROOT not found: {PROJECT_ROOT}. Fix CONFIG paths.")

def check_python_version():
    if sys.version_info < PYTHON_MIN_VER:
        fail(f"Python {PYTHON_MIN_VER[0]}.{PYTHON_MIN_VER[1]}+ required. Current: {sys.version.split()[0]}")
    logging.info("Python version OK: %s", sys.version.split()[0])

def check_venv():
    venv = os.environ.get("VIRTUAL_ENV")
    if not venv:
        fail("Virtual environment is NOT active. Activate it first: `source venv/bin/activate` (or your path).")
    logging.info("Virtual environment active: %s", venv)

def ensure_pip_and_wheel():
    try:
        run(f"{sys.executable} -m pip --version")
        run(f"{sys.executable} -m pip install --upgrade pip wheel setuptools", check=True)
        logging.info("pip/wheel/setuptools are present and up to date.")
    except subprocess.CalledProcessError:
        fail("Failed to prepare pip/wheel/setuptools.")

def install_requirements():
    if REQUIREMENTS.exists():
        logging.info("Installing requirements from %s", REQUIREMENTS)
        try:
            run(f"{sys.executable} -m pip install -r {REQUIREMENTS}", check=True)
            logging.info("Requirements installed.")
        except subprocess.CalledProcessError:
            fail("Error installing required packages from requirements.txt")
    else:
        warn(f"No requirements.txt at {REQUIREMENTS}. Skipping dependency install.")

def check_api_file():
    if not API_PY_PATH.exists():
        warn(f"api.py not found at: {API_PY_PATH}. If your app entry is elsewhere, update UVICORN_APP.")
    else:
        logging.info("api.py found at: %s", API_PY_PATH)

def python_import_test(module_app: str) -> bool:
    # Verify the module:app can import and expose `app`
    if ":" not in module_app:
        warn(f"UVICORN_APP '{module_app}' missing ':app' pattern? Expected 'module:app'")
        return False
    module, appname = module_app.split(":", 1)
    code = f"import importlib; m=importlib.import_module('{module}'); assert hasattr(m,'{appname}')"
    result = run(f'{sys.executable} -c "{code}"', check=False)
    if result.returncode == 0:
        logging.info("Import check OK for %s", module_app)
        return True
    logging.error("Import check FAILED for %s\nstdout: %s\nstderr: %s",
                  module_app, result.stdout, result.stderr)
    return False

def check_backend_dependencies():
    # Example: PostgreSQL; adapt as needed or add your own checks (Redis, S3 creds, API keys)
    # Only check if systemctl exists
    systemctl = run("which systemctl", check=False)
    if systemctl.returncode == 0:
        res = run("systemctl is-active --quiet postgresql", check=False)
        if res.returncode == 0:
            logging.info("PostgreSQL service is active.")
        else:
            warn("PostgreSQL not active (if you use it). If you rely on managed DB, ignore this.")
    else:
        logging.info("systemctl not found; skipping service checks.")

def port_in_use(port: int) -> bool:
    # prefer ss if available, fallback to lsof
    if run("which ss", check=False).returncode == 0:
        res = run(f"ss -ltn '( sport = :{port} )'", check=False)
        return res.returncode == 0 and str(port) in res.stdout
    elif run("which lsof", check=False).returncode == 0:
        res = run(f"lsof -i :{port}", check=False)
        return res.returncode == 0
    else:
        warn("Neither ss nor lsof available to check ports.")
        return False

def open_firewall_port_if_possible(port: int):
    # Only if ufw exists and is active
    if run("which ufw", check=False).returncode != 0:
        logging.info("ufw not installed; skipping firewall changes.")
        return
    status = run("ufw status", check=False)
    if "inactive" in (status.stdout or "").lower():
        logging.info("ufw inactive; no firewall rule needed.")
        return
    logging.info("Attempting to allow port %d via ufw.", port)
    run(f"sudo ufw allow {port}", check=False)

def uvicorn_running() -> bool:
    # Detect uvicorn by pgrep
    if run("which pgrep", check=False).returncode == 0:
        res = run("pgrep -f uvicorn", check=False)
        return res.returncode == 0
    # fallback: ps filtering safely
    res = run("ps aux", check=False)
    return "uvicorn" in res.stdout

def start_uvicorn_foreground():
    cmd = f"uvicorn {UVICORN_APP} --host {UVICORN_HOST} --port {UVICORN_PORT} --log-level info"
    logging.info("Starting uvicorn in background: %s", cmd)
    # Use nohup so it persists after shell exits; write both stdout/stderr to log
    bg = f"nohup {cmd} >> {shlex.quote(str(UVICORN_LOG))} 2>&1 & echo $!"
    res = run(bg, shell=True, check=False)
    if res.returncode == 0:
        logging.info("Uvicorn started (nohup). Check log: %s", UVICORN_LOG)
    else:
        fail(f"Failed to start uvicorn. stderr: {res.stderr}")

def systemd_restart():
    logging.info("Restarting systemd service: %s", SYSTEMD_SERVICE)
    res = run(f"sudo systemctl restart {SYSTEMD_SERVICE}", check=False)
    if res.returncode != 0:
        fail(f"Failed to restart {SYSTEMD_SERVICE}. stderr: {res.stderr}")
    # Wait and confirm
    time.sleep(2)
    status = run(f"systemctl is-active {SYSTEMD_SERVICE}", check=False)
    if "active" in status.stdout:
        logging.info("%s is active.", SYSTEMD_SERVICE)
    else:
        fail(f"{SYSTEMD_SERVICE} is not active. Check `journalctl -u {SYSTEMD_SERVICE} -xe`")

def healthcheck(host: str = "127.0.0.1", port: int = UVICORN_PORT, path: str = "/health"):
    import http.client
    conn = None
    try:
        conn = http.client.HTTPConnection(host, port, timeout=3)
        conn.request("GET", path)
        resp = conn.getresponse()
        logging.info("Healthcheck %s:%d%s -> %d", host, port, path, resp.status)
        return resp.status < 500
    except Exception as e:
        warn(f"Healthcheck failed: {e}")
        return False
    finally:
        if conn:
            conn.close()

def main():
    setup_logging()
    logging.info("Starting VPS doctor...")
    ensure_dirs()
    check_python_version()
    check_venv()
    ensure_pip_and_wheel()
    install_requirements()
    check_api_file()

    if not python_import_test(UVICORN_APP):
        fail("Import test failed for UVICORN_APP. Fix the module:app target or PYTHONPATH.")

    check_backend_dependencies()
    open_firewall_port_if_possible(UVICORN_PORT)

    # Start or restart uvicorn
    if USE_SYSTEMD:
        systemd_restart()
    else:
        if uvicorn_running():
            logging.info("Uvicorn appears to be running already.")
        else:
            start_uvicorn_foreground()

    # Give server a moment to bind
    time.sleep(1.5)

    # Verify port and basic reachability
    if port_in_use(UVICORN_PORT):
        logging.info("Port %d is listening.", UVICORN_PORT)
    else:
        warn(f"Port {UVICORN_PORT} not listening. Check logs: {UVICORN_LOG}")

    # Optional healthcheck (adjust path)
    health_ok = healthcheck(host="127.0.0.1", port=UVICORN_PORT, path="/health")
    if not health_ok:
        warn("Healthcheck did not succeed. If you have no /health endpoint, ignore or change path.")

    logging.info("All checks completed.")

if __name__ == "__main__":
    main()
