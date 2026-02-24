# 🚀 REVFLOW OS - AUTOMATED MIGRATION QUICK START

## ✅ Everything is Ready!

Three scripts have been created in `/opt/shared-api-engine/`:
- `RUN_MIGRATION_NOW.sh` - Main migration script
- `verify_migration.sh` - Post-migration testing
- `rollback_migration.sh` - Rollback if needed

---

## 🎯 RUN THE MIGRATION NOW

### Step 1: Make scripts executable

```bash
chmod +x /opt/shared-api-engine/RUN_MIGRATION_NOW.sh
chmod +x /opt/shared-api-engine/verify_migration.sh
chmod +x /opt/shared-api-engine/rollback_migration.sh
```

### Step 2: Run the migration (2-3 minutes)

```bash
bash /opt/shared-api-engine/RUN_MIGRATION_NOW.sh
```

**What it does:**
- ✅ Backs up all 7 modules (in `/opt/shared-api-engine/migration_backups_<timestamp>/`)
- ✅ Adds RevFlowClient import to each module
- ✅ Replaces all hardcoded `localhost:8XXX` calls
- ✅ Replaces with `client.call_module()` gateway calls
- ✅ Logs all changes to `/opt/shared-api-engine/migration_log_<timestamp>.txt`
- ✅ Scans for remaining hardcoded calls
- ✅ Verifies RevFlowClient works

### Step 3: Verify the migration (2 minutes)

```bash
bash /opt/shared-api-engine/verify_migration.sh
```

**What it checks:**
- ✅ Gateway health
- ✅ All 7 module services running
- ✅ No remaining hardcoded calls
- ✅ RevFlowClient functionality
- ✅ Test log saved to `/opt/shared-api-engine/migration_test_<timestamp>.log`

### Step 4: Restart the modules (1 minute)

```bash
systemctl restart revpublish-backend.service
systemctl restart revvest-iq.service
systemctl restart revaudit-backend.service
systemctl restart revaudit-frontend.service
systemctl restart revaudit-v5.service
systemctl restart revaudit-v6.service
systemctl restart revaudit.service
systemctl restart revflow-lead-scoring.service
systemctl restart revshield-pro.service
systemctl restart revflow-admin-api.service
systemctl restart revhome-uvicorn.service
systemctl restart revhome-docker.service
systemctl restart revhome-chat-api.service
```

Or restart all rev* services at once:
```bash
systemctl restart rev*.service
```

---

## 📊 What Gets Migrated

| Module | File | Changes |
|--------|------|---------|
| **RevPublish** | `/opt/revpublish/backend/routes/content_sources.py` | 3 hardcoded calls → gateway |
| **RevVest IQ** | `/opt/revflow-os/modules/revvest/backend/gap_analyzer.py` | 1 hardcoded URL → gateway |
| **RevAudit** | `/opt/shared-api-engine/revaudit/revaudit_v3.py` | 3 hardcoded ports → gateway |
| **Lead Scoring** | `/opt/revflow-revenue-aligned-scoring-system/python/shared-api-engine/revflow_scoring_client.py` | 1 hardcoded URL → gateway |
| **RevShield Pro** | `/opt/revflow-security-monitor/scripts/scheduled_scanner.py` | 1 hardcoded call → gateway |
| **Admin API** | `/opt/revflow-admin-api/main.py` | 2 hardcoded calls → gateway |
| **RevHome** | `/opt/revhome/*.sh` | Updated shell scripts |

---

## 🔄 If Something Goes Wrong

### View the migration log
```bash
cat /opt/shared-api-engine/migration_log_<timestamp>.txt
```

### Rollback to pre-migration state

Find the timestamp from the migration script output or:
```bash
ls -dt /opt/shared-api-engine/migration_backups_* | head -1
```

Then rollback:
```bash
bash /opt/shared-api-engine/rollback_migration.sh <timestamp>
```

Example:
```bash
bash /opt/shared-api-engine/rollback_migration.sh 1738001234
```

This restores all files from the backup and clears the changes.

---

## 📝 Migration Checklist

- [ ] Read this guide
- [ ] Make scripts executable (`chmod +x`)
- [ ] Run migration: `bash RUN_MIGRATION_NOW.sh`
- [ ] Check migration log for errors
- [ ] Run verification: `bash verify_migration.sh`
- [ ] Check verification log
- [ ] Restart modules: `systemctl restart rev*.service`
- [ ] Test gateway: `curl http://localhost:8004/api/gateway/health`
- [ ] Test individual modules
- [ ] Confirm no hardcoded calls remain

---

## ⏱️ Timeline

| Step | Time | What |
|------|------|------|
| 1 | 2 min | Make scripts executable |
| 2 | 3 min | Run migration |
| 3 | 2 min | Run verification |
| 4 | 2 min | Restart modules |
| **Total** | **~10 minutes** | **All 7 modules migrated** |

---

## 🎯 Success Indicators

✅ Migration script completes without errors
✅ Verification script shows all PASS
✅ All 7 modules restart successfully
✅ Gateway health check returns 200 OK
✅ No `localhost:8XXX` calls remain in module files
✅ `grep -r "localhost:8" /opt/revpublish /opt/revvest /opt/revaudit` returns nothing

---

## 💡 Pro Tips

1. **Run everything in a tmux session** so if connection drops, migration continues:
   ```bash
   tmux new-session -d -s migration
   tmux send-keys -t migration "bash /opt/shared-api-engine/RUN_MIGRATION_NOW.sh" Enter
   ```

2. **Monitor logs while running**:
   ```bash
   tail -f /opt/shared-api-engine/migration_log_*.txt
   ```

3. **Keep a backup of all backups** before cleanup:
   ```bash
   cp -r /opt/shared-api-engine/migration_backups_* /root/migration_backups_safety/
   ```

---

## 🚨 Emergency Contacts / Notes

- **Gateway endpoint**: `http://localhost:8004/api/gateway`
- **RevCore API**: `http://localhost:8770`
- **Shared API**: `/opt/shared-api-engine`
- **Client file**: `/opt/shared-api-engine/revflow_client.py`
- **Environment**: `/opt/shared-api-engine/.env`

---

**Ready? Run this:**

```bash
bash /opt/shared-api-engine/RUN_MIGRATION_NOW.sh && bash /opt/shared-api-engine/verify_migration.sh
```

Let's go! 🚀
