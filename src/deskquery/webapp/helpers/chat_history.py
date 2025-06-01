# std lib imports
import os, json
from pathlib import Path
from datetime import datetime

# set base_path to chat history storage
BASE_DIR = Path(__file__).resolve().parents[1]
HISTORY_DIR = BASE_DIR / "chat_history_storage"


class Chat:
    def __init__(self, chat_id, title="Neuer Chat", messages=None, created_at=None, last_updated=None):
        self.chat_id = chat_id
        self.title = title
        self.messages = messages if messages is not None else []
        self.created_at = created_at or datetime.utcnow().isoformat()
        self.last_updated = last_updated or self.created_at

    @classmethod
    def load(cls, chat_id):
        path = HISTORY_DIR / f"{chat_id}.json"
        if not path.exists():
            return None
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return cls(
                chat_id=data["chat_id"],
                title=data.get("title", "Neuer Chat"),
                messages=data.get("messages", []),
                created_at=data.get("created_at"),
                last_updated=data.get("last_updated", data.get("created_at"))
            )

    def append_message(self, role, content, status=None, data=None):
        next_id = self.messages[-1]["id"] + 1 if self.messages else 1
        msg = {
            "id": next_id,
            "role": role,
            "content": content
        }
        if status:
            msg["status"] = status
        if data:
            msg["data"] = data
        self.messages.append(msg)
        self.last_updated = datetime.utcnow().isoformat()
        self.save()

    def rename(self, new_title):
        self.title = new_title
        self.save()

    def delete(self):
        path = HISTORY_DIR / f"{self.chat_id}.json"
        if path.exists():
            os.remove(path)
            return True
        return False

    def save(self):
        os.makedirs(HISTORY_DIR, exist_ok=True)
        with open(HISTORY_DIR / f"{self.chat_id}.json", "w", encoding="utf-8") as f:
            json.dump({
                "chat_id": self.chat_id,
                "title": self.title,
                "messages": self.messages,
                "created_at": self.created_at,
                "last_updated": self.last_updated
            }, f, ensure_ascii=False, indent=2)


    def to_dict(self):
        return {
            "chat_id": self.chat_id,
            "title": self.title,
            "created_at": self.created_at,
            "last_updated": self.last_updated
        }


    def get_message(self, message_id):
        return next((m for m in self.messages if m["id"] == message_id), None)


    def get_message_text(self, message_id):
        msg = self.get_message(message_id)
        return msg["content"] if msg else None


    def get_message_data(self, message_id):
        msg = self.get_message(message_id)
        return msg.get("data") if msg and "data" in msg else None


    def get_all_texts(self):
        return [m["content"] for m in self.messages if m["role"] in ("user", "assistant")]


    def get_all_data(self):
        return [m["data"] for m in self.messages if "data" in m]


    def get_text_data_pairs(self):
        return [
            {"id": m["id"], "text": m["content"], "data": m.get("data")}
            for m in self.messages
        ]


def list_chats():
    os.makedirs(HISTORY_DIR, exist_ok=True)
    chats = []

    for file in HISTORY_DIR.glob("*.json"):
        chat = Chat.load(file.stem)
        if chat:
            chats.append(chat.to_dict())

    chats.sort(key=lambda c: c["last_updated"], reverse=True)
    return chats