import urllib.request
import json
import time
import sys
import os

sys.path.append(os.getcwd())
from bot.config import get_settings

def main():
    settings = get_settings()
    token = settings.bot_token
    offset = 0
    print("Direct listener started. Please FORWARD the message AGAIN.")
    
    while True:
        url = f"https://api.telegram.org/bot{token}/getUpdates?offset={offset}&timeout=30"
        try:
            with urllib.request.urlopen(url) as response:
                data = json.loads(response.read().decode())
                if data.get("ok"):
                    for update in data.get("result", []):
                        offset = update["update_id"] + 1
                        print(f"Update caught! ID: {update['update_id']}")
                        msg = update.get("message")
                        if msg and msg.get("forward_from_chat"):
                            chat = msg["forward_from_chat"]
                            print(f"ID FOUND: {chat['id']} (Title: {chat.get('title')})")
                            with open("found_id.txt", "w") as f:
                                f.write(str(chat['id']))
                            os._exit(0)
                        elif msg:
                            print(f"Msg from {msg['from'].get('username')}: {msg.get('text')}")
                else:
                    print(f"Error: {data}")
        except Exception as e:
            print(f"Error: {e}")
        time.sleep(1)

if __name__ == "__main__":
    main()
