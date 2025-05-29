import requests
from datetime import datetime
import time
import os
from dotenv import load_dotenv
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from slack_helper import get_all_channel_ids
from utils import to_unix_timestamp

SLACK_TOKEN = os.getenv("SLACK_TOKEN")
SLACKBOT_ID = os.getenv("SLACKBOT_ID")

client = WebClient(token=SLACK_TOKEN, timeout=180)

load_dotenv()

# Function to list all files in a specific Slack channel
# def list_files_in_channel(channel_id, start_time, end_time):
#     try:
#         files = []
#         next_cursor = None

#         while True:
#             response = client.files_list(
#                 channel=channel_id,
#                 limit=1000,
#                 cursor=next_cursor,
#                 ts_from=start_time,
#                 ts_to=end_time
#             )

#             files.extend(response.get("files", []))
#             next_cursor = response.get("response_metadata", {}).get("next_cursor")

#             if not next_cursor:
#                 break

#         # Displaying file details
#         files = [file for file in files if file.get('user') == SLACKBOT_ID]
#         print(f"\nTotal Files Found: {len(files)}")
#         # for file in files:
#             # print(f"File: {file.get('name')} - URL: {file.get('url_private')} - Uploaded by: {file.get('user')}")

#         return files

#     except SlackApiError as e:
#         print(f"Error fetching files in channel: {e.response['error']}")
#         return None

def list_files_in_channel(channel_id, start_ts, end_ts, filter_by_user_id=SLACKBOT_ID):
    try:
        files = []
        has_more = True
        next_cursor = None

        while has_more:
            response = client.conversations_history(
                channel=channel_id,
                oldest=start_ts,
                latest=end_ts,
                limit=1000,
                cursor=next_cursor
            )

            messages = response['messages']
            for msg in messages:
                if 'files' in msg:
                    for f in msg['files']:
                        if not filter_by_user_id or f.get('user') == filter_by_user_id:
                            files.append({
                                'name': f.get('name'),
                                'url_private': f.get('url_private'),
                                'user': f.get('user'),
                                'timestamp': f.get('timestamp')
                            })

            next_cursor = response.get("response_metadata", {}).get("next_cursor")
            has_more = bool(next_cursor)

        print(f"\nTotal Files Found: {len(files)}")
        for i, file in enumerate(files):
            if i == 0:
                print(f"{file['name']} | Uploaded by: {file['user']} | URL: {file['url_private']}")

        return files

    except SlackApiError as e:
        print(f"Error fetching files: {e.response['error']}")
        return []

# Example Usage
if __name__ == "__main__":
    start_ts = to_unix_timestamp("2025-01-01")
    end_ts = to_unix_timestamp("2025-05-28")

    channels = get_all_channel_ids()
    print(channels)

    channel_id = input("Enter the Channel ID you want to list files for: ")
    print("\nListing All Files in Channel...")
    list_files_in_channel(channel_id, start_ts, end_ts)