#!/usr/bin/env python3
"""
Kubernetes Pod Monitor and API Tester for Gomall Application (gRPC Compatible)
Automatically checks pod status and performs connectivity tests for gRPC services
"""

import os
import sys
import time
import socket
import subprocess
from datetime import datetime
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from colorama import init, Fore, Style
from tabulate import tabulate
import requests

# Initialize colorama for colored output
init(autoreset=True)

@dataclass
class PodStatus:
    """Pod status information"""
    name: str
    ready: str
    status: str
    restarts: int
    age: str
    namespace: str = "default"

@dataclass
class ServiceTest:
    """Service test configuration"""
    name: str
    port: int
    service_type: str = "grpc"  # "http" or "grpc"
    test_endpoint: str = "/"

class KubernetesMonitor:
    """Monitor Kubernetes pods and services"""
    
    def __init__(self, kubeconfig_path: str = "kind-kubeconfig.yaml"):
        self.kubeconfig_path = kubeconfig_path
        self.services = [
            ServiceTest("frontend", 8080, "http", "/"),
            ServiceTest("cart", 8883, "grpc"),
            ServiceTest("checkout", 8884, "grpc"),
            ServiceTest("email", 8885, "grpc"),
            ServiceTest("order", 8885, "grpc"),
            ServiceTest("payment", 8886, "grpc"),
            ServiceTest("product", 8881, "grpc"),
            ServiceTest("user", 8882, "grpc"),
        ]
        
    def run_kubectl_command(self, command: List[str]) -> Tuple[bool, str]:
        """Execute kubectl command with proper kubeconfig"""
        try:
            env = os.environ.copy()
            env['KUBECONFIG'] = self.kubeconfig_path
            
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                env=env,
                timeout=30
            )
            return result.returncode == 0, result.stdout.strip()
        except subprocess.TimeoutExpired:
            return False, "Command timeout"
        except Exception as e:
            return False, str(e)
    
    def get_pod_status(self) -> List[PodStatus]:
        """Get status of all pods"""
        success, output = self.run_kubectl_command([
            "kubectl", "get", "pods", "-o", "wide", "--no-headers"
        ])
        
        if not success:
            print(f"{Fore.RED}❌ Failed to get pod status: {output}")
            return []
        
        pods = []
        for line in output.split('\n'):
            if line.strip():
                parts = line.split()
                if len(parts) >= 5:
                    pod = PodStatus(
                        name=parts[0],
                        ready=parts[1],
                        status=parts[2],
                        restarts=int(parts[3]),
                        age=parts[4]
                    )
                    pods.append(pod)
        return pods
    
    def check_pods_health(self) -> bool:
        """Check if all pods are running and ready"""
        print(f"\n{Fore.CYAN}🔍 Checking Pod Status...")
        print("=" * 80)
        
        pods = self.get_pod_status()
        if not pods:
            return False
        
        # Prepare table data
        table_data = []
        all_healthy = True
        
        for pod in pods:
            # Status indicators
            if pod.status == "Running" and pod.ready.split('/')[0] == pod.ready.split('/')[1]:
                status_icon = f"{Fore.GREEN}✅"
                status_color = Fore.GREEN
            else:
                status_icon = f"{Fore.RED}❌"
                status_color = Fore.RED
                all_healthy = False
            
            # Restart warnings
            restart_indicator = ""
            if pod.restarts > 0:
                if pod.restarts > 5:
                    restart_indicator = f"{Fore.RED}🚨 {pod.restarts} restarts"
                else:
                    restart_indicator = f"{Fore.YELLOW}⚠️  {pod.restarts} restarts"
            
            table_data.append([
                status_icon,
                pod.name,
                f"{status_color}{pod.status}",
                f"{status_color}{pod.ready}",
                restart_indicator if restart_indicator else f"{Fore.GREEN}No restarts",
                pod.age
            ])
        
        # Print table
        headers = ["Status", "Pod Name", "Phase", "Ready", "Restarts", "Age"]
        print(tabulate(table_data, headers=headers, tablefmt="grid"))
        
        # Summary
        if all_healthy:
            print(f"\n{Fore.GREEN}🎉 All {len(pods)} pods are healthy and running!")
        else:
            print(f"\n{Fore.RED}⚠️  Some pods are not healthy. Check the details above.")
        
        return all_healthy
    
    def port_forward_service(self, service_name: str, local_port: int, service_port: int) -> subprocess.Popen:
        """Start port forwarding for a service"""
        env = os.environ.copy()
        env['KUBECONFIG'] = self.kubeconfig_path
        
        cmd = [
            "kubectl", "port-forward", 
            f"service/{service_name}", 
            f"{local_port}:{service_port}"
        ]
        
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            env=env
        )
        
        # Wait a moment for port forward to establish
        time.sleep(2)
        return process
    
    def test_port_connectivity(self, host: str, port: int, timeout: int = 5) -> Tuple[bool, str, float]:
        """Test if a port is open and accepting connections"""
        start_time = time.time()
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            result = sock.connect_ex((host, port))
            sock.close()
            response_time = time.time() - start_time
            
            if result == 0:
                return True, "Port open", response_time
            else:
                return False, "Port closed", response_time
        except socket.timeout:
            return False, "Connection timeout", timeout
        except Exception as e:
            return False, str(e), 0
    
    def test_http_service(self, url: str, timeout: int = 10) -> Tuple[bool, str, float]:
        """Test HTTP service endpoint"""
        start_time = time.time()
        try:
            response = requests.get(url, timeout=timeout)
            response_time = time.time() - start_time
            
            if response.status_code == 200:
                return True, f"HTTP {response.status_code}", response_time
            else:
                return False, f"HTTP {response.status_code}", response_time
        except requests.exceptions.ConnectionError:
            return False, "Connection refused", 0
        except requests.exceptions.Timeout:
            return False, "Request timeout", timeout
        except Exception as e:
            return False, str(e), 0
    
    def test_service_connectivity(self, service: ServiceTest, timeout: int = 10) -> Tuple[bool, str, float]:
        """Test service connectivity (HTTP or gRPC port check)"""
        port_forward_process = None
        try:
            # Start port forwarding
            local_port = 8000 + service.port  # Offset to avoid conflicts
            port_forward_process = self.port_forward_service(service.name, local_port, service.port)
            
            if service.service_type == "http":
                # Test HTTP endpoint
                url = f"http://localhost:{local_port}{service.test_endpoint}"
                return self.test_http_service(url, timeout)
            else:
                # Test gRPC port connectivity
                return self.test_port_connectivity("localhost", local_port, timeout)
                
        except Exception as e:
            return False, str(e), 0
        finally:
            if port_forward_process:
                port_forward_process.terminate()
                port_forward_process.wait()
    
    def run_connectivity_tests(self) -> bool:
        """Run connectivity tests for all services"""
        print(f"\n{Fore.CYAN}🧪 Running Service Connectivity Tests...")
        print("=" * 80)
        
        table_data = []
        all_tests_passed = True
        
        for service in self.services:
            print(f"Testing {service.name} ({service.service_type})...", end=" ")
            
            success, message, response_time = self.test_service_connectivity(service)
            
            if success:
                status_icon = f"{Fore.GREEN}✅"
                status_text = f"{Fore.GREEN}PASS"
                if service.service_type == "http":
                    response_text = f"{response_time:.3f}s"
                else:
                    response_text = f"Port open ({response_time:.3f}s)"
            else:
                status_icon = f"{Fore.RED}❌"
                status_text = f"{Fore.RED}FAIL"
                response_text = message
                all_tests_passed = False
            
            service_type_icon = "🌐" if service.service_type == "http" else "⚡"
            
            table_data.append([
                status_icon,
                f"{service_type_icon} {service.name}",
                status_text,
                f":{service.port}",
                service.service_type.upper(),
                response_text
            ])
            
            print(f"{status_text} - {message}")
        
        # Print results table
        headers = ["Status", "Service", "Result", "Port", "Type", "Response"]
        print(f"\n{tabulate(table_data, headers=headers, tablefmt='grid')}")
        
        if all_tests_passed:
            print(f"\n{Fore.GREEN}🎉 All connectivity tests passed!")
        else:
            print(f"\n{Fore.RED}⚠️  Some connectivity tests failed. Check service logs for details.")
        
        return all_tests_passed
    
    def get_service_info(self):
        """Get service information"""
        print(f"\n{Fore.CYAN}📋 Service Information...")
        print("=" * 80)
        
        success, output = self.run_kubectl_command([
            "kubectl", "get", "services", "--no-headers"
        ])
        
        if success:
            table_data = []
            for line in output.split('\n'):
                if line.strip() and 'kubernetes' not in line:
                    parts = line.split()
                    if len(parts) >= 4:
                        # Add service type indicator
                        service_name = parts[0]
                        if service_name == "frontend":
                            type_icon = "🌐 HTTP"
                        elif service_name.startswith("gomall-"):
                            type_icon = "🗄️  Middleware"
                        else:
                            type_icon = "⚡ gRPC"
                        
                        table_data.append([
                            f"{type_icon} {parts[0]}",  # Name with icon
                            parts[1],  # Type
                            parts[2],  # Cluster-IP
                            parts[3],  # External-IP
                            parts[4] if len(parts) > 4 else "",  # Port(s)
                        ])
            
            headers = ["Service Name", "Type", "Cluster-IP", "External-IP", "Port(s)"]
            print(tabulate(table_data, headers=headers, tablefmt="grid"))
    
    def run_full_check(self) -> bool:
        """Run complete health check and tests"""
        print(f"{Fore.YELLOW}{'='*80}")
        print(f"{Fore.YELLOW}🚀 Gomall Kubernetes Health Check & Connectivity Tests")
        print(f"{Fore.YELLOW}📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{Fore.YELLOW}{'='*80}")
        
        # Check if kubeconfig exists
        if not os.path.exists(self.kubeconfig_path):
            print(f"{Fore.RED}❌ Kubeconfig file not found: {self.kubeconfig_path}")
            return False
        
        # Get service info
        self.get_service_info()
        
        # Check pod status
        pods_healthy = self.check_pods_health()
        
        # Run connectivity tests only if pods are healthy
        if pods_healthy:
            connectivity_tests_passed = self.run_connectivity_tests()
        else:
            print(f"\n{Fore.YELLOW}⏭️  Skipping connectivity tests due to unhealthy pods")
            connectivity_tests_passed = False
        
        # Final summary
        print(f"\n{Fore.CYAN}📊 Summary:")
        print("=" * 80)
        
        if pods_healthy and connectivity_tests_passed:
            print(f"{Fore.GREEN}🎉 All checks passed! Gomall application is healthy.")
            print(f"{Fore.GREEN}✅ All pods are running")
            print(f"{Fore.GREEN}✅ All services are accessible")
            return True
        else:
            print(f"{Fore.RED}⚠️  Some checks failed:")
            if not pods_healthy:
                print(f"{Fore.RED}   - Pod health issues detected")
            if not connectivity_tests_passed:
                print(f"{Fore.RED}   - Service connectivity issues detected")
            return False

def main():
    """Main function"""
    # Change to script directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)
    
    monitor = KubernetesMonitor()
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "--pods-only":
            monitor.check_pods_health()
        elif sys.argv[1] == "--connectivity-only":
            monitor.run_connectivity_tests()
        elif sys.argv[1] == "--services":
            monitor.get_service_info()
        else:
            print("Usage: python k8s_monitor_fixed.py [--pods-only|--connectivity-only|--services]")
    else:
        monitor.run_full_check()

if __name__ == "__main__":
    main() 