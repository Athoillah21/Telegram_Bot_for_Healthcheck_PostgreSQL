import os
import subprocess
import requests
from datetime import datetime

BOT_TOKEN = "************************"
CHAT_ID = "****************"

BASE_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"

def send_message(chat_id, text):
    """Send a message back to the Telegram chat."""
    url = f"{BASE_URL}/sendMessage"
    payload = {"chat_id": chat_id, "text": text}
    requests.post(url, data=payload)

def send_document(chat_id, file_path):
    """Send a file (HTML report) back to the Telegram chat."""
    url = f"{BASE_URL}/sendDocument"
    with open(file_path, "rb") as file:
        files = {"document": file}
        data = {"chat_id": chat_id}
        requests.post(url, data=data, files=files)

def run_healthcheck(command_args):
    """Run the healthcheck shell script and generate the report."""
    try:
        # Parse command_args to extract dbname
        args = command_args.split()
        dbname = None
        for i in range(len(args)):
            if args[i] == "-d" and i + 1 < len(args):
                dbname = args[i + 1]
                break

        if not dbname:
            raise ValueError("Database name (-d) not found in arguments.")

        # Construct the command to run
        cmd = f"bash /home/ubuntu/healthcheck_html/generate_html.sh {command_args}"
        subprocess.run(cmd, shell=True, check=True)

        # Construct the report file path using the extracted dbname
        report_file = f"/home/ubuntu/healthcheck_html/report/db_healthcheck_report_{dbname}_{datetime.now().strftime('%Y-%m-%d')}.html"

        # Check if the report file exists
        if os.path.exists(report_file):
            return report_file
        else:
            raise FileNotFoundError(f"Report file not found: {report_file}")
    except subprocess.CalledProcessError as e:
        print(f"Error executing healthcheck script: {e}")
        return None
    except Exception as e:
        print(f"Unexpected error: {e}")
        return None

def process_healthcheck_command(message):
    """Parse and handle the /hc command."""
    try:
        # Extract command arguments
        parts = message["text"].split()
        if len(parts) < 5 or parts[0] != "/hc":
            send_message(message["chat"]["id"], "Usage: /hc -h <host> -p <port> -U <user> -d <dbname>")
            return

        # Construct the command arguments from the user's message
        command_args = " ".join(parts[1:])

        # Run the healthcheck script and get the report file path
        report_file = run_healthcheck(command_args)

        if report_file:
            # Send the report back to the user
            send_document(message["chat"]["id"], report_file)
        else:
            send_message(message["chat"]["id"], "Failed to generate the healthcheck report.")
    except Exception as e:
        print(f"Error processing /hc command: {e}")
        send_message(message["chat"]["id"], "An error occurred while processing the command.")

def handle_updates():
    """Poll for new messages from Telegram and process them."""
    last_update_id = None

    while True:
        # Get updates from the bot
        params = {"timeout": 100, "offset": last_update_id}
        response = requests.get(f"{BASE_URL}/getUpdates", params=params)
        updates = response.json().get("result", [])

        for update in updates:
            # Process each new message
            message = update.get("message")
            if message:
                if message.get("text", "").startswith("/hc"):
                    process_healthcheck_command(message)

            # Update the offset to the latest processed message
            last_update_id = update["update_id"] + 1

if __name__ == "__main__":
    handle_updates()

