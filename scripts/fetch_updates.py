import urllib.request
import json
import sys
import os

# Add parent dir to path to import bot.config
sys.path.append(os.getcwd())

from bot.config import get_settings

def main():
    settings = get_settings()
    token = settings.bot_token
    url = f"https://api.telegram.org/bot{token}/getUpdates"
    
    print(f"Fetching updates from {url}...")
    try:
        with urllib.request.urlopen(url) as response:
            data = json.loads(response.read().decode())
            
            if not data.get("ok"):
                print(f"Error: {data}")
                return

            found = False
            for update in data.get("result", []):
                chat = None
                source = ""
                if "message" in update:
                    chat = update["message"]["chat"]
                    source = "Message"
                elif "channel_post" in update:
                    chat = update["channel_post"]["chat"]
                    source = "Channel Post"
                elif "my_chat_member" in update:
                    chat = update["my_chat_member"]["chat"]
                    source = "Member Update"
                    
                if chat:
                    print(f"[{source}] FOUND CHAT: {chat['id']} | Title: {chat.get('title')} | Type: {chat['type']}")
                    found = True
            
            if not found:
                print("No chats found in recent updates.")
    except Exception as e:
        print(f"Request failed: {e}")

if __name__ == "__main__":
    main()
