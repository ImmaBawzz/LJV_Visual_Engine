"""
Checkpoint CLI Tool

Usage:
  python checkpoint_cli.py status           # Show current pipeline status
  python checkpoint_cli.py reset            # Reset checkpoint (start fresh)
  python checkpoint_cli.py log              # Show structured execution log
  python checkpoint_cli.py summary          # Show brief summary
"""

import json
import sys
from pathlib import Path
from checkpoint_manager import get_checkpoint, CHECKPOINT_FILE, STRUCTURED_LOG


def cmd_status():
    """Show detailed pipeline status."""
    cp = get_checkpoint()
    print(cp.report())


def cmd_reset():
    """Reset checkpoint and start fresh."""
    cp = get_checkpoint()
    cp.reset()
    print("✓ Checkpoint reset. Next run will start from step 1.")


def cmd_log():
    """Show structured execution log."""
    if not STRUCTURED_LOG.exists():
        print("No execution log found.")
        return

    logs = json.loads(STRUCTURED_LOG.read_text(encoding="utf-8"))
    
    print("\n" + "=" * 100)
    print("EXECUTION LOG (Structured)")
    print("=" * 100)
    
    for entry in logs:
        timestamp = entry.get("timestamp", "-")
        level = entry.get("level", "?")
        step = entry.get("step", "-")
        message = entry.get("message", "-")
        exit_code = entry.get("exit_code", "-")

        level_color = {
            "ERROR": "31",    # Red
            "WARNING": "33",  # Yellow
            "INFO": "32"      # Green
        }.get(level, "0")

        print(f"\033[{level_color}m[{level:7}]\033[0m {timestamp} | {step:40} | {message:50} | Exit: {exit_code}")
    
    print("=" * 100 + "\n")


def cmd_summary():
    """Show brief summary."""
    cp = get_checkpoint()
    completed = len(cp.get_completed_steps())
    total = len(cp.state["steps"])
    status = cp.state.get("overall_status", "unknown").upper()

    print(f"Status: {status}")
    print(f"Progress: {completed}/{total} steps completed")
    
    if cp.get_resume_point():
        print(f"Resume point: Step {cp.get_resume_point()}")
    else:
        print("All steps completed!")


def main():
    """Main CLI entry point."""
    if len(sys.argv) < 2:
        cmd_status()
        return

    cmd = sys.argv[1].lower()

    if cmd == "status":
        cmd_status()
    elif cmd == "reset":
        cmd_reset()
    elif cmd == "log":
        cmd_log()
    elif cmd == "summary":
        cmd_summary()
    else:
        print(f"Unknown command: {cmd}")
        print(__doc__)


if __name__ == "__main__":
    main()
