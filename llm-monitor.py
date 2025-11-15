#!/usr/bin/env python3
"""
Simple LLM Monitor for FiveM Server
==================================
Works with: PS G:\FiveM\txData> G:\FiveM\fxArtifact\FXServer.exe +exec server.cfg

This script provides:
- Read server logs 
- Queue commands for manual typing
- Check server status
"""

import time
import json
from datetime import datetime
from pathlib import Path

class ServerMonitor:
    def __init__(self):
        self.log_file = Path("G:/FiveM/txData/default/logs/fxserver.log")
        self.queue_file = Path("G:/FiveM/server-control/llm-commands.txt")
        
        # Create queue directory if needed
        self.queue_file.parent.mkdir(exist_ok=True)
    
    def read_logs(self, lines=20):
        """Read recent server logs"""
        if not self.log_file.exists():
            return ["Log file not found. Server may not be started yet."]
        
        try:
            with open(self.log_file, 'r', encoding='utf-8', errors='ignore') as f:
                all_lines = f.readlines()
                recent_lines = all_lines[-lines:]
                return [line.strip() for line in recent_lines if line.strip()]
        except Exception as e:
            return [f"Error reading logs: {e}"]
    
    def queue_command(self, command):
        """Queue a command for LLM"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        command_line = f"[{timestamp}] LLM: {command}"
        
        with open(self.queue_file, 'a') as f:
            f.write(command_line + "\n")
        
        return f"Command queued: {command}"
    
    def check_server(self):
        """Check if server appears to be running"""
        logs = self.read_logs(5)
        
        # Look for recent activity
        recent_activity = any(
            line.lower().startswith(('[', 'script:')) and 
            datetime.now().minute in [int(time.strftime("%M")) % 60]  # Simple check
            for line in logs[-10:]
        )
        
        return {
            "logs_available": bool(logs and not logs[0].startswith("Log file not found")),
            "recent_activity": recent_activity,
            "log_count": len(logs)
        }

def main():
    monitor = ServerMonitor()
    
    print("FiveM Server LLM Monitor")
    print("=" * 30)
    print("Working with your server startup:")
    print("PS G:\\FiveM\\txData> G:\\FiveM\\fxArtifact\\FXServer.exe +exec server.cfg")
    print()
    
    # Check server status
    status = monitor.check_server()
    print(f"Server Status:")
    print(f"  Logs available: {status['logs_available']}")
    print(f"  Recent activity: {status['recent_activity']}")
    print(f"  Log entries: {status['log_count']}")
    
    # Read recent logs
    print(f"\nRecent Server Logs:")
    logs = monitor.read_logs(10)
    for log in logs[-5:]:
        if log and not log.startswith("Log file not found"):
            print(f"  {log}")
    
    # Queue example commands
    print(f"\nLLM Commands Queued:")
    commands = ["status", "restart ajd-crafting", "players"]
    for cmd in commands:
        result = monitor.queue_command(cmd)
        print(f"  {result}")
    
    print(f"\nInstructions:")
    print(f"1. Start your server normally")
    print(f"2. Check commands in: {monitor.queue_file}")
    print(f"3. Type commands manually in server console")
    print(f"4. Run this script anytime to monitor server")

if __name__ == "__main__":
    main()
