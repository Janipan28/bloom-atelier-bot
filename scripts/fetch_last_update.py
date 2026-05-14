import urllib.request
import json
import sys
import os

sys.path.append(os.getcwd())
from bot.config import get_settings

def main():
    settings = get_settings()
    token = settings.bot_token
    # offset=-1 to get only the last update
    url = f"https://api.telegram.org/bot{token}/getUpdates?offset=-1"
    
    print(f"Fetching last update from {url}...")
    try:
        with urllib.request.urlopen(url) as response:
            data = json.loads(response.read().decode())
            if not data.get("ok"):
                print(f"Error: {data}")
                return

            for update in data.get("result", []):
                msg = update.get("message")
                if msg:
                    print(f"Update ID: {update['update_id']}")
                    if msg.get("forward_from_chat"):
                        chat = msg["forward_from_chat"]
                        print(f"🎯 TARGET_CHANNEL_ID: {chat['id']} | Title: {chat.get('title')}")
                    else:
                        print(f"No forwarded chat info in message: {json.dumps(msg, indent=2)}")
                else:
                    print(f"Last update is not a message: {json.dumps(update, indent=2)}")
    except Exception as e:
        print(f"Request failed: {e}")

if __name__ == "__main__":
    main()
