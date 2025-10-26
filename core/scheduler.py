#!/usr/bin/env python3
"""
Scheduler - Handles scheduled tasks like backups and restarts.
"""
import json
import time
from datetime import datetime, timedelta
from pathlib import Path
import threading
from typing import List, Dict, Optional

# Assume logger is passed or imported
# from core.logger import EnhancedLogger
# Assume managers are passed or imported for execution
# from managers.server_manager import ServerManager
# from managers.world_manager import WorldManager
# from utils.helpers import get_server_directory

class Scheduler:
    """Manages scheduled tasks."""

    def __init__(self, config_dir: Path, logger=None, server_manager=None, world_manager=None):
        self.schedule_file = config_dir / "schedule.json"
        self.logger = logger
        self.server_manager = server_manager
        self.world_manager = world_manager
        self.tasks = self._load_schedule()
        self.running = False
        self.thread = None
        self.check_interval = 60 # Check every 60 seconds

    def _log(self, level: str, message: str):
        if self.logger:
            self.logger.log(level, message)
        else:
            print(f"[{level}] {message}")

    def _load_schedule(self) -> List[Dict]:
        """Load schedule from JSON file."""
        if not self.schedule_file.exists():
            return []
        try:
            with open(self.schedule_file, 'r') as f:
                data = json.load(f)
                # Basic validation
                if isinstance(data, list):
                     # Convert timestamp strings back to datetime objects if needed
                     for task in data:
                          if 'last_run' in task and task['last_run']:
                               try: task['last_run_dt'] = datetime.fromisoformat(task['last_run'])
                               except: task['last_run_dt'] = None
                          else: task['last_run_dt'] = None
                     return data
            self._log('WARNING', 'schedule.json is not a list, starting fresh.')
            return []
        except Exception as e:
            self._log('ERROR', f"Failed to load schedule: {e}")
            return []

    def _save_schedule(self):
        """Save schedule to JSON file."""
        try:
             # Prepare data for saving (convert datetime back to string)
             tasks_to_save = []
             for task in self.tasks:
                  saved_task = task.copy()
                  if 'last_run_dt' in saved_task:
                       saved_task['last_run'] = saved_task['last_run_dt'].isoformat() if saved_task['last_run_dt'] else None
                       del saved_task['last_run_dt'] # Remove object before saving
                  tasks_to_save.append(saved_task)

             with open(self.schedule_file, 'w') as f:
                 json.dump(tasks_to_save, f, indent=2)
        except Exception as e:
            self._log('ERROR', f"Failed to save schedule: {e}")

    def add_task(self, task_type: str, server_name: str, frequency: str, time_str: Optional[str] = None):
        """Add a new scheduled task."""
        # Validation needed for frequency (e.g., 'daily', 'weekly@Mon', 'hourly') and time_str ('HH:MM')
        new_task = {
            "id": int(time.time()), # Simple unique ID
            "type": task_type, # 'backup', 'restart'
            "server": server_name,
            "frequency": frequency, # e.g., "daily", "weekly@Sun", "hourly"
            "time": time_str, # e.g., "03:00" for daily/weekly
            "enabled": True,
            "last_run": None,
            "last_run_dt": None
        }
        self.tasks.append(new_task)
        self._save_schedule()
        self._log('SUCCESS', f"Added scheduled task for {server_name}: {task_type} {frequency} {time_str or ''}")

    def remove_task(self, task_id: int) -> bool:
         """Removes a task by its ID."""
         initial_len = len(self.tasks)
         self.tasks = [task for task in self.tasks if task.get("id") != task_id]
         if len(self.tasks) < initial_len:
              self._save_schedule()
              self._log('SUCCESS', f"Removed scheduled task ID {task_id}")
              return True
         self._log('WARNING', f"Task ID {task_id} not found.")
         return False
         
    def toggle_task(self, task_id: int) -> bool:
         """Enables or disables a task by its ID."""
         for task in self.tasks:
              if task.get("id") == task_id:
                   task["enabled"] = not task.get("enabled", True)
                   self._save_schedule()
                   status = "enabled" if task["enabled"] else "disabled"
                   self._log('SUCCESS', f"Task ID {task_id} {status}.")
                   return True
         self._log('WARNING', f"Task ID {task_id} not found.")
         return False

    def list_tasks(self) -> List[Dict]:
         """Returns the list of configured tasks."""
         return self.tasks

    def _should_run(self, task: Dict, now: datetime) -> bool:
        """Check if a task is due to run."""
        if not task.get("enabled", True):
            return False

        last_run = task.get("last_run_dt")
        frequency = task.get("frequency", "").lower()
        time_str = task.get("time") # HH:MM

        try:
            target_time = None
            if time_str:
                 hour, minute = map(int, time_str.split(':'))
                 target_time = now.replace(hour=hour, minute=minute, second=0, microsecond=0)

            if frequency == "hourly":
                if not last_run or (now - last_run >= timedelta(hours=1)):
                    return True
            elif frequency == "daily":
                if target_time and now >= target_time:
                     if not last_run or last_run.date() < now.date():
                          return True
            elif frequency.startswith("weekly@"):
                 # Example: weekly@sun (Sunday = 6 in isoweekday)
                 day_map = {"mon": 0, "tue": 1, "wed": 2, "thu": 3, "fri": 4, "sat": 5, "sun": 6}
                 try:
                      target_day_str = frequency.split('@')[1][:3]
                      target_weekday = day_map[target_day_str]
                      if target_time and now >= target_time and now.weekday() == target_weekday:
                           if not last_run or last_run.date() < now.date():
                                return True
                 except (IndexError, KeyError):
                      self._log('ERROR', f"Invalid weekly frequency format: {frequency}")

            # Add more frequencies: monthly, etc.

        except Exception as e:
            self._log('ERROR', f"Error checking schedule for task {task.get('id')}: {e}")

        return False

    def _execute_task(self, task: Dict):
        """Execute the scheduled task."""
        task_type = task.get("type")
        server_name = task.get("server")

        self._log('INFO', f"Executing scheduled task for {server_name}: {task_type}")

        success = False
        if task_type == "backup":
            if self.world_manager:
                 # Need server path - requires helper function or ConfigManager access
                 try:
                      from utils.helpers import get_server_directory # Local import
                      server_path = get_server_directory(server_name)
                      success = self.world_manager.create_backup(server_name, server_path)
                 except ImportError:
                      self._log('ERROR', "Cannot execute backup: utils.helpers not found.")
                 except Exception as e:
                      self._log('ERROR', f"Error during scheduled backup: {e}")
            else:
                 self._log('ERROR', "WorldManager not available for backup task.")
        elif task_type == "restart":
            if self.server_manager:
                 try:
                      self._log('INFO', f"Stopping server {server_name} for scheduled restart...")
                      stopped = self.server_manager.stop_server(force_after_timeout=True) # Add optional force
                      if stopped:
                           self._log('INFO', "Waiting briefly before restarting...")
                           time.sleep(10)
                           self._log('INFO', f"Starting server {server_name} after scheduled restart...")
                           success = self.server_manager.start_server()
                      else:
                           self._log('ERROR', f"Failed to stop server {server_name} for restart.")
                 except Exception as e:
                      self._log('ERROR', f"Error during scheduled restart: {e}")
            else:
                 self._log('ERROR', "ServerManager not available for restart task.")
        else:
            self._log('WARNING', f"Unknown scheduled task type: {task_type}")

        if success:
             task['last_run_dt'] = datetime.now()
             self._save_schedule() # Save updated last run time
        else:
             self._log('ERROR', f"Scheduled task '{task_type}' for '{server_name}' failed.")


    def check_and_run_tasks(self):
        """Iterate through tasks and run if due."""
        now = datetime.now()
        for task in self.tasks:
            if self._should_run(task, now):
                self._execute_task(task)

    def _scheduler_loop(self):
        """Background thread loop."""
        self._log('INFO', "Scheduler background thread started.")
        while self.running:
            try:
                self.check_and_run_tasks()
            except Exception as e:
                self._log('ERROR', f"Error in scheduler loop: {e}")
            
            # Sleep until the next check interval
            # More precise sleep would calculate time until next minute/hour boundary
            time.sleep(self.check_interval) 
        self._log('INFO', "Scheduler background thread stopped.")

    def start(self):
        """Start the scheduler background thread."""
        if not self.running:
            self.running = True
            self.thread = threading.Thread(target=self._scheduler_loop, daemon=True)
            self.thread.start()

    def stop(self):
        """Stop the scheduler background thread."""
        if self.running:
            self.running = False
            if self.thread:
                # No forceful join, allow daemon thread to exit naturally
                pass 
            self._log('INFO', "Scheduler stop requested.")