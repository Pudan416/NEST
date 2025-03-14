"""
Script to run both the Tourist Guide Bot and Admin Bot simultaneously.
"""

import subprocess
import sys
import os
import time
import signal
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger("run_all")

# Store process objects
processes = []


def signal_handler(sig, frame):
    """Handle Ctrl+C gracefully."""
    logger.info("Received signal to stop. Shutting down bots...")
    for proc, name in processes:
        if proc.poll() is None:  # If process is still running
            logger.info(f"Stopping {name}...")
            proc.terminate()
            try:
                proc.wait(timeout=5)
                logger.info(f"{name} stopped gracefully.")
            except subprocess.TimeoutExpired:
                logger.warning(f"{name} did not stop gracefully. Forcing...")
                proc.kill()
    logger.info("All bots stopped.")
    sys.exit(0)


def start_bot(script_name, bot_name):
    """Start a bot process and return the process object."""
    try:
        logger.info(f"Starting {bot_name}...")
        process = subprocess.Popen(
            [sys.executable, script_name],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )
        processes.append((process, bot_name))
        logger.info(f"{bot_name} started with PID {process.pid}")
        return process
    except Exception as e:
        logger.error(f"Failed to start {bot_name}: {str(e)}")
        return None


def monitor_process_output(process, name):
    """Check if a process has output to display."""
    if process.poll() is not None:
        # Process has terminated
        logger.error(
            f"{name} has stopped unexpectedly with return code {process.returncode}"
        )
        return False

    # Check for output
    output = process.stdout.readline()
    if output:
        logger.info(f"{name}: {output.strip()}")

    return True


if __name__ == "__main__":
    # Register signal handler for Ctrl+C
    signal.signal(signal.SIGINT, signal_handler)

    # Check for environment variables
    if not os.getenv("TG_TOKEN") or not os.getenv("ADMIN_BOT_TOKEN"):
        logger.error(
            "Missing required environment variables. Please check your .env file."
        )
        sys.exit(1)

    # Start main bot
    main_bot = start_bot("run.py", "Main Tourist Guide Bot")

    # Give the main bot a moment to initialize
    time.sleep(2)

    # Start admin bot
    admin_bot = start_bot("admin_bot.py", "Admin Bot")

    # Monitor output from both bots
    logger.info("Both bots are running. Press Ctrl+C to stop.")

    try:
        # Simple loop to monitor both processes
        while True:
            if main_bot and not monitor_process_output(main_bot, "Main Bot"):
                main_bot = None

            if admin_bot and not monitor_process_output(admin_bot, "Admin Bot"):
                admin_bot = None

            # If both bots have stopped, exit
            if not main_bot and not admin_bot:
                logger.error("Both bots have stopped. Exiting.")
                break

            # Brief pause to prevent CPU overuse
            time.sleep(0.1)
    except KeyboardInterrupt:
        # This should be handled by the signal handler
        pass
