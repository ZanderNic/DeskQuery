# std lib imports
import os, json
from pathlib import Path

# set base_path to chat history storage
BASE_DIR = Path(__file__).resolve().parents[1]
HISTORY_DIR = BASE_DIR / "chat_history_storage"


def save_chat(chat_id, messages, title=None):
    os.makedirs(HISTORY_DIR, exist_ok=True)
    path = os.path.join(HISTORY_DIR, f"{chat_id}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump({
            "chat_id": chat_id,
            "title": title or messages[0]["content"][:30],
            "messages": messages
        }, f, ensure_ascii=False, indent=2)

def load_chat(chat_id):
    path = os.path.join(HISTORY_DIR, f"{chat_id}.json")
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return None

def list_chats():
    os.makedirs(HISTORY_DIR, exist_ok=True)
    chats = []
    
    for f in os.listdir(HISTORY_DIR):
        if f.endswith(".json"):
            with open(os.path.join(HISTORY_DIR, f), "r", encoding="utf-8") as file:
                data = json.load(file)
                chats.append({"chat_id": data["chat_id"], "title": data.get("title", data["chat_id"])})
    return chats

def delete_chat(chat_id):
    path = os.path.join(HISTORY_DIR, f"{chat_id}.json")
    if os.path.exists(path):
        os.remove(path)
        return True
    return False

def rename_chat(chat_id, new_title):
    path = os.path.join(HISTORY_DIR, f"{chat_id}.json")
    if not os.path.exists(path):
        return False
    with open(path, "r+", encoding="utf-8") as f:
        data = json.load(f)
        data["title"] = new_title
        f.seek(0)
        f.truncate()
        json.dump(data, f, ensure_ascii=False, indent=2)
    return True