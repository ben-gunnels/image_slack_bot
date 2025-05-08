import os
from flask import Flask, request, jsonify
from EventHandler import EventHandler
import logging
import threading
import time
import base64
import hmac
import hashlib
import requests
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad
from dotenv import load_dotenv
import hashlib, hmac, base64, json, uuid

load_dotenv()

if os.path.exists("app.log"):
    os.remove("app.log")

# Basic config
logging.basicConfig(
    filename="app.log",
    level=logging.INFO,
    format='%(asctime)s %(levelname)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

app = Flask(__name__)

events_of_interest = set({"app_mention"})

# YOUR APP credentials
APP_ID = os.getenv("APP_ID")
APP_SECRET = os.getenv("APP_SECRET")
TEMP_TOKEN = os.getenv("TEMP_TOKEN")

# Decryption function
def decrypt_secret_key(encrypted_key_b64, secret):
    encrypted_key = base64.b64decode(encrypted_key_b64)
    key = hashlib.sha256(secret.encode()).digest()
    cipher = AES.new(key, AES.MODE_ECB)
    decrypted = unpad(cipher.decrypt(encrypted_key), AES.block_size)
    return decrypted.decode()

@app.route('/shein-callback')
def shein_callback():
    # Generate signature using HMAC-SHA256
    # token = os.getenv("TEMP_TOKEN")
     # 1️⃣ Pull the token directly from the request
    token = (
        request.args.get("tempToken")                # ?temp_token=...
        or request.form.get("tempToken")             # form-encoded POST
        or (request.get_json(silent=True) or {}).get("tempToken")  # JSON body
        or request.headers.get("X-Temp-Token")        # custom header
    )

    if not token:
        return "Authorization failed: token not provided", 400
    else:
        print("Token acquired.")

    message = APP_ID # + token
    signature = hmac.new(APP_SECRET.encode(), message.encode(), hashlib.sha256).hexdigest().upper()

    headers = {
        "x-lt-signature": signature,
        "Content-Type": "application/json"
    }

    payload = {
        "appid": APP_ID,
        "token": token
    }

    # Call the get-by-token 
    # url = "https://openapi.sheincorp.cn/open-api/auth/v1/get-by-token"

    timestamp = str(int(time.time() * 1000))
    api_path = "/open-api/auth/get-by-token"
    random_key = str(uuid.uuid4())[:5]
    random_secret_key = APP_SECRET + random_key

    # Generate Signature
    sign_string = f"{APP_ID}&{timestamp}&{api_path}"
    signature = hmac.new(random_secret_key.encode(), sign_string.encode(), hashlib.sha256).digest()
    base64_signature = base64.b64encode(signature).decode()
    signature = random_key + base64_signature

    # Set Headers
    headers = {
        "Content-Type": "application/json;charset=UTF-8",
        "x-lt-appid": APP_ID,
        "x-lt-timestamp": timestamp,
        "x-lt-signature": signature
    }

    # Request Body (with tempToken)
    payload = {
        token    
    }

    # Send Request
    url = "https://openapi-test01.sheincorp.cn/open-api/auth/get-by-token"
    response = requests.post(url, headers=headers, json=payload)

    if response.status_code != 200:
        return f"Error from SHEIN API: {response.text}", 500

    return jsonify(response.json())

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))  # Default to 5000 if not set
    app.run(host="0.0.0.0", port=port)