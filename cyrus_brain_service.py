"""
Cyrus Brain — Background launcher & Scheduled Task manager.

Runs the brain as a hidden background process in the user's desktop session
(required for UIAutomation access to VS Code windows).

Usage:
  python cyrus_brain_service.py install   — Register login task + start now
  python cyrus_brain_service.py start     — Start brain in background
  python cyrus_brain_service.py stop      — Stop running brain
  python cyrus_brain_service.py remove    — Unregister login task
  python cyrus_brain_service.py status    — Check if brain is running
"""

import os
import sys
import subprocess
import ctypes

TASK_NAME = "CyrusBrain"
LOCK_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "brain.pid")


def _brain_dir():
    return os.path.dirname(os.path.abspath(__file__))


def _pythonw():
    """Return path to pythonw.exe (windowless Python) in the venv."""
    for venv_name in ("venv", ".venv"):
        for exe in ("pythonw.exe", "python.exe"):
            path = os.path.join(_brain_dir(), venv_name, "Scripts", exe)
            if os.path.exists(path):
                return path
    # Fall back to system Python
    return sys.executable


def _brain_script():
    return os.path.join(_brain_dir(), "cyrus_brain.py")


def _read_pid():
    try:
        with open(LOCK_FILE) as f:
            return int(f.read().strip())
    except (FileNotFoundError, ValueError):
        return None


def _is_running(pid):
    if pid is None:
        return False
    try:
        # OpenProcess with PROCESS_QUERY_LIMITED_INFORMATION
        handle = ctypes.windll.kernel32.OpenProcess(0x1000, False, pid)
        if handle:
            ctypes.windll.kernel32.CloseHandle(handle)
            return True
    except Exception:
        pass
    return False


def start():
    """Start brain as a hidden background process."""
    pid = _read_pid()
    if _is_running(pid):
        print(f"Cyrus Brain is already running (PID {pid}).")
        return

    pythonw = _pythonw()
    script = _brain_script()

    # START_INFO with hidden window
    si = subprocess.STARTUPINFO()
    si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    si.wShowWindow = 0  # SW_HIDE

    proc = subprocess.Popen(
        [pythonw, script],
        cwd=_brain_dir(),
        startupinfo=si,
        creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NO_WINDOW,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    with open(LOCK_FILE, "w") as f:
        f.write(str(proc.pid))

    print(f"Cyrus Brain started (PID {proc.pid}).")


def stop():
    """Stop the running brain process."""
    pid = _read_pid()
    if not _is_running(pid):
        print("Cyrus Brain is not running.")
        if os.path.exists(LOCK_FILE):
            os.remove(LOCK_FILE)
        return

    try:
        # PROCESS_TERMINATE
        handle = ctypes.windll.kernel32.OpenProcess(0x0001, False, pid)
        if handle:
            ctypes.windll.kernel32.TerminateProcess(handle, 0)
            ctypes.windll.kernel32.CloseHandle(handle)
            print(f"Cyrus Brain stopped (PID {pid}).")
    except Exception as e:
        print(f"Failed to stop brain: {e}")

    if os.path.exists(LOCK_FILE):
        os.remove(LOCK_FILE)


def install():
    """Register a Scheduled Task to start brain at user login."""
    pythonw = _pythonw()
    script = _brain_script()

    # Remove existing task if present
    subprocess.run(
        ["schtasks", "/Delete", "/TN", TASK_NAME, "/F"],
        capture_output=True,
    )

    # Create task that runs at user logon, in user's session
    result = subprocess.run(
        [
            "schtasks", "/Create",
            "/TN", TASK_NAME,
            "/TR", f'"{pythonw}" "{script}"',
            "/SC", "ONLOGON",
            "/RL", "LIMITED",
            "/F",
        ],
        capture_output=True,
        text=True,
    )

    if result.returncode == 0:
        print(f"Scheduled task '{TASK_NAME}' registered (runs at login).")
        start()
    else:
        print(f"Failed to register task: {result.stderr.strip()}")
        print("Starting brain in background anyway...")
        start()


def remove():
    """Unregister the login task and stop the brain."""
    stop()
    result = subprocess.run(
        ["schtasks", "/Delete", "/TN", TASK_NAME, "/F"],
        capture_output=True,
        text=True,
    )
    if result.returncode == 0:
        print(f"Scheduled task '{TASK_NAME}' removed.")
    else:
        print(f"No scheduled task to remove.")


def status():
    """Check if the brain is running."""
    pid = _read_pid()
    if _is_running(pid):
        print(f"Cyrus Brain is running (PID {pid}).")
    else:
        print("Cyrus Brain is not running.")
        if os.path.exists(LOCK_FILE):
            os.remove(LOCK_FILE)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    cmd = sys.argv[1].lower().lstrip("-/")
    commands = {
        "install": install,
        "start": start,
        "stop": stop,
        "remove": remove,
        "uninstall": remove,
        "status": status,
    }

    fn = commands.get(cmd)
    if fn:
        fn()
    else:
        print(f"Unknown command: {cmd}")
        print(f"Valid commands: {', '.join(commands)}")
        sys.exit(1)
