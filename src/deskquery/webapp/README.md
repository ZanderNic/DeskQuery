DeskQuery Chat Web App - Overview
=================================

This is a Flask-based web application that allows users to interact with a language model (LLM) through a chat interface. The application supports persistent chat history, model selection, and multimodal responses including text, tables, and Plotly plots.


IMPORTANT NOTICE
----------------

This application is a **demo web interface** intended for experimentation and testing purposes only.

While it demonstrates features such as:
- Interactive LLM-based chat
- Support for tables and Plotly plots
- Persistent chat history
- Model selection

... it is **not designed for production use**.

Key limitations:
- Chat history is stored as plain `.json` files on the local filesystem.
- The backend is synchronous and minimal.

In a real-world frontend/backend system:
- Conversations would be stored in a database with user authentication.
- The frontend would be separated and possibly use a JS framework (React, Vue, etc.).

Use this project as a base to explore ideas or prototype features — not as a finished solution.

----------------

### 1. Running the Application

Start the app by running:

    python deskquery/webapp/app.py

It will start a development server at http://127.0.0.1:5000/

----------------


### 2. Sending a Chat Message (POST /chat)

Send a POST request to /chat with the following JSON body:

    {
        "chat_id": "optional-chat-id",
        "message": "Your question here"
    }

If no chat_id is provided, a new chat will be created automatically.

----------------


### 3. Expected LLM Response Format


The function that handles user input (e.g. desk_query or test_query) must return a dictionary in this format:

    {
        "id": 1,
        "role": "assistant",
        "content": "Here is your result.",
        "status": "done",
        "data": {
            "type": "mixed",            # must be one of: table, plot, mixed if none will just display the text that is present in contetn
            "plotly": {
                "data": [...],
                "layout": {...}
            },
            "df": {
                "columns": [...],
                "rows": [...]
            }
        }
    }

The `type` field inside `data` is mandatory if a plot or a data should be displayed and determines how the frontend will render the message:
- "table": data table (Pandas-like structure)
- "plot": Plotly chart
- "mixed": combination of text and plot/table

----------------

### 4. Example test_query Function

Use this for local testing without a real LLM:

    def test_query(user_input, data=None, model=None, START_STEP=1):
        return {
            "id": 1,
            "role": "assistant",
            "content": "Here is your test plot!",
            "status": "done",
            "data": {
                "type": "mixed",
                "plotly": {
                    "data": [
                        {
                            "x": ["2024-01-01", "2024-01-02", "2024-01-03"],
                            "y": [0.85, 0.91, 0.76],
                            "type": "scatter",
                            "mode": "lines+markers",
                            "name": "Test Data"
                        }
                    ],
                    "layout": {
                        "title": "Test Plot",
                        "xaxis": { "title": "Date" },
                        "yaxis": { "title": "Utilization" }
                    }
                }
            }
        }

Replace `desk_query` with `test_query` in app.py for development.

---

### 5. Chat History Storage

Chat messages are persisted in JSON files under:

    deskquery/chat_history_storage/

Each file is named after its `chat_id` and contains the entire conversation and metadata.

Example file: test-plotly-chat.json

File structure:

    {
        "chat_id": "test-plotly-chat",
        "title": "Testchat mit Plotly",
        "created_at": "2025-06-01T18:00:00Z",
        "last_updated": "2025-06-01T15:48:51.207053",
        "messages": [
            {
                "id": 1,
                "role": "user",
                "content": "Wie sieht die Auslastung diese Woche aus?",
                "status": null
            },
            {
                "id": 2,
                "role": "assistant",
                "content": "Hier ist die Auslastung der Woche als Plot.",
                "status": "done",
                "data": {
                    "type": "mixed",
                    "plotly": {
                        "data": [...],
                        "layout": {...}
                    }
                }
            },
            {
                "id": 3,
                "role": "user",
                "content": "Nur Plot bitte.",
                "status": null
            },
            {
                "id": 4,
                "role": "assistant",
                "content": "",
                "status": "done",
                "data": {
                    "type": "plot",
                    "plotly": {
                        "data": [...],
                        "layout": {...}
                    }
                }
            },
            {
                "id": 5,
                "role": "user",
                "content": "Und zeig mir bitte nur die Tabelle.",
                "status": null
            },
            {
                "id": 6,
                "role": "assistant",
                "content": "Hier ist die aktuelle Übersichtstabelle:",
                "status": "done",
                "data": {
                    "type": "table",
                    "df": {
                        "columns": ["Raum", "Belegt", "Kapazität"],
                        "rows": [
                            ["Alpha", 7, 10],
                            ["Beta", 6, 10],
                            ["Gamma", 9, 10]
                        ]
                    }
                }
            },
            ...
        ]
    }

Notes:
- Every message must have a unique `id` (incremental).
- The `role` is either "user" or "assistant".
- The `data` field is optional and only present for assistant responses.
- If `data` is present, the field `type` must be set ("plot", "table", or "mixed").

The frontend uses this data to reconstruct the conversation history and render visual elements accordingly.

---

### 6. API Endpoints

GET     /                       - Load chat UI
POST    /chat                   - Send message, receive response
GET     /chats                  - Get list of all chats
GET     /chats/<chat_id>        - Get one chat and its messages
POST    /chats/new              - Create new chat
POST    /chats/<id>/rename      - Rename a chat
DELETE  /chats/delete/<id>      - Delete a chat
GET     /get-models             - Get list of available LLM models
POST    /set-model              - Set current model (provider + model)

---

### 7. Notes

- Plots are rendered using Plotly.js and must be passed as a standard Plotly object.
- Tables must be passed as a dict with "columns" and "rows" keys.
- The frontend supports displaying mixed content in one response.
- Chat titles can be renamed, and chats are grouped in the UI by date.

This setup allows for quick experimentation with LLMs in a structured and interactive environment.
