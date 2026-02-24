#!/bin/bash
LOGFILE="/opt/revhome/health.log"
URL="http://127.0.0.1:8100/getStatus"
TS=$(date '+%Y-%m-%d %H:%M:%S')

if curl -s "$URL" | grep -q "healthy"; then
  echo "$TS ✅ API healthy" >> "$LOGFILE"
else
  echo "$TS ❌ API down, restarting..." >> "$LOGFILE"
  systemctl restart revhome.service
fi
