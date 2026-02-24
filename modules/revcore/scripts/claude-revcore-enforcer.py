#!/usr/bin/env python3
"""
Claude Code + RevCore Integration Daemon
Monitors and enforces resource limits for Claude Code processes
Prevents runaway memory/CPU consumption
"""

import psutil
import subprocess
import json
import time
import logging
import os
from datetime import datetime
from pathlib import Path

# Configuration
MEMORY_LIMIT_MB = 2000
MEMORY_KILL_THRESHOLD_MB = 2200  # Emergency kill threshold
CPU_LIMIT_PERCENT = 60
CHECK_INTERVAL = 5  # Check every 5 seconds

# Logging setup
LOG_DIR = Path("/var/log/revcore")
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR / "claude-enforcer.log"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class ClaudeResourceEnforcer:
    def __init__(self):
        self.violated_processes = {}  # Track violations for escalation
        self.violation_threshold = 3  # Kill after 3 violations
        
    def find_claude_processes(self):
        """Find all Claude Code processes"""
        claude_procs = []
        try:
            for proc in psutil.process_iter(['pid', 'name', 'memory_info', 'cpu_percent', 'cmdline']):
                try:
                    if 'claude' in proc.info['name'].lower() or \
                       (proc.info['cmdline'] and any('claude' in arg for arg in proc.info['cmdline'])):
                        claude_procs.append(proc)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
        except Exception as e:
            logger.error(f"Error finding Claude processes: {e}")
        
        return claude_procs
    
    def check_and_enforce(self):
        """Check resources and enforce limits"""
        claude_procs = self.find_claude_processes()
        
        if not claude_procs:
            return
        
        current_time = datetime.now()
        
        for proc in claude_procs:
            try:
                pid = proc.pid
                memory_mb = proc.memory_info().rss / 1024 / 1024
                cpu_percent = proc.cpu_percent(interval=0.5)
                name = proc.name()
                
                # Log current state
                logger.debug(f"PID {pid} ({name}): Memory={memory_mb:.1f}MB, CPU={cpu_percent:.1f}%")
                
                violation = False
                violation_type = ""
                
                # Check memory limits
                if memory_mb > MEMORY_KILL_THRESHOLD_MB:
                    # EMERGENCY: Kill immediately
                    logger.critical(f"EMERGENCY: PID {pid} exceeded critical memory threshold ({memory_mb:.1f}MB > {MEMORY_KILL_THRESHOLD_MB}MB). Killing immediately.")
                    self._kill_process(proc)
                    continue
                
                elif memory_mb > MEMORY_LIMIT_MB:
                    violation = True
                    violation_type = f"Memory exceeded: {memory_mb:.1f}MB > {MEMORY_LIMIT_MB}MB"
                
                # Check CPU limits
                if cpu_percent > CPU_LIMIT_PERCENT:
                    violation = True
                    violation_type += f" | CPU exceeded: {cpu_percent:.1f}% > {CPU_LIMIT_PERCENT}%"
                
                # Track and escalate violations
                if violation:
                    if pid not in self.violated_processes:
                        self.violated_processes[pid] = {
                            'count': 0,
                            'first_violation': current_time,
                            'last_violation': current_time,
                            'type': violation_type
                        }
                    
                    violation_data = self.violated_processes[pid]
                    violation_data['count'] += 1
                    violation_data['last_violation'] = current_time
                    
                    logger.warning(f"PID {pid} Violation #{violation_data['count']}: {violation_type}")
                    
                    # Kill after repeated violations
                    if violation_data['count'] >= self.violation_threshold:
                        logger.error(f"PID {pid} reached violation threshold ({violation_data['count']}). Killing process.")
                        self._kill_process(proc)
                        del self.violated_processes[pid]
                    
                    # Attempt to slow down process
                    elif violation_data['count'] == 2:
                        logger.info(f"PID {pid} sent SIGSTOP (pause) to reduce resource usage")
                        try:
                            os.kill(pid, 19)  # SIGSTOP
                            time.sleep(2)
                            os.kill(pid, 18)  # SIGCONT
                        except:
                            pass
                
                else:
                    # Clear violations if process is now compliant
                    if pid in self.violated_processes:
                        logger.info(f"PID {pid} returned to normal operation")
                        del self.violated_processes[pid]
            
            except (psutil.NoSuchProcess, psutil.AccessDenied, Exception) as e:
                logger.debug(f"Error checking process {proc.pid}: {e}")
    
    def _kill_process(self, proc):
        """Gracefully kill a process, then forcefully if needed"""
        pid = proc.pid
        try:
            # First try SIGTERM (graceful)
            logger.warning(f"Sending SIGTERM to PID {pid}")
            proc.terminate()
            try:
                proc.wait(timeout=5)
                logger.info(f"PID {pid} terminated gracefully")
            except psutil.TimeoutExpired:
                # Force kill with SIGKILL
                logger.error(f"PID {pid} did not respond to SIGTERM. Sending SIGKILL.")
                proc.kill()
                proc.wait(timeout=2)
                logger.info(f"PID {pid} force killed")
        except Exception as e:
            logger.error(f"Error killing PID {pid}: {e}")
    
    def report_status(self):
        """Generate status report"""
        claude_procs = self.find_claude_processes()
        
        if not claude_procs:
            logger.info("No Claude Code processes currently running")
            return
        
        total_memory = 0
        for proc in claude_procs:
            try:
                memory_mb = proc.memory_info().rss / 1024 / 1024
                total_memory += memory_mb
                cpu_percent = proc.cpu_percent(interval=0.1)
                logger.info(f"Process {proc.pid}: {memory_mb:.1f}MB memory, {cpu_percent:.1f}% CPU")
            except:
                pass
        
        logger.info(f"Total Claude memory usage: {total_memory:.1f}MB / {MEMORY_LIMIT_MB}MB limit")
        
        if self.violated_processes:
            logger.warning(f"Active violations: {len(self.violated_processes)}")
            for pid, data in self.violated_processes.items():
                logger.warning(f"  PID {pid}: {data['count']} violations - {data['type']}")
    
    def run(self):
        """Main monitoring loop"""
        logger.info("=" * 60)
        logger.info("Claude Code + RevCore Enforcer Started")
        logger.info(f"Memory Limit: {MEMORY_LIMIT_MB}MB")
        logger.info(f"CPU Limit: {CPU_LIMIT_PERCENT}%")
        logger.info(f"Check Interval: {CHECK_INTERVAL}s")
        logger.info("=" * 60)
        
        check_count = 0
        
        try:
            while True:
                check_count += 1
                self.check_and_enforce()
                
                # Report status every 12 checks (60 seconds)
                if check_count % 12 == 0:
                    self.report_status()
                
                time.sleep(CHECK_INTERVAL)
        
        except KeyboardInterrupt:
            logger.info("Enforcer stopped by user")
        except Exception as e:
            logger.error(f"Fatal error in enforcer: {e}")

if __name__ == "__main__":
    enforcer = ClaudeResourceEnforcer()
    enforcer.run()
