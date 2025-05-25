#!/usr/bin/env python3
"""
Simple test runner for continuous monitoring
"""

import time
import sys
from k8s_monitor import KubernetesMonitor

def continuous_monitor(interval: int = 60):
    """Run monitoring continuously with specified interval"""
    monitor = KubernetesMonitor()
    
    print(f"🔄 Starting continuous monitoring every {interval} seconds...")
    print("Press Ctrl+C to stop")
    
    try:
        while True:
            print(f"\n{'='*50}")
            print(f"⏰ {time.strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"{'='*50}")
            
            # Run health check
            healthy = monitor.run_full_check()
            
            if not healthy:
                print(f"⚠️  Issues detected! Check logs above.")
            
            print(f"\n💤 Waiting {interval} seconds for next check...")
            time.sleep(interval)
            
    except KeyboardInterrupt:
        print(f"\n🛑 Monitoring stopped by user")

def quick_check():
    """Run a quick health check"""
    monitor = KubernetesMonitor()
    healthy = monitor.run_full_check()
    sys.exit(0 if healthy else 1)

def main():
    if len(sys.argv) > 1:
        if sys.argv[1] == "continuous":
            interval = int(sys.argv[2]) if len(sys.argv) > 2 else 60
            continuous_monitor(interval)
        elif sys.argv[1] == "quick":
            quick_check()
        else:
            print("Usage:")
            print("  python run_tests.py quick              # Run once")
            print("  python run_tests.py continuous [60]    # Run every N seconds")
    else:
        quick_check()

if __name__ == "__main__":
    main() 