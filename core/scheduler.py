#!/usr/bin/env python3
"""
Scheduler - Handles scheduled tasks like backups and restarts.
"""
import json
import time
import signal
import atexit
from datetime import datetime, timedelta
from pathlib import Path
import threading
from typing import List, Dict, Optional, Callable

# Assume logger is passed or imported
# from core.logger import EnhancedLogger
# Assume managers are passed or imported for execution
# from managers.server_manager import ServerManager
# from managers.world_manager import WorldManager
# from utils.helpers import get_server_directory


class Scheduler:
    """Manages scheduled tasks like backups and restarts."""

    # Singleton instance for signal handler access
    _instance: Optional['Scheduler'] = None

    def __init__(self, config_dir: Path, logger=None, server_manager=None, world_manager=None):
        """Initialize the Scheduler.

        Args:
            config_dir: Path to the configuration directory
            logger: Logger instance for logging messages
            server_manager: ServerManager instance for server operations
            world_manager: WorldManager instance for world operations
        """
        self.schedule_file = config_dir / "schedule.json"
        self.logger = logger
        self.server_manager = server_manager
        self.world_manager = world_manager
        self.tasks = self._load_schedule()
        self.running = False
        self.thread = None
        self.check_interval = 60  # Check every 60 seconds
        self._lock = threading.Lock()  # Thread safety
        self._shutdown_event = threading.Event()  # For graceful shutdown
        self._shutdown_callbacks: List[Callable] = []  # Callbacks to run on shutdown

        # Set singleton for signal handler access
        Scheduler._instance = self

    def _log(self, level: str, message: str):
        """Log a message using the logger or print to console.

        Args:
            level: Log level (INFO, ERROR, WARNING, etc.)
            message: Message to log
        """
        if self.logger:
            self.logger.log(level, message)
        else:
            print(f"[{level}] {message}")

    def register_shutdown_callback(self, callback: Callable) -> None:
        """Register a callback to be called during shutdown.

        Args:
            callback: Function to call during shutdown (no arguments)
        """
        if callback not in self._shutdown_callbacks:
            self._shutdown_callbacks.append(callback)

    def unregister_shutdown_callback(self, callback: Callable) -> None:
        """Unregister a shutdown callback.

        Args:
            callback: Function to remove from callbacks
        """
        if callback in self._shutdown_callbacks:
            self._shutdown_callbacks.remove(callback)

    def graceful_shutdown(self, signum: Optional[int] = None, frame=None) -> None:
        """Perform graceful shutdown of the scheduler and registered components.

        This method can be used as a signal handler or called directly.

        Args:
            signum: Signal number (optional, for signal handler compatibility)
            frame: Current stack frame (optional, for signal handler compatibility)
        """
        if signum:
            self._log('INFO', f'Received signal {signum}, initiating graceful shutdown...')
        else:
            self._log('INFO', 'Initiating graceful shutdown...')

        # Signal shutdown to the scheduler loop
        self._shutdown_event.set()

        # Stop the scheduler
        self.stop()

        # Run all registered shutdown callbacks
        for callback in self._shutdown_callbacks:
            try:
                self._log('INFO', f'Running shutdown callback: {callback.__name__}')
                callback()
            except Exception as e:
                self._log('ERROR', f'Error in shutdown callback {callback.__name__}: {e}')

        # Save current schedule state
        try:
            self._save_schedule()
            self._log('INFO', 'Schedule saved during shutdown')
        except Exception as e:
            self._log('ERROR', f'Failed to save schedule during shutdown: {e}')

        self._log('INFO', 'Graceful shutdown complete')

    def setup_signal_handlers(self) -> None:
        """Set up signal handlers for graceful shutdown.

        This should be called from the main thread.
        """
        try:
            # Handle SIGINT (Ctrl+C) and SIGTERM
            signal.signal(signal.SIGINT, self.graceful_shutdown)
            signal.signal(signal.SIGTERM, self.graceful_shutdown)

            # Register atexit handler as fallback
            atexit.register(self._atexit_handler)

            self._log('INFO', 'Signal handlers registered for graceful shutdown')
        except Exception as e:
            self._log('WARNING', f'Could not set up signal handlers: {e}')

    def _atexit_handler(self) -> None:
        """Handler called at program exit."""
        if self.running:
            self._log('INFO', 'Atexit handler: stopping scheduler')
            self.stop()

    @classmethod
    def get_instance(cls) -> Optional['Scheduler']:
        """Get the singleton scheduler instance.

        Returns:
            The scheduler instance or None if not created
        """
        return cls._instance

    def _load_schedule(self) -> List[Dict]:
        """Load schedule from JSON file.
        
        Returns:
            List of scheduled tasks
        """
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
        """Add a new scheduled task.
        
        Args:
            task_type: Type of task ('backup', 'restart')
            server_name: Name of the server
            frequency: Frequency of task ('hourly', 'daily', 'weekly@day')
            time_str: Time for daily/weekly tasks (HH:MM format)
        """
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
        """Removes a task by its ID.
        
        Args:
            task_id: ID of the task to remove
            
        Returns:
            True if task was removed, False if not found
        """
        initial_len = len(self.tasks)
        self.tasks = [task for task in self.tasks if task.get("id") != task_id]
        if len(self.tasks) < initial_len:
             self._save_schedule()
             self._log('SUCCESS', f"Removed scheduled task ID {task_id}")
             return True
        self._log('WARNING', f"Task ID {task_id} not found.")
        return False
         
    def toggle_task(self, task_id: int) -> bool:
        """Enables or disables a task by its ID.
        
        Args:
            task_id: ID of the task to toggle
            
        Returns:
            True if task was toggled, False if not found
        """
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
        """Returns the list of configured tasks.
        
        Returns:
            List of configured tasks
        """
        return self.tasks

    def _should_run(self, task: Dict, now: datetime) -> bool:
        """Check if a task is due to run.
        
        Args:
            task: Task dictionary
            now: Current datetime
            
        Returns:
            True if task should run, False otherwise
        """
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
        """Execute the scheduled task.

        Args:
            task: Task dictionary to execute
        """
        task_type = task.get("type")
        server_name = task.get("server")

        if not server_name:
            self._log('ERROR', "Server name is None for scheduled task.")
            return

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
                      # Save current server context and switch to target server
                      original_server = self.server_manager.get_current_server()
                      if original_server != server_name:
                          self.server_manager.set_current_server(server_name)

                      self._log('INFO', f"Stopping server {server_name} for scheduled restart...")
                      stopped = self.server_manager.stop_server()
                      if stopped:
                           self._log('INFO', "Waiting briefly before restarting...")
                           time.sleep(10)
                           self._log('INFO', f"Starting server {server_name} after scheduled restart...")
                           success = self.server_manager.start_server()
                      else:
                           self._log('ERROR', f"Failed to stop server {server_name} for restart.")

                      # Restore original server context if different
                      if original_server and original_server != server_name:
                          self.server_manager.set_current_server(original_server)
                 except Exception as e:
                      self._log('ERROR', f"Error during scheduled restart: {e}")
            else:
                 self._log('ERROR', "ServerManager not available for restart task.")
        else:
            self._log('WARNING', f"Unknown scheduled task type: {task_type}")

    def start(self):
        """Start the scheduler thread."""
        with self._lock:
            if self.running:
                self._log('WARNING', 'Scheduler is already running')
                return
            
            self.running = True
            self.thread = threading.Thread(
                target=self._scheduler_loop,
                daemon=True,
                name="MSM-Scheduler"
            )
            self.thread.start()
            self._log('INFO', 'Scheduler started')

    def stop(self):
        """Stop the scheduler thread."""
        with self._lock:
            if not self.running:
                return
            
            self.running = False
            if self.thread and self.thread.is_alive():
                self.thread.join(timeout=5)
                if self.thread.is_alive():
                    self._log('WARNING', 'Scheduler thread did not stop gracefully')
            self._log('INFO', 'Scheduler stopped')

    def _scheduler_loop(self):
        """Main scheduler loop that runs in a separate thread."""
        self._log('INFO', 'Scheduler loop started')

        while self.running and not self._shutdown_event.is_set():
            try:
                now = datetime.now()

                for task in self.tasks:
                    # Check for shutdown between task executions
                    if self._shutdown_event.is_set():
                        break

                    if self._should_run(task, now):
                        try:
                            self._execute_task(task)
                            # Update last run time
                            task['last_run_dt'] = now
                            task['last_run'] = now.isoformat()
                            self._save_schedule()
                        except Exception as e:
                            self._log('ERROR', f'Error executing task {task.get("id")}: {e}')

                # Use event wait instead of sleep for responsive shutdown
                # This will return immediately if shutdown_event is set
                self._shutdown_event.wait(timeout=self.check_interval)

            except Exception as e:
                self._log('ERROR', f'Error in scheduler loop: {e}')
                # Use event wait for error recovery too
                self._shutdown_event.wait(timeout=self.check_interval)

        self._log('INFO', 'Scheduler loop stopped')