#!/opt/revflow-os/shared-venv/bin/python
"""
RevFlow OS - Consul Port Validator & Service Registration
Validates ports, detects conflicts, and registers services with correct health checks.

Usage:
  ./consul-port-validator.py --scan              # Scan running services and show status
  ./consul-port-validator.py --validate          # Validate current Consul registrations
  ./consul-port-validator.py --fix               # Auto-fix misconfigured registrations
  ./consul-port-validator.py --register <file>   # Register services from JSON config
"""

import subprocess
import json
import requests
import argparse
import sys
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum

# Consul configuration
CONSUL_URL = "http://127.0.0.1:8500"
CONSUL_API = f"{CONSUL_URL}/v1"

# Reserved system ports that should NEVER be used for services
# Only ports that are ACTUALLY in use by Consul (not optional ones)
RESERVED_PORTS = {
    8300: "Consul RPC",
    8301: "Consul Serf LAN",
    8302: "Consul Serf WAN",
    8500: "Consul HTTP API",
    # 8501: "Consul HTTPS API (disabled)",
    # 8502: "Consul gRPC (disabled)",
    8503: "Consul gRPC TLS",
    8600: "Consul DNS",
}

# Known TCP-only services (no HTTP health check)
TCP_SERVICES = {
    5432: ("PostgreSQL", "postgresql"),
    6379: ("Redis", "redis"),
    3306: ("MySQL", "mysql"),
    27017: ("MongoDB", "mongodb"),
    9200: ("Elasticsearch", "elasticsearch"),
}

# RevFlow port ranges
REVFLOW_FRONTEND_RANGE = (3000, 3999)
REVFLOW_BACKEND_RANGE = (8000, 8999)
REVFLOW_INFRA_RANGE = (9000, 9999)


class HealthCheckType(Enum):
    HTTP = "http"
    TCP = "tcp"
    SCRIPT = "script"


@dataclass
class RunningService:
    port: int
    pid: int
    process_name: str
    protocol: str = "tcp"


@dataclass
class ConsulService:
    id: str
    name: str
    port: int
    check_type: Optional[str] = None
    check_endpoint: Optional[str] = None


class Colors:
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    RESET = '\033[0m'
    BOLD = '\033[1m'


def print_header(text: str):
    print(f"\n{Colors.BOLD}{Colors.CYAN}{'='*60}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.CYAN}{text:^60}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.CYAN}{'='*60}{Colors.RESET}\n")


def print_ok(text: str):
    print(f"  {Colors.GREEN}✓{Colors.RESET} {text}")


def print_warn(text: str):
    print(f"  {Colors.YELLOW}⚠{Colors.RESET} {text}")


def print_error(text: str):
    print(f"  {Colors.RED}✗{Colors.RESET} {text}")


def print_info(text: str):
    print(f"  {Colors.BLUE}ℹ{Colors.RESET} {text}")


def get_listening_ports() -> Dict[int, RunningService]:
    """Get all listening TCP ports and their processes."""
    services = {}
    try:
        result = subprocess.run(
            ["netstat", "-tulpn"],
            capture_output=True,
            text=True
        )
        for line in result.stdout.split('\n'):
            if 'LISTEN' not in line:
                continue
            parts = line.split()
            if len(parts) < 7:
                continue

            # Parse address:port
            addr_port = parts[3]
            if ':' in addr_port:
                port_str = addr_port.rsplit(':', 1)[-1]
                try:
                    port = int(port_str)
                except ValueError:
                    continue

                # Parse PID/process
                pid_proc = parts[6] if len(parts) > 6 else "-"
                if '/' in pid_proc:
                    pid_str, proc = pid_proc.split('/', 1)
                    try:
                        pid = int(pid_str)
                    except ValueError:
                        pid = 0
                else:
                    pid = 0
                    proc = pid_proc

                # Only track if not already tracked or if this is 0.0.0.0
                if port not in services or '0.0.0.0' in addr_port:
                    services[port] = RunningService(
                        port=port,
                        pid=pid,
                        process_name=proc,
                        protocol="tcp"
                    )
    except Exception as e:
        print_error(f"Failed to get listening ports: {e}")

    return services


def get_consul_services() -> Dict[str, ConsulService]:
    """Get all registered Consul services."""
    services = {}
    try:
        resp = requests.get(f"{CONSUL_API}/agent/services", timeout=5)
        resp.raise_for_status()
        data = resp.json()

        for svc_id, svc_data in data.items():
            services[svc_id] = ConsulService(
                id=svc_id,
                name=svc_data.get("Service", ""),
                port=svc_data.get("Port", 0)
            )

        # Get health check details
        resp = requests.get(f"{CONSUL_API}/agent/checks", timeout=5)
        resp.raise_for_status()
        checks = resp.json()

        for check_id, check_data in checks.items():
            svc_id = check_data.get("ServiceID", "")
            if svc_id in services:
                if "HTTP" in check_data.get("Definition", {}):
                    services[svc_id].check_type = "http"
                    services[svc_id].check_endpoint = check_data["Definition"].get("HTTP", "")
                elif "TCP" in check_data.get("Definition", {}):
                    services[svc_id].check_type = "tcp"
                    services[svc_id].check_endpoint = check_data["Definition"].get("TCP", "")
                # Also check top-level fields
                if check_data.get("Type") == "http":
                    services[svc_id].check_type = "http"
                elif check_data.get("Type") == "tcp":
                    services[svc_id].check_type = "tcp"

    except Exception as e:
        print_error(f"Failed to get Consul services: {e}")

    return services


def get_consul_health() -> Dict[str, str]:
    """Get health status of all Consul checks."""
    health = {}
    try:
        for state in ["passing", "warning", "critical"]:
            resp = requests.get(f"{CONSUL_API}/health/state/{state}", timeout=5)
            resp.raise_for_status()
            for check in resp.json():
                svc_id = check.get("ServiceID", "")
                if svc_id:
                    health[svc_id] = state
    except Exception as e:
        print_error(f"Failed to get health status: {e}")
    return health


def validate_port(port: int) -> List[str]:
    """Validate a port and return list of issues."""
    issues = []

    # Check reserved ports
    if port in RESERVED_PORTS:
        issues.append(f"Port {port} is reserved for {RESERVED_PORTS[port]}")

    # Check port ranges
    if port < 1024:
        issues.append(f"Port {port} is a privileged port (< 1024)")

    return issues


def determine_health_check_type(port: int, process_name: str) -> HealthCheckType:
    """Determine the appropriate health check type for a service."""
    # Known TCP-only services
    if port in TCP_SERVICES:
        return HealthCheckType.TCP

    # Process name hints
    tcp_processes = ["postgres", "redis", "mysql", "mongo", "consul"]
    for proc in tcp_processes:
        if proc in process_name.lower():
            return HealthCheckType.TCP

    # Default to HTTP for RevFlow backend ports
    if REVFLOW_BACKEND_RANGE[0] <= port <= REVFLOW_BACKEND_RANGE[1]:
        return HealthCheckType.HTTP

    # Default to TCP for unknown services
    return HealthCheckType.TCP


def scan_services():
    """Scan and display all running services."""
    print_header("SCANNING RUNNING SERVICES")

    listening = get_listening_ports()
    consul_services = get_consul_services()
    consul_health = get_consul_health()

    # Group by port range
    frontend_ports = {}
    backend_ports = {}
    infra_ports = {}
    other_ports = {}

    for port, svc in listening.items():
        if REVFLOW_FRONTEND_RANGE[0] <= port <= REVFLOW_FRONTEND_RANGE[1]:
            frontend_ports[port] = svc
        elif REVFLOW_BACKEND_RANGE[0] <= port <= REVFLOW_BACKEND_RANGE[1]:
            backend_ports[port] = svc
        elif REVFLOW_INFRA_RANGE[0] <= port <= REVFLOW_INFRA_RANGE[1]:
            infra_ports[port] = svc
        else:
            other_ports[port] = svc

    # Display backend services (main focus)
    print(f"{Colors.BOLD}Backend Services (8000-8999):{Colors.RESET}")
    print(f"  {'Port':<8} {'Process':<20} {'Consul Status':<15} {'Health':<10}")
    print(f"  {'-'*8} {'-'*20} {'-'*15} {'-'*10}")

    for port in sorted(backend_ports.keys()):
        svc = backend_ports[port]

        # Find matching Consul service
        consul_match = None
        consul_status = "Not registered"
        health_status = "-"

        for cid, csvc in consul_services.items():
            if csvc.port == port:
                consul_match = csvc
                consul_status = f"✓ {csvc.name[:15]}"
                health_status = consul_health.get(cid, "unknown")
                break

        # Check for issues
        issues = validate_port(port)

        health_color = Colors.GREEN if health_status == "passing" else (
            Colors.YELLOW if health_status == "warning" else (
                Colors.RED if health_status == "critical" else Colors.RESET
            )
        )

        status_color = Colors.GREEN if consul_match else Colors.YELLOW

        print(f"  {port:<8} {svc.process_name[:20]:<20} {status_color}{consul_status[:15]:<15}{Colors.RESET} {health_color}{health_status:<10}{Colors.RESET}")

        for issue in issues:
            print_error(f"    {issue}")

    # Summary
    print(f"\n{Colors.BOLD}Summary:{Colors.RESET}")
    print(f"  Running services: {len(listening)}")
    print(f"  Consul registered: {len(consul_services)}")
    print(f"  Backend ports in use: {len(backend_ports)}")

    # Check for conflicts
    conflicts = []
    for port in listening.keys():
        if port in RESERVED_PORTS:
            if any(cs.port == port for cs in consul_services.values()):
                conflicts.append((port, RESERVED_PORTS[port]))

    if conflicts:
        print(f"\n{Colors.RED}{Colors.BOLD}PORT CONFLICTS DETECTED:{Colors.RESET}")
        for port, reserved_for in conflicts:
            print_error(f"Port {port} is registered but reserved for {reserved_for}")


def validate_registrations():
    """Validate all Consul registrations."""
    print_header("VALIDATING CONSUL REGISTRATIONS")

    listening = get_listening_ports()
    consul_services = get_consul_services()
    consul_health = get_consul_health()

    issues_found = 0

    for svc_id, svc in consul_services.items():
        print(f"\n{Colors.BOLD}{svc.name}{Colors.RESET} (:{svc.port})")

        svc_issues = []

        # Check if port is reserved
        if svc.port in RESERVED_PORTS and svc_id not in ["consul"]:
            svc_issues.append(f"Uses reserved port {svc.port} ({RESERVED_PORTS[svc.port]})")

        # Check if service is actually running
        if svc.port not in listening:
            svc_issues.append(f"No service listening on port {svc.port}")

        # Check health check type
        if svc.port in TCP_SERVICES and svc.check_type == "http":
            svc_issues.append(f"Using HTTP check for TCP-only service (should be TCP)")

        # Check health status
        health = consul_health.get(svc_id, "unknown")
        if health == "critical":
            svc_issues.append(f"Health check is CRITICAL")
        elif health == "warning":
            svc_issues.append(f"Health check is WARNING")

        if svc_issues:
            for issue in svc_issues:
                print_error(issue)
            issues_found += len(svc_issues)
        else:
            print_ok("OK")

    print(f"\n{Colors.BOLD}Validation Complete:{Colors.RESET}")
    if issues_found:
        print_error(f"Found {issues_found} issue(s)")
        print_info("Run with --fix to auto-correct issues")
    else:
        print_ok("All registrations valid")

    return issues_found


def fix_registrations():
    """Auto-fix misconfigured Consul registrations."""
    print_header("FIXING CONSUL REGISTRATIONS")

    listening = get_listening_ports()
    consul_services = get_consul_services()

    fixes_applied = 0

    for svc_id, svc in list(consul_services.items()):
        fixes_needed = []

        # Skip Consul itself
        if svc_id == "consul":
            continue

        # Check if using reserved port
        if svc.port in RESERVED_PORTS:
            print_warn(f"{svc.name}: Using reserved port {svc.port}")
            # Try to find actual port
            for port, running in listening.items():
                if svc.name.lower().replace(" ", "") in running.process_name.lower().replace(" ", ""):
                    if port not in RESERVED_PORTS:
                        fixes_needed.append(("port", port))
                        break

        # Check if service not running on registered port
        if svc.port not in listening and svc.port not in RESERVED_PORTS:
            print_warn(f"{svc.name}: Not listening on port {svc.port}")
            # Deregister orphaned service
            try:
                resp = requests.put(f"{CONSUL_API}/agent/service/deregister/{svc_id}", timeout=5)
                if resp.status_code == 200:
                    print_ok(f"Deregistered orphaned service: {svc.name}")
                    fixes_applied += 1
            except Exception as e:
                print_error(f"Failed to deregister: {e}")
            continue

        # Check if TCP service has HTTP check
        if svc.port in TCP_SERVICES and svc.check_type == "http":
            fixes_needed.append(("check_type", "tcp"))

        # Apply fixes by re-registering
        if fixes_needed:
            new_port = svc.port
            check_type = svc.check_type or "http"

            for fix_type, fix_value in fixes_needed:
                if fix_type == "port":
                    new_port = fix_value
                elif fix_type == "check_type":
                    check_type = fix_value

            # Deregister old
            try:
                requests.put(f"{CONSUL_API}/agent/service/deregister/{svc_id}", timeout=5)
            except:
                pass

            # Determine health check
            if check_type == "tcp" or new_port in TCP_SERVICES:
                check_config = {
                    "TCP": f"localhost:{new_port}",
                    "Interval": "30s",
                    "Timeout": "5s"
                }
            else:
                # Try to determine correct health endpoint
                health_endpoint = f"http://localhost:{new_port}/health"
                # Test if /health exists
                try:
                    test_resp = requests.get(health_endpoint, timeout=2)
                    if test_resp.status_code == 404:
                        # Try root
                        health_endpoint = f"http://localhost:{new_port}/"
                except:
                    health_endpoint = f"http://localhost:{new_port}/"

                check_config = {
                    "HTTP": health_endpoint,
                    "Interval": "30s",
                    "Timeout": "10s"
                }

            # Register with fixes
            registration = {
                "ID": svc_id,
                "Name": svc.name,
                "Port": new_port,
                "Tags": ["revflow", "auto-fixed"],
                "Check": check_config
            }

            try:
                resp = requests.put(
                    f"{CONSUL_API}/agent/service/register",
                    json=registration,
                    timeout=5
                )
                if resp.status_code == 200:
                    print_ok(f"Fixed {svc.name}: port={new_port}, check={check_type}")
                    fixes_applied += 1
                else:
                    print_error(f"Failed to register: {resp.text}")
            except Exception as e:
                print_error(f"Failed to register: {e}")

    print(f"\n{Colors.BOLD}Fix Complete:{Colors.RESET}")
    print_ok(f"Applied {fixes_applied} fix(es)")


def register_from_file(filepath: str):
    """Register services from a JSON configuration file."""
    print_header(f"REGISTERING FROM {filepath}")

    try:
        with open(filepath) as f:
            config = json.load(f)
    except Exception as e:
        print_error(f"Failed to read config file: {e}")
        return

    listening = get_listening_ports()

    for svc in config.get("services", []):
        svc_id = svc.get("id")
        svc_name = svc.get("name")
        svc_port = svc.get("port")

        if not all([svc_id, svc_name, svc_port]):
            print_error(f"Invalid service config: {svc}")
            continue

        # Validate port
        issues = validate_port(svc_port)
        if issues:
            print_error(f"{svc_name}: {', '.join(issues)}")
            continue

        # Check if port is listening
        if svc_port not in listening:
            print_warn(f"{svc_name}: Port {svc_port} not listening, skipping")
            continue

        # Determine check type
        check_type = svc.get("check_type", "auto")
        if check_type == "auto":
            check_type = determine_health_check_type(svc_port, listening[svc_port].process_name)

        # Build check config
        if check_type == HealthCheckType.TCP or check_type == "tcp":
            check_config = {
                "TCP": f"localhost:{svc_port}",
                "Interval": svc.get("interval", "30s"),
                "Timeout": svc.get("timeout", "5s")
            }
        else:
            endpoint = svc.get("health_endpoint", f"http://localhost:{svc_port}/health")
            check_config = {
                "HTTP": endpoint,
                "Interval": svc.get("interval", "30s"),
                "Timeout": svc.get("timeout", "10s")
            }

        # Register
        registration = {
            "ID": svc_id,
            "Name": svc_name,
            "Port": svc_port,
            "Tags": svc.get("tags", ["revflow"]),
            "Meta": svc.get("meta", {}),
            "Check": check_config
        }

        try:
            resp = requests.put(
                f"{CONSUL_API}/agent/service/register",
                json=registration,
                timeout=5
            )
            if resp.status_code == 200:
                print_ok(f"Registered: {svc_name} (:{svc_port})")
            else:
                print_error(f"Failed: {svc_name} - {resp.text}")
        except Exception as e:
            print_error(f"Failed: {svc_name} - {e}")


def main():
    parser = argparse.ArgumentParser(
        description="RevFlow OS - Consul Port Validator & Service Registration"
    )
    parser.add_argument("--scan", action="store_true", help="Scan running services")
    parser.add_argument("--validate", action="store_true", help="Validate Consul registrations")
    parser.add_argument("--fix", action="store_true", help="Auto-fix misconfigured registrations")
    parser.add_argument("--register", metavar="FILE", help="Register services from JSON file")

    args = parser.parse_args()

    if not any([args.scan, args.validate, args.fix, args.register]):
        # Default: show status
        args.scan = True
        args.validate = True

    if args.scan:
        scan_services()

    if args.validate:
        validate_registrations()

    if args.fix:
        fix_registrations()

    if args.register:
        register_from_file(args.register)


if __name__ == "__main__":
    main()
