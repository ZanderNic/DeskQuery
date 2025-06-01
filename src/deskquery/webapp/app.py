# std lib imports
from io import BytesIO
import traceback
import uuid
import json
from pathlib import Path

# 3 Party-import 
from flask import Flask, request, jsonify, render_template, send_file
import matplotlib.pyplot as plt


# import from projekt files
from deskquery.main import main as desk_query
from deskquery.data.dataset import create_dataset
from deskquery.webapp.helpers.helper import *
from deskquery.webapp.helpers.chat_history import Chat, list_chats
from deskquery.llm.llm_api import models_to_json


# webapp\llm_chat\choose_function.py
app = Flask(__name__)

generated_images = {}   # TODO evaluate if we still need this: this is was used for a first start 

global current_model
current_model = None
global dataset
dataset = create_dataset()
global NEXT_STEP
NEXT_STEP = 1

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/chat', methods=['POST'])
def chat():
    try:
        data = request.get_json()
        user_input = data.get('message', '')
        chat_id = data.get('chat_id') or str(uuid.uuid4())

        global current_model
        print("backend: chat: current_model:", current_model)

        chat = Chat.load(chat_id) or Chat(chat_id)

        # Determine NEXT_STEP if needed
        global NEXT_STEP
        if chat.messages:
            NEXT_STEP = 3 if chat.messages[-1].get("status") == "ask_user" else 1

        if user_input:
            chat.append_message("user", user_input)

        # LLM response
        # response = desk_query(
        #     user_input,
        #     data=dataset,
        #     model=current_model,
        #     START_STEP=NEXT_STEP
        # )
        # print("LLM response:", response)

        ### TEST
        response = test_query(
            user_input,
            data=dataset,
            model=current_model,
            START_STEP=NEXT_STEP
        )
            
        return format_chat_response(chat, response)

    except Exception as e:
        print("Error in /chat:", str(e))
        traceback.print_exc()
        return jsonify({
            "type": "error",
            "message": "An error occurred. Please try again."
        }), 500


@app.route('/image/<img_id>')
def serve_image(img_id):
    if img_id not in generated_images:
        return "Image not found", 404
    img_io = generated_images[img_id]
    img_io.seek(0)
    return send_file(img_io, mimetype='image/png')


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
    return jsonify(list_chats())

@app.route('/chats/<chat_id>', methods=['GET'])
def get_single_chat(chat_id):
    chat = Chat.load(chat_id)
    if chat:
        return jsonify({
            "chat_id": chat.chat_id,
            "title": chat.title,
            "created_at": chat.created_at,
            "last_updated": chat.last_updated,
            "messages": chat.messages
        })
    return jsonify({'error': 'Not found'}), 404


# Renames a chat
@app.route('/chats/<chat_id>/rename', methods=['POST'])
def rename_chat_route(chat_id):
    data = request.get_json()
    new_title = data.get("title", "").strip()
    if not new_title:
        return jsonify({"error": "Title cannot be empty"}), 400

    chat = Chat.load(chat_id)
    if not chat:
        return jsonify({"status": "not found"}), 404

    chat.rename(new_title)
    return jsonify({"status": "renamed"}), 200


# Deletes a chat by ID
@app.route('/chats/delete/<chat_id>', methods=['DELETE'])
def delete_chat_route(chat_id):
    chat = Chat.load(chat_id)
    if chat and chat.delete():
        return jsonify({"status": "deleted"}), 200
    return jsonify({"status": "not found"}), 404


# Creates a new empty chat
@app.route('/chats/new', methods=['POST'])
def create_new_chat():
    new_id = str(uuid.uuid4())
    chat = Chat(chat_id=new_id, title="Neuer Chat")
    chat.save()
    return jsonify({"chat_id": new_id, "title": chat.title})



def test_query(user_input, data=None, model=None, START_STEP=1):
    return {
        "id": 1,
        "role": "assistant",
        "content": "Hier ist dein Testplot!",
        "status": "done",
        "data": {
            "plotly": {
                "data": [
                    {
                        "x": ["2024-01-01", "2024-01-02", "2024-01-03"],
                        "y": [0.85, 0.91, 0.76],
                        "type": "scatter",
                        "mode": "lines+markers",
                        "name": "Testdaten"
                    }
                ],
                "layout": {
                    "title": "Testplot",
                    "xaxis": {"title": "Datum"},
                    "yaxis": {"title": "Auslastung"}
                }
            },
            "type": "mixed"
        }
    }



if __name__ == '__main__':
    app.run(debug=True)