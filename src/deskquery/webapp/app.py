# std lib imports
from io import BytesIO
import traceback
import uuid
import json
from pathlib import Path

# 3 Party-import 
from flask import Flask, request, jsonify, render_template, send_file
import pandas as pd

# import from project files
from deskquery.main import main as desk_query, infer_chat_renaming
from deskquery.data.dataset import create_dataset
from deskquery.functions.types import PlotFunction
from deskquery.webapp.helpers.helper import *
from deskquery.webapp.helpers.chat_data import ChatData, list_chats
from deskquery.llm.llm_api import models_to_json


app = Flask(__name__)

global current_model
current_model = None
global dataset
dataset = create_dataset()
global NEXT_STEP
NEXT_STEP = 1
global current_chat_id
current_chat_id = None

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/chat', methods=['POST'])
def chat():
    global NEXT_STEP
    global current_model
    global current_chat_id
    try:
        data = request.get_json()
        user_input = data.get('message', '')
        chat_id = data.get('chat_id', None) or str(uuid.uuid4())

        # check if a new chat was selected
        print("current chat id:", current_chat_id)
        print("got chat id:", chat_id)
        if chat_id != current_chat_id:
            current_chat_id = chat_id
            NEXT_STEP = 1

        print("backend: chat: current_model:", current_model)

        chat_data = ChatData.load(chat_id)

        message = {
            "role": "user",
            "content": user_input,
        }
        # if the chat history is empty, append the user message
        if not chat_data.messages:
            message["status"] = "user_msg"
        # if the last message is refinement question to the user, append the user response
        elif chat_data.messages[-1].get("content", "") != user_input:
            if chat_data.messages[-1].get("status", "") == "ask_user":
                message["status"] = "user_response"
            else:
                message["status"] = "user_msg"
        
        # if the message object has been altered, add it to the chat history
        if message.get("status", None): 
            chat_data.add_message(**message)

        response = desk_query(
            user_input,
            chat_data=chat_data,
            data=dataset, 
            model=current_model, 
            START_STEP=NEXT_STEP if NEXT_STEP else 1
        )
        print("main.py response:\n", response)

        if isinstance(response, dict) and response.get("message", False):
            message_data = {
                "status": response["status"], 
                "role": "assistant", 
                "content": response["message"]
            }
            if response.get("data", False):                
                if all(not isinstance(v, (list, dict)) for v in response["data"].data.values()):
                    df = pd.DataFrame([response["data"].data], dtype=object)
                else:
                    df = pd.DataFrame(response["data"].data, dtype=object)
                
                df = df = df.where(pd.notnull(df), None)

                message_data["data"] = {
                    "function_data": response["data"].data,
                    "plotable": response["data"].plotable,
                    "plotted": response["data"].plotted,
                    "plotly": response["data"].plot.default_plot.to_dict(),
                    "df": df.to_dict('index'),
                    "available_plots": [plot.__name__ for plot in response["data"].plot.available_plots],
                    "type": "mixed"
                }

            if response.get("NEXT_STEP", False):
                NEXT_STEP = response["NEXT_STEP"]
            else:
                NEXT_STEP = 1

            print("message_data:", message_data, sep="\n")
            chat_data.add_message(**message_data)
                
            return jsonify({
                "chat_id": chat_id,
                "chat_title": chat_data.title,
                "messages": chat_data.messages
            })
        else:
            print("main.py response is not an expected standard dict:", response)

    except Exception as e:
        print("Error in /chat endpoint:", str(e))
        traceback.print_exc()
        return jsonify({
            "status": "error",
            "chat_id": chat_id,
            "model": current_model,
            "message": "An error occurred. Please try again."
        }), 500


@app.route('/get-models', methods=['GET'])
def get_models():
    try:
        # read the available models from the models.json
        models_path = Path(__file__).resolve().parent.parent / 'llm' / 'models.json'
        models_to_json(str(models_path))
        
        with open(models_path, 'r') as file:
            models = json.load(file)
        return jsonify({"status": "success", "models": models})
    except FileNotFoundError:
        return jsonify({"status": "error", "message": "Models file not found"}), 404
    except Exception as e:
        print("Error in /get-models endpoint:", str(e))
        return jsonify({"status": "error", "message": "An error occurred"}), 500

@app.route('/set-model', methods=['POST'])
def set_model():
    data = request.get_json()
    provider = data.get('provider')
    model = data.get('model')
    if model:
        global current_model
        current_model = {'provider': provider, 'model': model}
        print(f"backend: current_model set to '{current_model}'")
        return jsonify({"status": "success", "model": model})
    else:
        print("backend: Model not provided")
        return jsonify({"status": "error", "message": "Model not provided"}), 400


# returns all chats that are in chat storage
@app.route('/chats', methods=['GET'])
def get_chats():
    return jsonify(list_chats(to_dict=True))


# returns a chat as json
@app.route('/chats/<chat_id>', methods=['GET'])
def get_single_chat(chat_id):
    chat = ChatData.load(chat_id)
    if chat:
        return jsonify(chat.to_dict())
    return jsonify({'status': 'Chat not found'}), 404


# renames a chat
@app.route('/chats/<chat_id>/rename', methods=['POST'])
def rename_chat_route(chat_id):
    data = request.get_json()
    new_title = data.get("title", "").strip()
    if not new_title:
        return jsonify({"error": "Title cannot be empty"}), 400

    chat = ChatData.load(chat_id)
    if not chat:
        return jsonify({"status": "Chat not found"}), 404

    # rename the chat
    try:
        chat.rename_chat(new_title)
        return jsonify({"status": "renamed"}), 200
    except Exception as e:
        return jsonify({"status": "error"}), 500


# deletes a chat by ID
@app.route('/chats/delete/<chat_id>', methods=['DELETE'])
def delete_chat_route(chat_id):
    chat = ChatData.load(chat_id)
    if not chat:
        return jsonify({"status": "Chat not found"}), 404

    # delete the chat
    try:
        chat.delete()
        return jsonify({"status": "deleted"}), 200
    except Exception as e:
        return jsonify({"status": "error"}), 500


# creates a new chat
@app.route('/chats/new', methods=['POST'])
def create_new_chat():
    new_chat = ChatData()
    new_chat.save()
    print("New chat created in backend with ID:", new_chat.chat_id)
    return jsonify({"chat_id": new_chat.chat_id, "title": new_chat.title})


# infers an automatic chat name from the first user chat message
@app.route('/chats/<chat_id>/infer-name', methods=['POST'])
def infer_chat_name(chat_id):
    chat = ChatData.load(chat_id)
    if not chat:
        return jsonify({"status": "Chat not found"}), 404

    # infer a name for the chat based on the messages
    try:
        infer_chat_renaming(chat)
        return jsonify({"status": "success", "title": chat.title}), 200
    except Exception as e:
        print("Error inferring chat name:", str(e))
        return jsonify({"status": "error", "message": "Failed to infer chat name"}), 500


def test_query(
    user_input=None,
    chat_data=None,
    data=None, 
    model=None, 
    START_STEP=1
):
    return {
        "id": 15,
        "role": "assistant",
        "content": "Here is your test plot!",
        "status": "success",
        "data": {
            "type": "mixed",
            "plotted": True,
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


if __name__ == '__main__':
    app.run(debug=True)