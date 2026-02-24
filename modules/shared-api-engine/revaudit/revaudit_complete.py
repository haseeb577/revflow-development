#!/bin/bash
# RevAudit™ CLI

case "$1" in
    start)
        echo "Starting RevAudit™..."
        systemctl start revaudit-backend
        systemctl start revaudit-frontend
        echo "✓ Backend running on http://localhost:8950"
        echo "✓ Frontend running on http://localhost:3100"
        ;;
    stop)
        echo "Stopping RevAudit™..."
        systemctl stop revaudit-backend
        systemctl stop revaudit-frontend
        ;;
    restart)
        echo "Restarting RevAudit™..."
        systemctl restart revaudit-backend
        systemctl restart revaudit-frontend
        ;;
    status)
        echo "=== RevAudit™ Status ==="
        systemctl status revaudit-backend --no-pager
        systemctl status revaudit-frontend --no-pager
        ;;
    logs)
        case "$2" in
            backend)
                tail -f /opt/revaudit/logs/backend.log
                ;;
            frontend)
                tail -f /opt/revaudit/logs/frontend.log
                ;;
            *)
                tail -f /opt/revaudit/logs/*.log
                ;;
        esac
        ;;
    run)
        echo "Running manual audit..."
        curl -X POST http://localhost:8950/audit/run
        ;;
    *)
        echo "RevAudit™ v4.0 - Usage:"
        echo "  revaudit start      - Start all services"
        echo "  revaudit stop       - Stop all services"
        echo "  revaudit restart    - Restart all services"
        echo "  revaudit status     - Show service status"
        echo "  revaudit logs       - View all logs"
        echo "  revaudit logs backend   - View backend logs"
        echo "  revaudit logs frontend  - View frontend logs"
        echo "  revaudit run        - Run manual audit"
        echo ""
        echo "Dashboard: http://localhost:3100"
        echo "API: http://localhost:8950"
        ;;
esac
