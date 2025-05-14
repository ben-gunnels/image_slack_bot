import requests
from requests.auth import HTTPBasicAuth
from dotenv import load_dotenv
import os

load_dotenv()

# Your Dropbox App Credentials
APP_KEY = os.getenv("DROPBOX_APP_KEY")
APP_SECRET = os.getenv("DROPBOX_APP_SECRET")

# Replace this with the code you copied from the URL
AUTHORIZATION_CODE = os.getenv("DROPBOX_AUTHORIZATION_CODE")

# API URL for Dropbox OAuth
token_url = "https://api.dropboxapi.com/oauth2/token"

# Request payload
data = {
    "code": AUTHORIZATION_CODE,
    "grant_type": "authorization_code",
    "redirect_uri": "https://localhost"
}

# Make the request with Basic Authentication (App Key + App Secret)
response = requests.post(
    token_url,
    data=data,
    auth=HTTPBasicAuth(APP_KEY, APP_SECRET)
)

if response.status_code == 200:
    print("Successfully obtained refresh token!")
    print(response.json())
else:
    print("Failed to obtain refresh token.")
    print(response.text)
