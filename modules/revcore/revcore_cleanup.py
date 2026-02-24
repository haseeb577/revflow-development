"""
RevFlow OS™ - RevCore Cleanup API
Purpose: Automated disk space management and maintenance
Module: 17 (RevCore™)
Port: 8950 (RevCore API Hub)
Date: 2026-02-02
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from typing import Optional, Dict, List
import subprocess
import os
from datetime import datetime
import psutil
import shutil

router = APIRouter(prefix="/api/cleanup", tags=["Maintenance"])


class CleanupConfig(BaseModel):
    """Configuration for cleanup operations"""
    journal_days: int = Field(default=7, description="Keep systemd journals for this many days")
    journal_size_mb: int = Field(default=500, description="Max journal size in MB")
    log_days: int = Field(default=14, description="Keep application logs for this many days")
    tmp_days: int = Field(default=7, description="Keep /tmp files for this many days")
    backup_days: int = Field(default=14, description="Keep backups for this many days")
    docker_cleanup: bool = Field(default=True, description="Clean Docker resources")
    truncate_large_logs: bool = Field(default=True, description="Truncate logs larger than 100MB")


class CleanupResult(BaseModel):
    """Result of cleanup operation"""
    success: bool
    disk_before: str
    disk_after: str
    space_recovered_percent: float
    operations_performed: List[str]
    errors: List[str]
    timestamp: str
    log_file: str


class DiskStatus(BaseModel):
    """Current disk status"""
    total_gb: float
    used_gb: float
    free_gb: float
    percent_used: float
    status: str  # healthy, warning, critical
    timestamp: str


def get_disk_info() -> Dict:
    """Get current disk usage information"""
    disk = psutil.disk_usage('/')
    return {
        'total_gb': round(disk.total / (1024**3), 2),
        'used_gb': round(disk.used / (1024**3), 2),
        'free_gb': round(disk.free / (1024**3), 2),
        'percent_used': disk.percent
    }


def get_disk_status(percent: float) -> str:
    """Determine disk status based on usage"""
    if percent < 70:
        return "healthy"
    elif percent < 85:
        return "warning"
    else:
        return "critical"


def run_command(cmd: List[str], description: str) -> tuple:
    """Run shell command and return success status"""
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout
        )
        return True, f"{description}: OK"
    except subprocess.TimeoutExpired:
        return False, f"{description}: Timeout"
    except Exception as e:
        return False, f"{description}: {str(e)}"


def clean_systemd_journals(config: CleanupConfig) -> tuple:
    """Clean systemd journals"""
    operations = []
    errors = []
    
    # Vacuum by time
    success, msg = run_command(
        ['journalctl', '--vacuum-time', f'{config.journal_days}d'],
        "Journal cleanup (time)"
    )
    if success:
        operations.append(msg)
    else:
        errors.append(msg)
    
    # Vacuum by size
    success, msg = run_command(
        ['journalctl', '--vacuum-size', f'{config.journal_size_mb}M'],
        "Journal cleanup (size)"
    )
    if success:
        operations.append(msg)
    else:
        errors.append(msg)
    
    return operations, errors


def clean_nginx_logs(config: CleanupConfig) -> tuple:
    """Clean Nginx logs"""
    operations = []
    errors = []
    
    nginx_log_dir = "/var/log/nginx"
    if not os.path.exists(nginx_log_dir):
        return operations, ["Nginx log directory not found"]
    
    try:
        # Remove old rotated logs
        cmd = f"find {nginx_log_dir} -type f -name '*.log.*' -mtime +{config.log_days} -delete"
        success, msg = run_command(['bash', '-c', cmd], "Nginx log cleanup")
        if success:
            operations.append(msg)
        else:
            errors.append(msg)
    except Exception as e:
        errors.append(f"Nginx cleanup error: {str(e)}")
    
    return operations, errors


def clean_application_logs(config: CleanupConfig) -> tuple:
    """Clean application logs"""
    operations = []
    errors = []
    
    log_dirs = [
        "/opt/*/logs",
        "/opt/*/log",
        "/var/log/revflow*",
        "/root/logs"
    ]
    
    for pattern in log_dirs:
        try:
            cmd = f"find {pattern} -type f -name '*.log' -mtime +{config.log_days} -delete 2>/dev/null || true"
            success, msg = run_command(['bash', '-c', cmd], f"App logs cleanup ({pattern})")
            if success:
                operations.append(msg)
        except Exception as e:
            errors.append(f"App log cleanup error ({pattern}): {str(e)}")
    
    # Truncate large logs if enabled
    if config.truncate_large_logs:
        try:
            cmd = "find /opt -type f -name '*.log' -size +100M -exec truncate -s 0 {} \\; 2>/dev/null || true"
            success, msg = run_command(['bash', '-c', cmd], "Large log truncation")
            if success:
                operations.append(msg)
        except Exception as e:
            errors.append(f"Large log truncation error: {str(e)}")
    
    return operations, errors


def clean_tmp_directory(config: CleanupConfig) -> tuple:
    """Clean /tmp directory"""
    operations = []
    errors = []
    
    try:
        # Remove old files
        cmd = f"find /tmp -type f -atime +{config.tmp_days} -delete 2>/dev/null || true"
        success, msg = run_command(['bash', '-c', cmd], "/tmp cleanup")
        if success:
            operations.append(msg)
        else:
            errors.append(msg)
        
        # Remove empty directories
        cmd = "find /tmp -type d -empty -delete 2>/dev/null || true"
        success, msg = run_command(['bash', '-c', cmd], "/tmp empty dirs cleanup")
        if success:
            operations.append(msg)
    except Exception as e:
        errors.append(f"/tmp cleanup error: {str(e)}")
    
    return operations, errors


def clean_root_directory(config: CleanupConfig) -> tuple:
    """Clean /root directory"""
    operations = []
    errors = []
    
    try:
        # Remove old backups
        for ext in ['*.backup', '*.bak', '*.old']:
            cmd = f"find /root -type f -name '{ext}' -mtime +30 -delete 2>/dev/null || true"
            success, msg = run_command(['bash', '-c', cmd], f"Root cleanup ({ext})")
            if success:
                operations.append(msg)
        
        # Remove old archives
        cmd = "find /root -type f \\( -name '*.tar.gz' -o -name '*.tgz' -o -name '*.zip' \\) -mtime +30 -delete 2>/dev/null || true"
        success, msg = run_command(['bash', '-c', cmd], "Root archive cleanup")
        if success:
            operations.append(msg)
        
        # Clean Python cache
        cmd = "find /root -type d -name '__pycache__' -exec rm -rf {} + 2>/dev/null || true"
        success, msg = run_command(['bash', '-c', cmd], "Python cache cleanup")
        if success:
            operations.append(msg)
    except Exception as e:
        errors.append(f"Root directory cleanup error: {str(e)}")
    
    return operations, errors


def clean_apt_cache() -> tuple:
    """Clean APT cache"""
    operations = []
    errors = []
    
    for cmd, desc in [
        (['apt-get', 'clean'], "APT clean"),
        (['apt-get', 'autoclean'], "APT autoclean"),
        (['apt-get', 'autoremove', '-y'], "APT autoremove")
    ]:
        success, msg = run_command(cmd, desc)
        if success:
            operations.append(msg)
        else:
            errors.append(msg)
    
    return operations, errors


def clean_pip_cache() -> tuple:
    """Clean pip cache"""
    operations = []
    errors = []
    
    for cmd in ['pip', 'pip3']:
        success, msg = run_command([cmd, 'cache', 'purge'], f"{cmd} cache cleanup")
        if success:
            operations.append(msg)
        # Don't record as error if pip not found
    
    return operations, errors


def clean_docker(config: CleanupConfig) -> tuple:
    """Clean Docker resources"""
    operations = []
    errors = []
    
    if not config.docker_cleanup:
        return operations, errors
    
    # Check if Docker is installed
    try:
        subprocess.run(['which', 'docker'], capture_output=True, check=True)
    except subprocess.CalledProcessError:
        return operations, ["Docker not installed"]
    
    # Prune images
    success, msg = run_command(
        ['docker', 'image', 'prune', '-af', '--filter', 'until=168h'],
        "Docker image prune"
    )
    if success:
        operations.append(msg)
    else:
        errors.append(msg)
    
    # Prune containers
    success, msg = run_command(
        ['docker', 'container', 'prune', '-f'],
        "Docker container prune"
    )
    if success:
        operations.append(msg)
    else:
        errors.append(msg)
    
    # Prune volumes
    success, msg = run_command(
        ['docker', 'volume', 'prune', '-f'],
        "Docker volume prune"
    )
    if success:
        operations.append(msg)
    else:
        errors.append(msg)
    
    # Prune build cache
    success, msg = run_command(
        ['docker', 'builder', 'prune', '-af'],
        "Docker builder prune"
    )
    if success:
        operations.append(msg)
    else:
        errors.append(msg)
    
    return operations, errors


def clean_old_backups(config: CleanupConfig) -> tuple:
    """Clean old backups"""
    operations = []
    errors = []
    
    backup_dirs = [
        "/opt/backups",
        "/opt/*/backup",
        "/root/backups"
    ]
    
    for pattern in backup_dirs:
        try:
            cmd = f"find {pattern} -type f -mtime +{config.backup_days} -delete 2>/dev/null || true"
            success, msg = run_command(['bash', '-c', cmd], f"Backup cleanup ({pattern})")
            if success:
                operations.append(msg)
        except Exception as e:
            errors.append(f"Backup cleanup error ({pattern}): {str(e)}")
    
    return operations, errors


def perform_cleanup(config: CleanupConfig) -> CleanupResult:
    """Perform full cleanup operation"""
    # Get initial disk status
    disk_before = get_disk_info()
    
    all_operations = []
    all_errors = []
    
    # Perform all cleanup operations
    cleanup_functions = [
        (clean_systemd_journals, (config,)),
        (clean_nginx_logs, (config,)),
        (clean_application_logs, (config,)),
        (clean_tmp_directory, (config,)),
        (clean_root_directory, (config,)),
        (clean_apt_cache, ()),
        (clean_pip_cache, ()),
        (clean_docker, (config,)),
        (clean_old_backups, (config,))
    ]
    
    for func, args in cleanup_functions:
        ops, errs = func(*args)
        all_operations.extend(ops)
        all_errors.extend(errs)
    
    # Get final disk status
    disk_after = get_disk_info()
    
    # Create log file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = f"/var/log/revflow-cleanup-api-{timestamp}.log"
    
    try:
        with open(log_file, 'w') as f:
            f.write(f"RevFlow OS™ Cleanup Report\n")
            f.write(f"{'='*60}\n")
            f.write(f"Timestamp: {datetime.now().isoformat()}\n")
            f.write(f"\nDisk Before:\n")
            f.write(f"  Used: {disk_before['used_gb']} GB ({disk_before['percent_used']}%)\n")
            f.write(f"  Free: {disk_before['free_gb']} GB\n")
            f.write(f"\nDisk After:\n")
            f.write(f"  Used: {disk_after['used_gb']} GB ({disk_after['percent_used']}%)\n")
            f.write(f"  Free: {disk_after['free_gb']} GB\n")
            f.write(f"\nOperations Performed:\n")
            for op in all_operations:
                f.write(f"  ✓ {op}\n")
            if all_errors:
                f.write(f"\nErrors:\n")
                for err in all_errors:
                    f.write(f"  ✗ {err}\n")
    except Exception as e:
        all_errors.append(f"Could not create log file: {str(e)}")
        log_file = "N/A"
    
    return CleanupResult(
        success=len(all_errors) == 0,
        disk_before=f"{disk_before['percent_used']}%",
        disk_after=f"{disk_after['percent_used']}%",
        space_recovered_percent=round(disk_before['percent_used'] - disk_after['percent_used'], 2),
        operations_performed=all_operations,
        errors=all_errors,
        timestamp=datetime.now().isoformat(),
        log_file=log_file
    )


@router.get("/status", response_model=DiskStatus)
async def get_disk_status_endpoint():
    """
    Get current disk usage status
    
    Returns:
        DiskStatus: Current disk usage information
    """
    try:
        disk_info = get_disk_info()
        status = get_disk_status(disk_info['percent_used'])
        
        return DiskStatus(
            total_gb=disk_info['total_gb'],
            used_gb=disk_info['used_gb'],
            free_gb=disk_info['free_gb'],
            percent_used=disk_info['percent_used'],
            status=status,
            timestamp=datetime.now().isoformat()
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get disk status: {str(e)}")


@router.post("/run", response_model=CleanupResult)
async def run_cleanup_endpoint(
    background_tasks: BackgroundTasks,
    config: Optional[CleanupConfig] = None
):
    """
    Run disk cleanup operation
    
    Args:
        config: Optional cleanup configuration
        
    Returns:
        CleanupResult: Results of cleanup operation
    """
    if config is None:
        config = CleanupConfig()
    
    try:
        # Check if running as root
        if os.geteuid() != 0:
            raise HTTPException(
                status_code=403,
                detail="Cleanup operations require root privileges"
            )
        
        result = perform_cleanup(config)
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Cleanup failed: {str(e)}")


@router.post("/schedule")
async def schedule_cleanup(
    background_tasks: BackgroundTasks,
    config: Optional[CleanupConfig] = None
):
    """
    Schedule cleanup to run in background
    
    Args:
        config: Optional cleanup configuration
        
    Returns:
        Dict: Confirmation message
    """
    if config is None:
        config = CleanupConfig()
    
    background_tasks.add_task(perform_cleanup, config)
    
    return {
        "message": "Cleanup scheduled",
        "timestamp": datetime.now().isoformat()
    }


@router.get("/logs")
async def list_cleanup_logs():
    """
    List all cleanup log files
    
    Returns:
        List: List of cleanup log files with timestamps
    """
    try:
        log_dir = "/var/log"
        log_files = []
        
        for filename in os.listdir(log_dir):
            if filename.startswith("revflow-cleanup"):
                filepath = os.path.join(log_dir, filename)
                stat = os.stat(filepath)
                log_files.append({
                    "filename": filename,
                    "path": filepath,
                    "size_bytes": stat.st_size,
                    "size_mb": round(stat.st_size / (1024**2), 2),
                    "modified": datetime.fromtimestamp(stat.st_mtime).isoformat()
                })
        
        # Sort by modified time (newest first)
        log_files.sort(key=lambda x: x['modified'], reverse=True)
        
        return {
            "count": len(log_files),
            "logs": log_files
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list logs: {str(e)}")


# Add this router to your RevCore main.py:
"""
from revcore_cleanup import router as cleanup_router
app.include_router(cleanup_router)
"""
