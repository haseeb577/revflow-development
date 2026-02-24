# RevAudit v3.0 - System Audit Tool

**Part of MODULE 17: RevCore™**

## Usage

```bash
# Run audit
revaudit

# View latest report
cat /root/REVFLOW_AUDIT_LATEST.md

# Download report
scp root@217.15.168.106:/root/REVFLOW_AUDIT_LATEST.md ~/Downloads/
```

## What It Does

- Scans all 18 RevFlow OS™ modules
- Checks deployment status
- Generates markdown reports
- Maintains audit history

## Location

- Script: `/opt/shared-api-engine/revaudit/revaudit_v3.py`
- Command: `revaudit`
- Reports: `/root/REVFLOW_AUDIT_*.md`

---

**© 2026 RevFlow OS™**
