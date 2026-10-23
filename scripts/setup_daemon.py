#!/usr/bin/env python3
"""
macOS launchd Daemon Manager for Telegram Companion Bot.
Allows the bot to run continuously in the background on your Mac across logins.

Usage:
    # Install and start background service
    python -m scripts.setup_daemon install

    # Check service status
    python -m scripts.setup_daemon status

    # Stop and uninstall service
    python -m scripts.setup_daemon uninstall
"""

from __future__ import annotations

import argparse
from pathlib import Path
import plistlib
import subprocess
import sys

# Add project root to sys.path
root_dir = Path(__file__).resolve().parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

LABEL = "com.kieran.telegram_journal_bot"
PLIST_PATH = Path.home() / "Library" / "LaunchAgents" / f"{LABEL}.plist"


def get_python_binary() -> str:
    """Find the preferred conda/virtualenv Python binary."""
    conda_py = Path("/opt/anaconda3/envs/tele-journal/bin/python")
    if conda_py.exists():
        return str(conda_py)
    return sys.executable


def install_daemon() -> None:
    """Generate launchd plist and load service."""
    py_bin = get_python_binary()
    output_dir = root_dir / "output"
    output_dir.mkdir(parents=True, exist_ok=True)

    plist_data = {
        "Label": LABEL,
        "ProgramArguments": [
            py_bin,
            "-u",
            "-m",
            "scripts.run_bot",
        ],
        "WorkingDirectory": str(root_dir),
        "RunAtLoad": True,
        "KeepAlive": True,
        "StandardOutPath": str(output_dir / "bot.log"),
        "StandardErrorPath": str(output_dir / "bot.err"),
        "EnvironmentVariables": {
            "PATH": "/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin",
            "PYTHONUNBUFFERED": "1",
        },
    }

    try:
        PLIST_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(PLIST_PATH, "wb") as f:
            plistlib.dump(plist_data, f)
    except PermissionError:
        print("❌ Permission Denied writing to ~/Library/LaunchAgents!", file=sys.stderr)
        print("Your ~/Library/LaunchAgents folder is currently owned by root (system).", file=sys.stderr)
        print("\nTo fix ownership and allow user background agents, run in your terminal:", file=sys.stderr)
        print("   sudo chown -R $(whoami) ~/Library/LaunchAgents", file=sys.stderr)
        print("\nThen re-run: python -m scripts.setup_daemon install", file=sys.stderr)
        sys.exit(1)

    # Load service via launchctl
    try:
        subprocess.run(["launchctl", "unload", str(PLIST_PATH)], capture_output=True, check=False)
        subprocess.run(["launchctl", "load", "-w", str(PLIST_PATH)], check=True)
        print("=" * 60)
        print("✅ Telegram Bot Background Service Installed & Started!")
        print("=" * 60)
        print(f"📄 Plist Location: {PLIST_PATH}")
        print(f"📝 Logs:           {output_dir / 'bot.log'}")
        print("The bot will now run continuously in the background across restarts.")
    except Exception as e:
        print(f"⚠️ Could not load service via launchctl: {e}", file=sys.stderr)


def uninstall_daemon() -> None:
    """Unload service and delete launchd plist."""
    if PLIST_PATH.exists():
        try:
            subprocess.run(["launchctl", "unload", str(PLIST_PATH)], check=False)
        except Exception:
            pass
        PLIST_PATH.unlink(missing_ok=True)
        print("🛑 Telegram Bot Background Service Uninstalled successfully.")
    else:
        print("ℹ️ No background service plist found.")


def status_daemon() -> None:
    """Check running status of the daemon."""
    if not PLIST_PATH.exists():
        print(f"⚪ Service is NOT installed (plist not found at {PLIST_PATH}).")
        return

    res = subprocess.run(["launchctl", "list"], capture_output=True, text=True, check=False)
    matches = [line for line in res.stdout.splitlines() if LABEL in line]

    if matches:
        print(f"🟢 Service '{LABEL}' is currently ACTIVE in launchctl:")
        for m in matches:
            print(f"   {m}")
        log_file = root_dir / "output" / "bot.log"
        if log_file.exists():
            print(f"\nLast 5 log entries ({log_file}):")
            lines = log_file.read_text(encoding="utf-8", errors="ignore").splitlines()[-5:]
            for l in lines:
                print(f"   {l}")
    else:
        print(f"🟡 Plist exists, but service '{LABEL}' is currently not running.")


def restart_daemon() -> None:
    """Restart the daemon service to reload code and cache."""
    print("🔄 Restarting Telegram Bot Background Service...")
    install_daemon()


def main() -> None:
    parser = argparse.ArgumentParser(description="Manage background launchd service for Telegram Bot.")
    parser.add_argument(
        "action",
        choices=["install", "uninstall", "status", "restart"],
        help="Action to perform (install, uninstall, status, restart).",
    )
    args = parser.parse_args()

    if args.action in ("install", "restart"):
        install_daemon()
    elif args.action == "uninstall":
        uninstall_daemon()
    elif args.action == "status":
        status_daemon()


if __name__ == "__main__":
    main()
