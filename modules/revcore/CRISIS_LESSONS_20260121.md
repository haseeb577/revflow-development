# RevFlow OS™ - Crisis Lessons (Jan 20-21, 2026)

## What Happened

On Jan 20-21, 2026, the VPS experienced a catastrophic CPU crisis:
- **Load average hit 70+** (normal is <2)
- **Hostinger throttled to 90% steal time** (couldn't SSH)
- **Root cause:** smarketsherpa-platform in infinite restart loop

## Root Cause Analysis

1. **smarketsherpa-platform** started failing due to PostgreSQL auth error
2. Code used `POSTGRES_*` env vars, but only `DB_*` vars were populated
3. `POSTGRES_PASSWORD` was empty → `fe_sendauth: no password supplied`
4. Systemd `Restart=on-failure` kept restarting every 10 seconds
5. Each restart consumed 2-3 CPU seconds
6. Restart loop created 70+ load → Hostinger throttled

## Fix Applied

1. Added `POSTGRES_*` variables to `/opt/shared-api-engine/.env`
2. Enabled password auth in `/etc/postgresql/16/main/pg_hba.conf`
3. Set postgres password: `revflow2026`
4. Fixed file permissions for postgres user
5. Masked service to stop loop: `systemctl mask smarketsherpa-platform`

## Patches Applied to Existing Modules

### RevGuard v3 → v3.1
- Added restart loop detection (3+ restarts in 5 min = loop)
- Added CPU steal time monitoring
- Added emergency mask capability
- Added smart restart with pre-flight checks
- Added database connectivity validation

### RevCORE database-discovery.py
- Now actually TESTS database connection (not just checks vars exist)
- Validates BOTH `DB_*` and `POSTGRES_*` variables
- Reports specific missing variables

### New: crisis-monitor.py
- Lightweight script for cron/timer
- Monitors steal time and load average
- Logs warnings before crisis becomes emergency

## New API Endpoints (RevGuard v3.1)

```bash
# Check steal time
curl http://localhost:8960/system/steal-time

# Check restart loop status
curl http://localhost:8960/service/smarketsherpa-platform/restart-loop

# Emergency mask a service
curl -X POST http://localhost:8960/service/smarketsherpa-platform/emergency-mask

# Database pre-flight check
curl http://localhost:8960/preflight/database

# Smart restart with all checks
curl -X POST http://localhost:8960/service/smarketsherpa-platform/smart-restart
```

## Prevention Checklist

Before deploying any new service:
- [ ] Run `/opt/revcore/scripts/database-discovery.py`
- [ ] Check BOTH `DB_*` and `POSTGRES_*` vars are set
- [ ] Test actual DB connection
- [ ] Verify file permissions for service user
- [ ] Set reasonable RestartSec (30s minimum)
- [ ] Add StartLimitBurst to prevent infinite loops

## Files Modified

- `/opt/revguard-v3/revguard.py` - v3.1 with crisis capabilities
- `/opt/revcore/scripts/database-discovery.py` - Connection testing
- `/opt/revcore/scripts/crisis-monitor.py` - New monitoring script
- `/opt/shared-api-engine/.env` - Added POSTGRES_* variables
