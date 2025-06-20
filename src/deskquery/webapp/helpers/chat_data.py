# std lib imports
import os, json
from pathlib import Path
import datetime
from typing import Dict, List, Optional, Any
import uuid

# third party imports
import plotly.io as pio

# project imports
from deskquery.functions.function_registry import plot_function_registry
from deskquery.functions.types import *

# set base_path to chat history storage
BASE_DIR = Path(__file__).resolve().parents[1]
HISTORY_DIR = BASE_DIR / "chat_history_storage"


class ChatData:
    """
    A class to represent the chat data structure stored in the chat history
    storage and facilitate operations on the chat.
    """

    def __init__(
        self,
        chat_id: Optional[str] = str(uuid.uuid4()),
        title: Optional[str] = "New Chat",
        messages: Optional[List[Dict[str, str]]] = [],
        created_at: Optional[datetime.datetime] = datetime.datetime.now(datetime.timezone.utc),
        last_timestamp: Optional[datetime.datetime] = None,
    ):
        """
        Initializes a ChatData instance with the provided data.

        Args:
            chat_id (str, optional):
                The unique identifier for the chat. Defaults to 
                `str(uuid.uuid4())` if not provided.
            title (str, optional):
                The title of the chat. Defaults to 'New Chat'.
            messages (list, optional):
                A list of messages in the chat. Defaults to an empty list.
            created_at (datetime, optional):
                The creation timestamp of the chat. Defaults to 
                `datetime.datetime.now(datetime.timezone.utc)` if not provided.
            last_timestamp (datetime, optional):
                The last timestamp of the chat. Defaults to the value of 
                `created_at` if not provided.
        """
        self.chat_id = chat_id
        self.title = title
        self.messages = messages
        self.created_at = created_at
        self.last_timestamp = last_timestamp or created_at

    def __getitem__(
        self,
        key: str,
    ) -> Optional[str]:
        """
        Retrieves the value of the specified key from the chat data.

        Args:
            key (str): The key to retrieve the value for.

        Returns:
            Object: 
                The value associated with the specified key, or `None` if the 
                key does not exist.
        """
        return getattr(self, key, None)

    @staticmethod
    def load(
        chat_id: str
    ) -> "ChatData":
        """
        Loads a ChatData instance from the chat history storage using the
        provided `chat_id`.

        Args:
            chat_id (str): The ID of the chat to load.

        Returns:
            ChatData: 
                An instance of ChatData with the loaded data, or `None` if
                the specified chat does not exist in the chat history storage.
        """
        path = HISTORY_DIR / f"{chat_id}.json"
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return ChatData(
                chat_id=data["chat_id"],
                title=data.get("title", "New Chat"),
                messages=data.get("messages", []),
                created_at=datetime.datetime.fromisoformat(data["created_at"]),
                last_timestamp=datetime.datetime.fromisoformat(data["last_timestamp"])
            )
        return None

    def save(
        self,
    ):
        """
        Saves the ChatData instance to the chat history storage.

        The file will be named with the `chat_id` and will be saved in the
        `HISTORY_DIR` directory. If the directory does not exist, it will be
        created.

        Raises:
            OSError: If there is an error writing to the file.
        """
        os.makedirs(HISTORY_DIR, exist_ok=True)
        path = HISTORY_DIR / f"{self.chat_id}.json"
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, ensure_ascii=False, indent=2)

    def delete(
        self,
    ):
        """
        Deletes the chat data file from the chat history storage.
        
        Raises:
            OSError: 
                If there is an error deleting the file or if the file does not 
                exist.
        """
        path = HISTORY_DIR / f"{self.chat_id}.json"
        if path.exists():
            os.remove(path)
        else:
            raise OSError(f"Chat data file {path} does not exist.")

    def rename_chat(
        self,
        new_title: str,
    ):
        """
        Renames the chat by updating its title and saving the changes to the
        respective JSON file in the chat history storage.

        Args:
            new_title (str): The new title for the chat.

        Raises:
            ValueError: If `new_title` is not a non-empty string.
            OSError: If there is an error writing to the file.
        """
        if not new_title or not isinstance(new_title, str):
            raise ValueError("new_title must be a non-empty string")

        self.title = new_title
        self.save()

    def to_dict(
        self,
    ) -> dict:
        """
        Converts the ChatData instance to a dictionary.

        Returns:
            dict: 
                A dictionary representation of the ChatData instance, 
                containing the keys `chat_id`, `title`, `messages`, 
                `last_timestamp` and `created_at`.
        """
        return {
            "chat_id": self.chat_id,
            "title": self.title,
            "messages": self.messages,
            "last_timestamp": self.last_timestamp.isoformat(),
            "created_at": self.created_at.isoformat(),
        }

    def merge_from_dict(
        self,
        new_data: dict,
    ):
        """
        Merges the chat data with the values provided in `new_data`.
        If there are missing keys, the existing values will be retained.
        Otherwise, the new values will overwrite the existing ones.

        Args:
            new_data (dict):
                A dictionary containing new values for the chat data.
                This dictionary should contain the keys `chat_id`, `title`,
                `messages` and `last_timestamp`. If any of these keys are missing,
                the existing value in the `ChatData` instance will be retained.

        Raises:
            TypeError: If `new_data` is not a dictionary or is empty.
        """
        if not new_data or not isinstance(new_data, dict):
            raise TypeError("new_data must be a non-empty dictionary")
        
        self.chat_id = new_data.get("chat_id", self.chat_id)
        self.title = new_data.get("title", self.title)
        self.messages = new_data.get("messages", self.messages)
        self.last_timestamp = new_data.get("last_timestamp", self.last_timestamp)
    
    def get_last_messages(
        self,
        n: int = 1,
    ) -> List[dict]:
        """
        Retrieves the last `n` messages from the chat.

        Args:
            n (int): The number of last messages to retrieve. Defaults to 1.

        Returns:
            list: A list containing the last `n` messages from the chat or
            all messages if there are fewer than `n` messages.
        """
        return self.messages[-n:] if len(self.messages) >= n else self.messages

    def get_last_data_message(
        self,
    ) -> Optional[dict]:
        """
        Retrieves the last message that holds data from the chat.

        Returns:
            dict: 
                The last data message from the chat, or `None` if there are no
                messages with data.
        """
        if not self.messages:
            return None
        
        for message in reversed(self.messages):
            if message.get("data", False):
                return message
        return None
    
    def add_message(
        self,
        role: str,
        content: str,
        status: str = None,
        data: Optional[dict] = None,
    ):
        """
        Adds a new message to the chat data and stores it in the storage.
        An id is inferred from the current length of the `messages` list and 
        is incremented by one for each new message. 

        Args:
            role (str):
                The role of the message sender (e.g., "user", "assistant").
            content (str):
                The content of the message.
            status (str, optional):
                The status of the message (e.g., "success", "no_match").
                Defaults to `None`.
            data (dict, optional):
                Additional data associated with the message. Defaults to
                `None`.

        Raises:
            TypeError:
                If `role` or `content` is not a non-empty string
        """
        # set up the new message id
        message = {
            "id": len(self.messages) + 1
        }

        # set the role and raise an error if it does not exist
        if not role:
            raise TypeError("role must be a non-empty string")
        elif not isinstance(role, str):
            message["role"] = str(role)
        else:
            message["role"] = role.strip()
        
        # set the content and raise an error if it does not exist
        if not content:
            raise TypeError("content must be a non-empty string")
        elif not isinstance(content, str):
            message["content"] = str(content)
        else:
            message["content"] = content
        
        # if the optional status exists, set it
        if status is not None:
            if not isinstance(status, str):
                message["status"] = str(status)
            else:
                message["status"] = status.strip()
        
        # if the optional data exists, set it
        if data is not None:
            if not isinstance(data, dict):
                raise TypeError("data must be a dictionary")
            message["data"] = data

        # append the newq message
        self.messages.append(message)
        # update the timestamp and save to storage
        self.last_timestamp = datetime.datetime.now(datetime.timezone.utc)
        self.save()

    def filter_messages(
        self,
        exclude_roles: Optional[List[str]] = None,
        exclude_status: Optional[List[str]] = None,
        exclude_ids: Optional[List[int]] = None,
        include_roles: Optional[List[str]] = None,
        include_status: Optional[List[str]] = None,
        include_ids: Optional[List[int]] = None,
        include_data: bool = False,
        sort: Optional[str] = 'asc'
    ):
        """
        Filters the messages in the chat based on the provided criteria and
        returns the filtered list.

        Args:
            exclude_roles (List[str], optional):
                A list of messanger roles to exclude from the messages. 
                Defaults to `None`, which excludes no roles.
            exclude_status (List[str], optional):
                A list of message statuses to exclude from the messages.
                Defaults to `None`, which excludes no status.
            exclude_ids (List[int], optional):
                A list of message IDs to exclude from the messages. Defaults
                to `None`, which excludes no IDs.
            include_roles (List[str], optional):
                A list of roles to include in the messages. Defaults to `None`,
                which includes all roles. This argument may be used if it is
                easier to specify the roles to include rather than exclude.
            include_status (List[str], optional):
                A list of message status to include in the messages. Defaults 
                to `None`, which includes all status. This argument may be used
                if it is easier to specify the status to include rather than 
                exclude.
            include_ids (List[int], optional):
                A list of message IDs to include in the messages. Defaults
                to `None`, which includes all IDs. This argument may be used
                if it is easier to specify the IDs to include rather than
                exclude.
            include_data (bool, optional):
                If `True`, includes messages with data. If `False`, inserts
                placeholders for the data in the messages. Defaults to `False`.
            sort (str, optional):
                The sorting order of the filtered messages. Can be either
                'asc' for ascending or 'desc' for descending order based on
                the message ID. Defaults to 'asc'. If some other value is
                provided, the messages will not be sorted.
        
        Returns:
            List[dict]: 
                A list of messages that match the filtering criteria. Each
                message is a dictionary containing the keys `id`, `status`, 
                `role`, `content`, and optionally `data` and `data_plotable`.
        """
        if exclude_roles is None:
            exclude_roles = []
        if exclude_status is None:
            exclude_status = []
        if exclude_ids is None:
            exclude_ids = []
        if include_roles is None:
            include_roles = []
        if include_status is None:
            include_status = []
        if include_ids is None:
            include_ids = []

        filtered_messages = []

        for message in self.messages:
            if (
                # weak inclusion criteria
                (not include_status or message["status"] in include_status) and
                (not include_roles or message["role"] in include_roles) and
                (not include_ids or message["id"] in include_ids) and
                # strong exclusion criteria
                (message["role"] not in exclude_roles) and
                (message["status"] not in exclude_status) and
                (message["id"] not in exclude_ids)
            ):
                if message.get("data", False):
                    message_to_add = message
                    if not include_data:
                        # if data is not included, create a filtered message
                        message_to_add = {
                            "id": message["id"],
                            "status": message["status"],
                            "role": message["role"],
                            "content": message["content"],
                            "data": {
                                "plotable": message["data"]["plotable"],
                                "plotted": message["data"]["plotted"],
                                "available_plots": message["data"]["available_plots"],
                            }
                        }
                    filtered_messages.append(message_to_add)

                else:
                    filtered_messages.append(message)

        # sort the filtered messages by id
        if sort == 'asc':
            filtered_messages.sort(key=lambda m: m["id"])
        elif sort == 'desc':
            filtered_messages.sort(key=lambda m: m["id"], reverse=True)

        return filtered_messages

    def __repr__(
        self
    ):
        return f"<ChatData chat_id={self.chat_id} title={self.title} messages={len(self.messages)} created_at={self.created_at.isoformat()}>"


def FREF_from_dict(
    data: Dict[str, Any],
) -> FunctionRegistryExpectedFormat:
    """
    Converts a dictionary, primarily originating from the `ChatData` class, to 
    a FunctionRegistryExpectedFormat object.
    
    Args:
        data (Dict[str, Any]):
            The data to use for the creation. This should feature the 
            `FunctionData` as a dictionary, the `PlotForFunction` seperated in
            the default plots JSON string und the `plotly` field and the 
            available plots as a list of `PlotFunction` function names and the 
            `plotted` boolean indicating whether the data has already been
            plotted.

            Minimal Expected keys and structure:

            ```
            data = {
                # FunctionData as dict
                "function_data": {...},
                # JSON string of the default plot
                "plotly": "{...}",
                # List of available plot function names from functions.helper.plot_helper
                "available_plots": ["PlotFunction1", "PlotFunction2", ...],
                # Boolean indicating if the data has been plotted before
                "plotted": False
            }
            ```

    Returns:
        FunctionRegistryExpectedFormat:
            The converted object.

    Raises:
        ValueError: 
            If the data does not match the expected format.
    """
    if not (
        isinstance(data, dict) and 
        "function_data" in data and 
        isinstance(data["function_data"], dict) and
        "plotly" in data and 
        isinstance(data["plotly"], str) and
        "available_plots" in data and 
        isinstance(data["available_plots"], list) and
        "plotted" in data and 
        isinstance(data["plotted"], bool)
    ):
        raise ValueError(
            "Invalid data format for FunctionRegistryExpectedFormat."
        )

    return FunctionRegistryExpectedFormat(
        data=FunctionData(data["function_data"]),
        plot=PlotForFunction(
            default_plot=Plot(pio.from_json(data["plotly"])),
            available_plots=[
                plot_function_registry[func] for func in data["available_plots"]
            ]
        ),
        plotted=data["plotted"]
    )

def list_chats(
    to_dict: Optional[bool] = False
):
    """
    Lists all chats stored in the chat history storage.
    This function retrieves all chat files from the `HISTORY_DIR` directory,
    loads them into `ChatData` instances, and returns a list chats sorted by
    their last updated timestamp in descending order.
    If `to_dict` is `True`, it returns a list of dictionaries representing the
    chat data instead of `ChatData` instances.
    
    Returns:
        List[ChatData] or List[dict]:
            A list of ChatData instances or dictionaries sorted by the
            `last_timestamp` in descending order.
    """
    os.makedirs(HISTORY_DIR, exist_ok=True)
    chats = []

    for file in HISTORY_DIR.glob("*.json"):
        print("found file: ", file, "with stem: ", file.stem)
        chat = ChatData.load(file.stem)
        if chat:
            if to_dict:
                chats.append(chat.to_dict())
            else:
                chats.append(chat)

    chats.sort(key=lambda c: c['last_timestamp'], reverse=True)
    return chats