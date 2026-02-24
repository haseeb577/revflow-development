import os
import sys
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Define the REPORT_DIR (Change this if it's not set)
REPORT_DIR = '/root/revhome_assessment_engine_v2/reports'  # Change this path if needed

# Function to check if REPORT_DIR exists and is accessible
def check_report_dir():
    # Ensure REPORT_DIR exists
    if not os.path.isdir(REPORT_DIR):
        logging.error(f"REPORT_DIR does not exist at: {REPORT_DIR}. Please create it.")
        sys.exit(1)
    else:
        logging.info(f"REPORT_DIR exists at: {REPORT_DIR}")
    
    # Ensure we have write access to REPORT_DIR
    try:
        test_file = os.path.join(REPORT_DIR, "test_write_access.txt")
        with open(test_file, 'w') as f:
            f.write("Test")
        os.remove(test_file)  # Clean up the test file
    except Exception as e:
        logging.error(f"Unable to write to REPORT_DIR: {e}")
        sys.exit(1)

# Function to check if the necessary files exist in the REPORT_DIR
def check_files():
    # Check api.py file in the backend folder
    api_file_path = '/root/traefik/backend/api.py'  # Adjust path if needed
    if os.path.isfile(api_file_path):
        logging.info(f"api.py found at: {api_file_path}")
    else:
        logging.error(f"api.py not found at: {api_file_path}")
        sys.exit(1)
    
    # Check if the necessary report files exist in REPORT_DIR
    report_file = os.path.join(REPORT_DIR, "sample_report.docx")  # Adjust for actual report files
    if os.path.isfile(report_file):
        logging.info(f"Sample report file found at: {report_file}")
    else:
        logging.error(f"Sample report file not found at: {report_file}")
        sys.exit(1)

# Function to check if necessary environment variables or paths are set up correctly
def check_environment():
    # Check Python environment
    python_version = sys.version
    logging.info(f"Python version: {python_version}")
    
    # Check if the virtual environment is active (if using venv)
    if os.getenv("VIRTUAL_ENV"):
        logging.info(f"Virtual environment is active: {os.getenv('VIRTUAL_ENV')}")
    else:
        logging.error("Virtual environment is not active.")
        sys.exit(1)
    
    # Check if necessary packages are installed (from requirements.txt)
    try:
        import fastapi
        import uvicorn
        import pydantic
        import requests
        logging.info("Required packages are installed.")
    except ImportError as e:
        logging.error(f"Missing required package: {e.name}")
        sys.exit(1)

# Function to check the configuration and set up for report generation
def check_report_generation():
    # Check that REPORT_DIR is correctly set and available
    check_report_dir()
    
    # Check that the necessary files are in place
    check_files()

# Run all checks
def run_checks():
    logging.info("Starting setup checks...")
    try:
        check_report_generation()  # Check REPORT_DIR and necessary files
        check_environment()  # Check environment and packages
        logging.info("All checks passed successfully.")
    except Exception as e:
        logging.error(f"Error during checks: {e}")
        sys.exit(1)

if __name__ == "__main__":
    run_checks()
