#!/bin/bash
# Iterative Dependency Installer
# Created: 2026-02-04 10:30:00

echo "========================================================================"
echo "ITERATIVE DEPENDENCY INSTALLER - AUTO-FIXING MISSING MODULES"
echo "========================================================================"
echo ""

cd /opt/revpublish/backend

MAX_ITERATIONS=20
iteration=0

while [ $iteration -lt $MAX_ITERATIONS ]; do
    iteration=$((iteration + 1))
    echo "=== ITERATION $iteration/$MAX_ITERATIONS ==="
    echo ""
    
    # Stop service first
    systemctl stop revpublish-backend 2>/dev/null
    sleep 1
    systemctl reset-failed revpublish-backend 2>/dev/null
    
    # Try to start service
    echo "Attempting to start service..."
    systemctl start revpublish-backend
    sleep 3
    
    # Check if it's running
    if systemctl is-active --quiet revpublish-backend; then
        echo ""
        echo "🎉🎉🎉🎉🎉🎉🎉🎉🎉🎉🎉🎉🎉🎉🎉🎉🎉🎉🎉🎉🎉🎉🎉"
        echo "🎉                                                 🎉"
        echo "🎉     SERVICE IS RUNNING SUCCESSFULLY!!!         🎉"
        echo "🎉                                                 🎉"
        echo "🎉🎉🎉🎉🎉🎉🎉🎉🎉🎉🎉🎉🎉🎉🎉🎉🎉🎉🎉🎉🎉🎉🎉"
        echo ""
        systemctl status revpublish-backend --no-pager | head -15
        echo ""
        echo "Testing API endpoint..."
        sleep 2
        curl -s http://localhost:8550/ | head -5 || echo "(Root endpoint check complete)"
        echo ""
        echo "✅ All dependencies installed!"
        echo "✅ Service is operational!"
        echo ""
        echo "Creating requirements.txt for future use..."
        venv/bin/pip freeze > requirements.txt
        echo "✅ requirements.txt created with $(wc -l < requirements.txt) packages"
        echo ""
        exit 0
    fi
    
    # Service failed - check for missing module
    echo "Service not running - checking error..."
    
    # Get the latest error
    error_log=$(journalctl -u revpublish-backend --since "10 seconds ago" -n 50 --no-pager)
    
    # Look for ModuleNotFoundError
    if echo "$error_log" | grep -q "ModuleNotFoundError: No module named"; then
        # Extract the module name
        missing_module=$(echo "$error_log" | grep "ModuleNotFoundError: No module named" | tail -1 | sed -n "s/.*No module named '\([^']*\)'.*/\1/p")
        
        if [ -z "$missing_module" ]; then
            echo "❌ Could not extract module name from error"
            echo ""
            echo "Full error log:"
            echo "$error_log" | tail -20
            echo ""
            exit 1
        fi
        
        echo "❌ Missing module detected: $missing_module"
        echo ""
        
        # Install the missing module
        echo "Installing $missing_module..."
        if venv/bin/pip install --no-cache-dir "$missing_module"; then
            echo "✅ $missing_module installed successfully"
            echo ""
        else
            echo "❌ Failed to install $missing_module"
            echo ""
            echo "Trying with common package name variations..."
            
            # Try common variations
            case "$missing_module" in
                "bs4")
                    venv/bin/pip install --no-cache-dir beautifulsoup4
                    ;;
                "PIL")
                    venv/bin/pip install --no-cache-dir Pillow
                    ;;
                "cv2")
                    venv/bin/pip install --no-cache-dir opencv-python
                    ;;
                "yaml")
                    venv/bin/pip install --no-cache-dir PyYAML
                    ;;
                *)
                    echo "No known variation for $missing_module"
                    exit 1
                    ;;
            esac
        fi
    elif echo "$error_log" | grep -q "ImportError"; then
        echo "❌ Import error detected (not a missing module)"
        echo ""
        echo "Error log:"
        echo "$error_log" | grep -A 5 "ImportError" | tail -10
        echo ""
        exit 1
    else
        echo "❌ Unknown error - not a missing module"
        echo ""
        echo "Last 20 lines of error log:"
        echo "$error_log" | tail -20
        echo ""
        exit 1
    fi
    
    echo ""
done

echo ""
echo "❌ Maximum iterations ($MAX_ITERATIONS) reached!"
echo "❌ Service still has issues"
echo ""
echo "This might indicate a deeper problem beyond missing dependencies."
echo "Check the logs manually:"
echo "  journalctl -u revpublish-backend -n 50"
echo ""
exit 1
