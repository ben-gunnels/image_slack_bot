import os
from flask import Flask, request, jsonify
from EventHandler import EventHandler
import logging
import threading

import base64
import hmac
import hashlib
import requests
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad
from dotenv import load_dotenv

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
    url = "https://openapi.sheincorp.cn/open-api/auth/v1/get-by-token"

    response = requests.post(url, json=payload, headers=headers)
    
    if response.status_code != 200:
        print("SHEIN API Error:", response.text)
        return f"Error from SHEIN API: {response.text}", 500
    
    else:
        print("Returned from Shein API")

    data = response.json().get("data", {})
    open_key_id = data.get("openKeyId")
    encrypted_secret_key = data.get("secretKey")

    print(data)

    if not open_key_id or not encrypted_secret_key:
        return "Missing keys in response", 500

    # Decrypt the secret key
    try:
        decrypted_secret = decrypt_secret_key(encrypted_secret_key, APP_SECRET)
        print(decrypted_secret)
    except Exception as e:
        return f"Decryption failed: {str(e)}", 500

    # Return or process as needed
    return jsonify({
        "openKeyId": open_key_id,
        "secretKey": decrypted_secret
    })

@app.route("/")
def hello():
    return "Hello from Railway!"

@app.route('/slack/events', methods=['POST'])
def slack_events():
    data = request.get_json()
    
    # Slack URL verification
    if data.get("type") == "url_verification":
        return jsonify({'challenge': data['challenge']})

    # Handle message events
    # Main event callback handling
    if data.get("type") == "event_callback":
        event = data.get("event", {})
        user = event.get("user")
        text = event.get("text")
        event_type = event.get("type")
        channel_id = event.get("channel")
        files = event.get("files")

        if event_type in events_of_interest:
            event_handler = EventHandler(app.logger, event_type, channel_id, user, text, files)
            app.logger.info(f"{event_type} message from {user}: {text}, channel: {channel_id}")

            # Launch background thread
            threading.Thread(target=event_handler.handle_event).start()

    return '', 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))  # Default to 5000 if not set
    app.run(host="0.0.0.0", port=port)