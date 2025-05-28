import os
import pathlib
import pathlib
import requests
import json
import base64
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

APP_KEY = os.getenv("DROPBOX_APP_KEY")
APP_SECRET = os.getenv("DROPBOX_APP_SECRET")
USER_ID = os.getenv("DROPBOX_USER_ID")
DROPBOX_REFRESH_TOKEN = os.getenv("DROPBOX_REFRESH_TOKEN")
DROPBOX_TOKEN_URL = "https://api.dropboxapi.com/oauth2/token"

def get_access_token(app_key, app_secret, refresh_token):
    """
    Uses the refresh token to get a new short-lived access token.
    """
    basic_auth = base64.b64encode(f"{app_key}:{app_secret}".encode()).decode()

    headers = {
        "Authorization": f"Basic {basic_auth}",
        "Content-Type": "application/x-www-form-urlencoded"
    }

    data = {
        "grant_type": "refresh_token",
        "refresh_token": refresh_token
    }

    response = requests.post(DROPBOX_TOKEN_URL, headers=headers, data=data)
    response.raise_for_status()

    return response.json()["access_token"]

def upload_to_shared_folder(file_path: str, folder_id):
    """
        Uploads a given file path to a shared dropbox folder. 
        The function must be supplied a known file ID and user id to perform this request. 
    """
    # Convert file path to a Path object
    file = pathlib.Path(file_path)
    
    if not file.exists():
        return {"error": "File does not exist"}
    
    # Exchange refresh token for short-lived access token
    try:
        access_token = get_access_token(APP_KEY, APP_SECRET, DROPBOX_REFRESH_TOKEN)
    except requests.RequestException as e:
        return {"error": "Failed to get access token", "details": str(e)}
    
    # Read the file content
    file_content = file.read_bytes()
    file_name = file.name

    # Specify the Dropbox path using the shared folder ID
    dropbox_path = f"/{file_name}"  # The file will appear in the root of the shared folder

    url = "https://content.dropboxapi.com/2/files/upload"

    # Set the request headers
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Dropbox-API-Select-User": USER_ID,
        "Dropbox-API-Path-Root": json.dumps({
            ".tag": "namespace_id",
            "namespace_id": folder_id
        }),
        "Content-Type": "application/octet-stream",
        "Dropbox-API-Arg": json.dumps({
            "path": dropbox_path,
            "mode": "add",
            "autorename": True,
            "mute": False
        })
    }

    # print("Uploading to Dropbox Shared Folder...")
    # print(f"User ID: {USER_ID}")
    # print(f"Shared Folder ID: {folder_id}")
    # print(f"Dropbox Path: {dropbox_path}")

    try:
        response = requests.post(url, headers=headers, data=file_content)
        # print(f"Response Status: {response.status_code}")
        print(f"Response Text: {response.text}")
        response.raise_for_status()  # This will raise an error for non-200 responses
        return {"message": "File uploaded successfully", "dropbox_path": dropbox_path}

    except requests.RequestException as e:
        print(f"Error Details: {str(e)}")
        return {"error": "Failed to upload file to Dropbox", "details": str(e)}