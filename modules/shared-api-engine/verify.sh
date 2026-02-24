#!/bin/bash
echo "=== VERIFICATION ==="
echo "1. Hardcoding: $(grep -c '^REV.*_API=' /opt/shared-api-engine/.env || echo 0) endpoints (should be 0)"
echo "2. Gateway: $(grep -c 'REVCORE_GATEWAY' /opt/shared-api-engine/.env) lines (should be 1+)"
echo "3. Client: $(test -f /opt/shared-api-engine/revflow_client_clean.py && echo 'OK' || echo 'MISSING')"
echo "4. Gateway file: $(test -f /opt/revcore/backend/app/routers/gateway.py && echo 'OK' || echo 'MISSING')"
python3 -c "import sys; sys.path.insert(0, '/opt/shared-api-engine'); from revflow_client import get_revflow_client; print('5. Client works: OK')" 2>/dev/null || echo "5. Client works: FAILED"
echo "=== IF ALL ARE OK, YOU'RE DONE! SLEEP! ==="
