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

   # Generate timestamp and random code
    timestamp = str(int(time.time() * 1000))
    api_path = "/open-api/auth/get-by-token"
    random_key = str(uuid.uuid4())[:5]

    print(f"DEBUG: Generated timestamp: {timestamp}")
    print(f"DEBUG: Generated random code: {random_key}")

    # Generate Signature (following the exact order in the UI)
    value = f"{APP_ID}&{timestamp}&{api_path}"
    print(f"DEBUG: Signature string to be hashed: {value}")

    key = f"{APP_SECRET}{random_key}"

    # HMAC-SHA256 using the secret key
    signature = hmac.new(key.encode('utf-8'), value.encode('utf-8'), hashlib.sha256).digest().hex()
    base64_signature = base64.b64encode(signature.encode('utf-8')).decode()
    final_signature = random_key + base64_signature

    print(f"DEBUG: Generated HMAC-SHA256 signature (base64): {base64_signature}")
    print(f"DEBUG: Final signature with random code: {final_signature}")

    # Set Headers
    headers = {
        "Content-Type": "application/json;charset=UTF-8",
        "x-lt-appid": APP_ID,
        "x-lt-timestamp": timestamp,
        "x-lt-signature": final_signature,
        "language": "en"
    }

    print(f"DEBUG: Headers set for the request: {headers}")

    # Request Body (with tempToken)
    payload = {
        "tempToken": token
    }
    print(f"DEBUG: Request payload: {json.dumps(payload)}")

    # Send Request
    url = "https://openapi.sheincorp.cn/open-api/auth/get-by-token"
    print(f"INFO: Sending POST request to SHEIN API: {url}")

    try:
        response = requests.post(url, headers=headers, json=payload)
        print(f"DEBUG: SHEIN API Response status: {response.status_code}")
        print(f"DEBUG: SHEIN API Response text: {response.text}")
    except requests.RequestException as e:
        print(f"ERROR: Error sending request to SHEIN API: {str(e)}")
        return f"Error connecting to SHEIN API: {str(e)}", 500

    # Handle Response
    if response.status_code != 200:
        print(f"ERROR: Error from SHEIN API: {response.text}")
        return f"Error from SHEIN API: {response.text}", 500

    print("INFO: Successfully received response from SHEIN API")
    return jsonify(response.json())

@app.route("/")
def hello():
    return "Hello from Railway!"

@app.route('/slack/events', methods=['POST', 'GET'])
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

        print(data)

        if event_type in events_of_interest:
            event_handler = EventHandler(app.logger, event_type, channel_id, user, text, files)
            app.logger.info(f"{event_type} message from {user}: {text}, channel: {channel_id}")

            # Launch background thread
            threading.Thread(target=event_handler.handle_event).start()

    return '', 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))  # Default to 5000 if not set
    app.run(host="0.0.0.0", port=port)