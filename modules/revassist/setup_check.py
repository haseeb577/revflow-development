import os
import subprocess
import sys
import logging
import time
from pathlib import Path

# Initialize logger
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Define the paths
REPORT_DIR = '/root/revhome_assessment_engine_v2/reports'
API_PY_PATH = '/root/traefik/backend/api.py'
UVICORN_LOG = '/root/revhome_assessment_engine_v2/uvicorn.log'

def check_and_create_report_dir():
    """Ensure REPORT_DIR exists, and create it if not."""
    if not os.path.exists(REPORT_DIR):
        logger.error(f"REPORT_DIR does not exist at: {REPORT_DIR}. Creating it now.")
        os.makedirs(REPORT_DIR)
    else:
        logger.info(f"REPORT_DIR exists at: {REPORT_DIR}")

def check_api_file():
    """Ensure api.py file exists and is properly configured."""
    if not os.path.exists(API_PY_PATH):
        logger.error(f"api.py not found at: {API_PY_PATH}")
        sys.exit(1)
    else:
        logger.info(f"api.py found at: {API_PY_PATH}")

def check_virtualenv():
    """Check if the virtual environment is active."""
    if 'VIRTUAL_ENV' not in os.environ:
        logger.error("Virtual environment is not active. Please activate your virtual environment.")
        sys.exit(1)
    else:
        logger.info(f"Virtual environment is active: {os.environ['VIRTUAL_ENV']}")

def install_requirements():
    """Install required packages from requirements.txt."""
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        logger.info("Required packages are installed.")
    except subprocess.CalledProcessError:
        logger.error("Error installing required packages.")
        sys.exit(1)

def check_dependencies():
    """Check if backend services (like databases or external APIs) are running."""
    # You can customize this based on your dependencies (e.g., database or external services)
    logger.info("Checking if all necessary backend dependencies are running...")
    # Placeholder check for database (example command, change based on actual service)
    try:
        subprocess.check_call(['systemctl', 'is-active', '--quiet', 'postgresql'])
        logger.info("Database service is running.")
    except subprocess.CalledProcessError:
        logger.warning("Database service is not running. Please check your database.")

def start_uvicorn():
    """Start Uvicorn with the proper configuration."""
    logger.info("Starting Uvicorn server...")
    command = ['uvicorn', 'revhome_api:app', '--host', '0.0.0.0', '--port', '5000', '--reload']
    try:
        subprocess.Popen(command)
        logger.info("Uvicorn server started successfully.")
    except Exception as e:
        logger.error(f"Error starting Uvicorn server: {str(e)}")
        sys.exit(1)

def check_port_and_firewall():
    """Ensure port 5000 is open and no firewall is blocking the server."""
    try:
        subprocess.check_call(['sudo', 'ufw', 'allow', '5000'])
        logger.info("Port 5000 opened in firewall.")
    except subprocess.CalledProcessError:
        logger.warning("Could not open port 5000 in the firewall.")
    
    # Check if the port is being used
    try:
        subprocess.check_call(['sudo', 'lsof', '-i', ':5000'])
        logger.info("Port 5000 is in use.")
    except subprocess.CalledProcessError:
        logger.warning("Port 5000 is not in use, server may not have started.")

def restart_uvicorn_if_needed():
    """Check if Uvicorn is running, and restart if necessary."""
    logger.info("Checking if Uvicorn is running...")
    try:
        result = subprocess.check_output(['ps', 'aux', '|', 'grep', 'uvicorn'])
        if 'uvicorn' in str(result):
            logger.info("Uvicorn is already running.")
        else:
            logger.info("Uvicorn is not running. Restarting Uvicorn...")
            start_uvicorn()
    except subprocess.CalledProcessError:
        logger.error("Error checking Uvicorn process.")
        sys.exit(1)

def main():
    """Run all checks and fixes."""
    logger.info("Starting setup checks...")
    check_and_create_report_dir()
    check_api_file()
    check_virtualenv()
    install_requirements()
    check_dependencies()
    start_uvicorn()
    check_port_and_firewall()
    restart_uvicorn_if_needed()
    logger.info("All checks and setup tasks completed successfully.")

if __name__ == '__main__':
    main()
