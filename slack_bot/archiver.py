import requests
import os
from dotenv import load_dotenv
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from slack_helper import get_all_channel_ids

SLACK_TOKEN = os.getenv("SLACK_TOKEN")
SLACKBOT_ID = os.getenv("SLACKBOT_ID")

client = WebClient(token=SLACK_TOKEN, timeout=180)

load_dotenv()

# Function to list all files in a specific Slack channel
def list_files_in_channel(channel_id):
    try:
        files = []
        next_cursor = None

        while True:
            response = client.files_list(
                channel=channel_id,
                limit=1000,
                cursor=next_cursor
            )

            files.extend(response.get("files", []))
            next_cursor = response.get("response_metadata", {}).get("next_cursor")

            if not next_cursor:
                break

        # Displaying file details
        files = [file for file in files if file.get('user') == SLACKBOT_ID]
        print(f"\nTotal Files Found: {len(files)}")
        for file in files:
            print(f"File: {file.get('name')} - URL: {file.get('url_private')} - Uploaded by: {file.get('user')}")

        return files

    except SlackApiError as e:
        print(f"Error fetching files in channel: {e.response['error']}")
        return None

# Example Usage
if __name__ == "__main__":
    print("Listing Channels...")
    channels = get_all_channel_ids()
    print(channels)

    channel_id = input("Enter the Channel ID you want to list files for: ")
    print("\nListing All Files in Channel...")
    list_files_in_channel(channel_id)