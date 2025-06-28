#!/usr/bin/env python3
"""
VSCode CPU Spike Monitor
========================
Real-time monitoring to catch what causes 99% CPU spikes when typing
"""

import psutil
import time
import subprocess
import threading
from datetime import datetime

class VSCodeCPUMonitor:
    def __init__(self):
        self.monitoring = False
        self.spike_threshold = 80  # CPU % threshold
        self.vscode_processes = []
        
    def find_vscode_processes(self):
        """Find all VSCode Insiders processes"""
        processes = []
        for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'cpu_percent']):
            try:
                if 'code-insiders' in proc.info['name']:
                    processes.append(proc)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        return processes
    
    def get_process_details(self, proc):
        """Get detailed process information"""
        try:
            cmdline = ' '.join(proc.cmdline())
            
            # Identify process type
            if '--type=zygote' in cmdline:
                proc_type = 'Zygote'
            elif '--type=utility' in cmdline:
                proc_type = 'Utility'
            elif '--type=renderer' in cmdline:
                proc_type = 'Renderer'
            elif '--type=gpu-process' in cmdline:
                proc_type = 'GPU'
            elif '--type=extensionHost' in cmdline:
                proc_type = 'Extension Host'
            else:
                proc_type = 'Main'
                
            return {
                'pid': proc.pid,
                'type': proc_type,
                'cpu_percent': proc.cpu_percent(interval=0.1),
                'memory_mb': proc.memory_info().rss / (1024 * 1024),
                'cmdline': cmdline[:100] + '...' if len(cmdline) > 100 else cmdline
            }
        except Exception as e:
            return None
    
    def monitor_cpu_spikes(self):
        """Monitor for CPU spikes in real-time"""
        print("🔍 MONITORING VSCODE CPU SPIKES...")
        print("Press Ctrl+C to stop monitoring")
        print("Start typing in VSCode to trigger spikes...\n")
        
        spike_count = 0
        
        try:
            while self.monitoring:
                vscode_procs = self.find_vscode_processes()
                
                if not vscode_procs:
                    print("❌ No VSCode Insiders processes found")
                    time.sleep(2)
                    continue
                
                high_cpu_procs = []
                total_cpu = 0
                
                for proc in vscode_procs:
                    details = self.get_process_details(proc)
                    if details and details['cpu_percent'] > 10:
                        high_cpu_procs.append(details)
                        total_cpu += details['cpu_percent']
                
                if total_cpu > self.spike_threshold:
                    spike_count += 1
                    timestamp = datetime.now().strftime("%H:%M:%S")
                    
                    print(f"🚨 CPU SPIKE #{spike_count} at {timestamp} - Total: {total_cpu:.1f}%")
                    print("-" * 60)
                    
                    for proc in sorted(high_cpu_procs, key=lambda x: x['cpu_percent'], reverse=True):
                        print(f"  PID {proc['pid']:>6}: {proc['type']:<15} {proc['cpu_percent']:>5.1f}% CPU {proc['memory_mb']:>6.0f}MB")
                        if proc['cpu_percent'] > 50:
                            print(f"    ❌ HIGH CPU: {proc['cmdline']}")
                    
                    print()
                    
                    # Capture stack trace of highest CPU process
                    if high_cpu_procs:
                        highest_cpu_proc = max(high_cpu_procs, key=lambda x: x['cpu_percent'])
                        if highest_cpu_proc['cpu_percent'] > 70:
                            self.capture_stack_trace(highest_cpu_proc['pid'])
                
                time.sleep(0.5)  # Check every 500ms
                
        except KeyboardInterrupt:
            print(f"\n✅ Monitoring stopped. Detected {spike_count} CPU spikes.")
    
    def capture_stack_trace(self, pid):
        """Capture stack trace of high CPU process"""
        try:
            # Try to get stack trace using gdb
            result = subprocess.run(['gdb', '-batch', '-ex', 'thread apply all bt', 
                                   '-p', str(pid)], 
                                  capture_output=True, text=True, timeout=5)
            
            if result.stdout:
                print(f"    📊 Stack trace for PID {pid}:")
                lines = result.stdout.split('\n')[:10]  # First 10 lines
                for line in lines:
                    if line.strip():
                        print(f"      {line}")
                        
        except Exception as e:
            print(f"    ⚠️ Could not capture stack trace: {e}")
    
    def check_extension_host_issues(self):
        """Check for extension host specific issues"""
        print("\n🔌 CHECKING EXTENSION HOST ISSUES...")
        
        try:
            # Check extension host processes
            for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'cpu_percent']):
                try:
                    if 'code-insiders' in proc.info['name'] and '--type=extensionHost' in ' '.join(proc.info['cmdline']):
                        cpu = proc.cpu_percent(interval=1)
                        mem = proc.memory_info().rss / (1024 * 1024)
                        
                        print(f"  Extension Host PID {proc.info['pid']}: {cpu:.1f}% CPU, {mem:.0f}MB")
                        
                        if cpu > 30:
                            print(f"    ❌ HIGH CPU EXTENSION HOST DETECTED")
                            print(f"    Command: {' '.join(proc.info['cmdline'])}")
                            
                            # Try to identify problematic extensions
                            self.identify_problematic_extensions()
                            
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
                    
        except Exception as e:
            print(f"  ❌ Error checking extension host: {e}")
    
    def identify_problematic_extensions(self):
        """Try to identify which extensions are causing issues"""
        print("    🔍 Checking for problematic extensions...")
        
        try:
            # Check VSCode logs for extension errors
            log_paths = [
                "~/.config/Code - Insiders/logs",
                "~/.vscode-insiders/logs"
            ]
            
            for log_path in log_paths:
                expanded_path = os.path.expanduser(log_path)
                if os.path.exists(expanded_path):
                    # Look for recent extension errors
                    result = subprocess.run(['find', expanded_path, '-name', '*.log', '-mtime', '-1'], 
                                          capture_output=True, text=True)
                    
                    if result.stdout:
                        print(f"    📄 Recent log files found in {log_path}")
                        
        except Exception as e:
            print(f"    ⚠️ Could not check extension logs: {e}")
    
    def run_comprehensive_analysis(self):
        """Run comprehensive CPU spike analysis"""
        print("🔬 VSCODE CPU SPIKE ANALYSIS")
        print("=" * 50)
        
        # Initial process check
        vscode_procs = self.find_vscode_processes()
        print(f"Found {len(vscode_procs)} VSCode processes")
        
        if not vscode_procs:
            print("❌ No VSCode Insiders processes running")
            print("💡 Start VSCode Insiders and run this script again")
            return
        
        # Show current state
        print("\n📊 CURRENT PROCESS STATE:")
        total_cpu = 0
        for proc in vscode_procs:
            details = self.get_process_details(proc)
            if details:
                total_cpu += details['cpu_percent']
                print(f"  PID {details['pid']:>6}: {details['type']:<15} {details['cpu_percent']:>5.1f}% CPU")
        
        print(f"\nTotal VSCode CPU usage: {total_cpu:.1f}%")
        
        if total_cpu > 50:
            print("🚨 HIGH CPU USAGE DETECTED - Starting real-time monitoring...")
            self.check_extension_host_issues()
        
        # Start monitoring
        self.monitoring = True
        monitor_thread = threading.Thread(target=self.monitor_cpu_spikes)
        monitor_thread.daemon = True
        monitor_thread.start()
        
        try:
            monitor_thread.join()
        except KeyboardInterrupt:
            self.monitoring = False
            print("\n✅ Analysis complete")

if __name__ == "__main__":
    import os
    monitor = VSCodeCPUMonitor()
    monitor.run_comprehensive_analysis()
