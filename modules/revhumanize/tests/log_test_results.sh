#!/bin/bash

TIMESTAMP=$(date +"%Y-%m-%d %H:%M:%S")
LOG_FILE="/opt/revflow-humanization-pipeline/tests/test_results.log"

echo "[$TIMESTAMP] Running test suite..." | tee -a $LOG_FILE

./run_all_tests.sh 2>&1 | tee -a $LOG_FILE

echo "[$TIMESTAMP] Test suite completed" | tee -a $LOG_FILE
echo "---" | tee -a $LOG_FILE
