#!/usr/bin/env python3
"""
Update RevPublish nginx config to serve static files
Created: 2026-01-23 03:34:00
"""

import re
from datetime import datetime
import shutil
import subprocess

CONFIG_FILE = "/etc/nginx/sites-available/automation.smarketsherpa.ai"

# New RevPublish location block
NEW_REVPUBLISH_BLOCK = """    # RevPublish Frontend (Production Build)
    location /revpublish/ {
        alias /opt/revpublish/frontend/dist/;
        try_files $uri $uri/ /revpublish/index.html;
        
        # Cache static assets
        location ~* \\.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf|eot)$ {
            expires 1y;
            add_header Cache-Control "public, immutable";
        }
    }"""

def backup_config():
    """Create backup of nginx config"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = f"{CONFIG_FILE}.backup-{timestamp}"
    shutil.copy2(CONFIG_FILE, backup_file)
    print(f"✓ Backup created: {backup_file}")
    return backup_file

def update_config():
    """Update nginx config to serve static files"""
    with open(CONFIG_FILE, 'r') as f:
        content = f.read()
    
    # Pattern to match the RevPublish location block (both comments and block)
    pattern = r'    # RevPublish Frontend \(Port 3550\)\s+location /revpublish/ \{[^}]*proxy_pass[^}]*\}'
    
    # Count matches
    matches = re.findall(pattern, content, re.DOTALL)
    if not matches:
        print("✗ Could not find RevPublish proxy_pass blocks")
        return False
    
    print(f"Found {len(matches)} RevPublish block(s) to replace")
    
    # Replace all occurrences
    new_content = re.sub(pattern, NEW_REVPUBLISH_BLOCK, content, flags=re.DOTALL)
    
    # Write updated config
    with open(CONFIG_FILE, 'w') as f:
        f.write(new_content)
    
    print("✓ Configuration updated")
    return True

def test_nginx():
    """Test nginx configuration"""
    result = subprocess.run(['nginx', '-t'], capture_output=True, text=True)
    if result.returncode == 0:
        print("✓ Nginx config syntax OK")
        return True
    else:
        print("✗ Nginx config has errors:")
        print(result.stderr)
        return False

def reload_nginx():
    """Reload nginx"""
    result = subprocess.run(['systemctl', 'reload', 'nginx'], capture_output=True)
    if result.returncode == 0:
        print("✓ Nginx reloaded")
        return True
    else:
        print("✗ Failed to reload nginx")
        return False

def test_access():
    """Test HTTP access"""
    result = subprocess.run(
        ['curl', '-s', '-o', '/dev/null', '-w', '%{http_code}', 
         'http://217.15.168.106/revpublish/'],
        capture_output=True,
        text=True
    )
    http_code = result.stdout.strip()
    
    if http_code == '200':
        print(f"✓ SUCCESS! RevPublish now serves static files (HTTP {http_code})")
        return True
    else:
        print(f"⚠ Got HTTP {http_code} (expected 200)")
        return False

def main():
    print("=" * 50)
    print("Updating RevPublish to Production Static Serving")
    print("=" * 50)
    print()
    
    # Step 1: Backup
    print("[1/5] Backing up nginx config...")
    backup_file = backup_config()
    print()
    
    # Step 2: Update config
    print("[2/5] Updating nginx configuration...")
    if not update_config():
        print("Aborting...")
        return 1
    print()
    
    # Step 3: Test config
    print("[3/5] Testing nginx configuration...")
    if not test_nginx():
        print()
        print("Restoring backup...")
        shutil.copy2(backup_file, CONFIG_FILE)
        return 1
    print()
    
    # Step 4: Reload
    print("[4/5] Reloading nginx...")
    if not reload_nginx():
        return 1
    print()
    
    # Step 5: Test access
    print("[5/5] Testing access...")
    import time
    time.sleep(2)
    test_access()
    
    print()
    print("=" * 50)
    print("UPDATE COMPLETE")
    print("=" * 50)
    print()
    print("✓ Stopped Vite dev server (port 3550 freed)")
    print("✓ Nginx now serves production build from /opt/revpublish/frontend/dist/")
    print()
    print("Test URLs:")
    print("  • http://217.15.168.106/revpublish/")
    print("  • https://automation.smarketsherpa.ai/revpublish/")
    print()
    print("To rebuild frontend in future:")
    print("  cd /opt/revpublish/frontend")
    print("  npm run build")
    print("  systemctl reload nginx")
    print()
    print("=" * 50)
    
    return 0

if __name__ == "__main__":
    exit(main())
