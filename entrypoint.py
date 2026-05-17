"""
Production Multi-Process Entrypoint
Launches and monitors both the FastAPI API and the Telegram Bot in a single container.
If either process crashes, this monitor exits, causing Docker/Render to auto-restart the container.
"""
import os
import subprocess
import sys
import time
import signal

def main():
    # Read dynamic port from Render environment (defaults to 8000 locally)
    port = os.environ.get("PORT", "8000")
    print(f"[Monitor] Starting FastAPI server on port {port}...")
    
    # 1. Start FastAPI server
    api_process = subprocess.Popen(
        ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", port]
    )

    print("[Monitor] Starting Telegram Bot...")
    # 2. Start Telegram Bot
    bot_process = subprocess.Popen(
        ["python", "bot.py"]
    )

    def terminate_processes(signum, frame):
        print("[Monitor] Received terminate signal. Stopping both processes...")
        api_process.terminate()
        bot_process.terminate()
        sys.exit(0)

    # Listen for shutdown signals from Docker/Render
    signal.signal(signal.SIGINT, terminate_processes)
    signal.signal(signal.SIGTERM, terminate_processes)

    # 3. Monitor loop
    try:
        while True:
            api_poll = api_process.poll()
            bot_poll = bot_process.poll()

            # If FastAPI server has exited
            if api_poll is not None:
                print(f"[Monitor] FastAPI server crashed/exited with code {api_poll}. Shutting down worker...")
                bot_process.terminate()
                sys.exit(api_poll)

            # If Telegram Bot has exited
            if bot_poll is not None:
                print(f"[Monitor] Telegram Bot crashed/exited with code {bot_poll}. Shutting down API...")
                api_process.terminate()
                sys.exit(bot_poll)

            time.sleep(3)
    except Exception as e:
        print(f"[Monitor] Unexpected error: {e}")
        api_process.terminate()
        bot_process.terminate()
        sys.exit(1)

if __name__ == "__main__":
    main()
