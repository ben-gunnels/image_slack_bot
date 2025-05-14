import requests
import os
from dotenv import load_dotenv

load_dotenv()

# Your Dropbox access token
ACCESS_TOKEN = os.getenv("DROPBOX_API_KEY")

# The file you want to upload
file_path = "./image_outputs/gen_image_2025-05-13-02-25-06.png"

# The Dropbox path where you want to save the file
dropbox_path = "/slack_designs/gen_image_2025-05-13-02-25-06.png"

# API URL for Dropbox upload
url = "https://content.dropboxapi.com/2/files/upload"

# Set the headers for the API request
headers = {
    "Authorization": f"Bearer {ACCESS_TOKEN}",
    "Content-Type": "application/octet-stream",
    "Dropbox-API-Arg": f'{{"path": "{dropbox_path}","mode": "add","autorename": true,"mute": false,"strict_conflict": false}}'
}

# Open the file and send it in the request
with open(file_path, "rb") as file:
    response = requests.post(url, headers=headers, data=file)

# Print the response for debugging
print("Status:", response.status_code)
print("Response:", response.text)
