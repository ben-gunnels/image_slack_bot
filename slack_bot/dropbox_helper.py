import requests
import os
import pathlib
from dotenv import load_dotenv
import json

# Load environment variables
load_dotenv()

DROPBOX_ACCESS_TOKEN = os.getenv("DROPBOX_ACCESS_TOKEN")
USER_ID = os.getenv("DROPBOX_USER_ID")
SHARED_FOLDER_ID = os.getenv("SHARED_FOLDER_ID")

def upload_to_shared_folder(file):
    if not file.exists():
        return {"error": "File does not exist"}

    # Read the file content
    file_content = file.read_bytes()
    file_name = file.name

    # Specify the Dropbox path using the shared folder ID
    dropbox_path = f"/{file_name}"  # The file will appear in the root of the shared folder

    url = "https://content.dropboxapi.com/2/files/upload"

    # Set the request headers
    headers = {
        "Authorization": f"Bearer {DROPBOX_ACCESS_TOKEN}",
        "Dropbox-API-Select-User": USER_ID,
        "Dropbox-API-Path-Root": json.dumps({
            ".tag": "namespace_id",
            "namespace_id": SHARED_FOLDER_ID
        }),
        "Content-Type": "application/octet-stream",
        "Dropbox-API-Arg": json.dumps({
            "path": dropbox_path,
            "mode": "add",
            "autorename": True,
            "mute": False
        })
    }

    print("Uploading to Dropbox Shared Folder...")
    print(f"User ID: {USER_ID}")
    print(f"Shared Folder ID: {SHARED_FOLDER_ID}")
    print(f"Dropbox Path: {dropbox_path}")

    try:
        response = requests.post(url, headers=headers, data=file_content)
        print(f"Response Status: {response.status_code}")
        print(f"Response Text: {response.text}")
        response.raise_for_status()  # This will raise an error for non-200 responses
        return {"message": "File uploaded successfully", "dropbox_path": dropbox_path}

    except requests.RequestException as e:
        print(f"Error Details: {str(e)}")
        return {"error": "Failed to upload file to Dropbox", "details": str(e)}