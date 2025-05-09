# std-lib imports
import os, json
from datetime import datetime

HISTORY_DIR = "chat_history"

def save_chat(chat_id, messages, title=None):
    os.makedirs(HISTORY_DIR, exist_ok=True)
    filepath = os.path.join(HISTORY_DIR, f"{chat_id}.json")
    data = {
        "chat_id": chat_id,
        "title": title or messages[0]["content"][:30],
        "messages": messages
    }
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def load_chat(chat_id):
    filepath = os.path.join(HISTORY_DIR, f"{chat_id}.json")
    if os.path.exists(filepath):
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    return None

def list_chats():
    os.makedirs(HISTORY_DIR, exist_ok=True)
    chats = []
    for fname in sorted(os.listdir(HISTORY_DIR)):
        if fname.endswith(".json"):
            with open(os.path.join(HISTORY_DIR, fname), "r", encoding="utf-8") as f:
                data = json.load(f)
                chats.append({"chat_id": data["chat_id"], "title": data["title"]})
    return chats
