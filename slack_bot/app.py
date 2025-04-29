import os
from flask import Flask, request, jsonify
from EventHandler import EventHandler
import logging
import threading

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
        if files:
            url_private = files[0].get("url_private")
        else:
            url_private = None

        if event_type in events_of_interest:
            event_handler = EventHandler(app.logger, event_type, channel_id, url_private, user, text, files)
            app.logger.info(f"{event_type} message from {user}: {text}, channel: {channel_id}, url: {url_private}")

            # Launch background thread
            threading.Thread(target=event_handler.handle_event).start()

    return '', 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))  # Default to 5000 if not set
    app.run(host="0.0.0.0", port=port)