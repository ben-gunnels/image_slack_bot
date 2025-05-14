import requests
import time
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Dropbox API credentials from .env file
CLIENT_ID = os.getenv("DROPBOX_APP_ID")
CLIENT_SECRET = os.getenv("DROPBOX_APP_SECRET")
REFRESH_TOKEN = os.getenv("REFRESH_TOKEN")
ACCESS_TOKEN = None
TOKEN_EXPIRES_AT = 0

# Function to refresh the access token
def refresh_access_token():
    global ACCESS_TOKEN, TOKEN_EXPIRES_AT

    url = "https://api.dropbox.com/oauth2/token"
    data = {
        "grant_type": "refresh_token",
        "refresh_token": REFRESH_TOKEN,
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
    }

    try:
        response = requests.post(url, data=data)
        response.raise_for_status()  # Raises an error for non-200 status codes
        token_data = response.json()
        ACCESS_TOKEN = token_data.get("access_token")
        expires_in = token_data.get("expires_in")

        if ACCESS_TOKEN is None:
            raise Exception("Failed to obtain access token. Response: " + response.text)

        # Calculate token expiry time (current time + expiry duration)
        TOKEN_EXPIRES_AT = time.time() + expires_in if expires_in else time.time() + 3600
        print("Access token refreshed successfully!")

    except requests.RequestException as e:
        raise Exception(f"Failed to refresh access token: {str(e)}")

# Function to get a valid access token
def get_access_token():
    global ACCESS_TOKEN, TOKEN_EXPIRES_AT

    if ACCESS_TOKEN is None or time.time() >= TOKEN_EXPIRES_AT:
        refresh_access_token()

    return ACCESS_TOKEN

# Function to upload file to Dropbox
def upload_file_to_dropbox(file_path, dropbox_path):
    try:
        access_token = get_access_token()
        url = "https://content.dropboxapi.com/2/files/upload"

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/octet-stream",
            "Dropbox-API-Arg": f'{{"path": "{dropbox_path}","mode": "add","autorename": true,"mute": false,"strict_conflict": false}}'
        }

        with open(file_path, "rb") as file:
            response = requests.post(url, headers=headers, data=file)
            response.raise_for_status()  # Raises an error for non-200 status codes

        print("File uploaded successfully!")
        print(response.json())

    except FileNotFoundError:
        print(f"File not found: {file_path}")
    except requests.RequestException as e:
        print(f"Failed to upload file. Error: {str(e)}")
    except Exception as e:
        print(f"Unexpected error: {str(e)}")

# Example usage
if __name__ == "__main__":
    file_path = "slack_bot/image_outputs/gen_image_2025-05-14-02-09-30.png"  # Replace with your local file path
    dropbox_path = "/slack_images/gen_image_2025-05-14-02-09-30.png"  # Dropbox destination path

    try:
        upload_file_to_dropbox(file_path, dropbox_path)
    except Exception as e:
        print(f"Error: {e}")
