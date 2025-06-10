# std lib imports
from io import BytesIO
import traceback
import uuid
import json
from pathlib import Path

# 3 Party-import 
from flask import Flask, request, jsonify, render_template, send_file


# import from project files
from deskquery.main import main as desk_query
from deskquery.data.dataset import create_dataset
from deskquery.webapp.helpers.helper import *
from deskquery.webapp.helpers.chat_data import ChatData, list_chats
from deskquery.llm.llm_api import models_to_json


# webapp\llm_chat\choose_function.py
app = Flask(__name__)

generated_images = {}

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
        chat_id = data.get('chat_id', None) or str(uuid.uuid4())

        global current_model
        print("backend: chat: current_model:", current_model)

        chat_data = ChatData.load(chat_id)

        # Check if the last message was a question by the system
        if chat_data.messages:
            global NEXT_STEP
            NEXT_STEP = 300 if chat_data.messages[-1].get("status", "") == "ask_user" else 1

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
       
        if isinstance(response, dict) and response.get("message"):
            message_data = {
                "status": response["status"], 
                "role": "assistant", 
                "content": response["message"]
            }
            if response.get("data", False):
                message_data["data"] = {
                    "function_data": response["data"].data,
                    "plotable": response["data"].plotable,
                    "plotly": response["data"].plot.default_plot.to_json(),
                    "available_plots": [plot.__name__ for plot in response["data"].plot.available_plots[:-1]],
                    "type": "mixed"
                }

            print("message_data:", message_data, sep="\n")
            chat_data.add_message(**message_data)
                
            return jsonify({
                "chat_id": chat_id,
                "messages": chat_data.messages
            })
        else:
            print("main.py response is not an expected standard dict:", response)
        
        #########

        # if isinstance(response, dict) and response.get("type") == "html_table":
        #     messages.append({"role": "assistant", "content": response.get("text", "[Table]")})
        #     save_chat(chat_id, messages)
        #     return jsonify({
        #         "chat_id": chat_id,
        #         "type": "mixed",
        #         **response
        #     })

        # elif isinstance(response, dict) and response.get("type") == "plot":
        #     messages.append({"role": "assistant", "content": response.get("text", "[Plot]")})
        #     save_chat(chat_id, messages)
        #     return jsonify({
        #         "chat_id": chat_id,
        #         "type": "mixed",
        #         **response
        #     })

        # elif isinstance(response, dict) and response.get("type") == "text":
        #     messages.append({"role": "assistant", "content": response["content"]})
        #     save_chat(chat_id, messages)
        #     return jsonify({
        #         "chat_id": chat_id,
        #         "type": "text",
        #         "content": response["content"]
        #     })

        # elif "image and text" in user_input:
        #     img_id = str(uuid.uuid4())
        #     generated_images[img_id] = create_image()
        #     messages.append({"role": "assistant", "content": "Here is an image with some text."})
        #     save_chat(chat_id, messages)
        #     return jsonify({
        #         "chat_id": chat_id,
        #         "type": "mixed",
        #         "text": "Here is an image with some text.",
        #         "image": f"/image/{img_id}"
        #     })

        # elif "graph and text" in user_input:
        #     messages.append({"role": "assistant", "content": "This is a graph with some explanation."})
        #     save_chat(chat_id, messages)
        #     return jsonify({
        #         "chat_id": chat_id,
        #         "type": "mixed",
        #         "text": "This is a graph with some explanation.",
        #         "plot": {
        #             "data": [{"x": [1, 2, 3], "y": [3, 1, 6], "type": "scatter"}],
        #             "layout": {"title": "Example Graph", "width": 600, "height": 400}
        #         }
        #     })

        # elif "image" in user_input:
        #     img_id = str(uuid.uuid4())
        #     generated_images[img_id] = create_image()
        #     return jsonify({
        #         "chat_id": chat_id,
        #         "type": "image",
        #         "content": f"/image/{img_id}"
        #     })

        # elif "graph" in user_input:
        #     messages.append({"role": "assistant", "content": "Here is a graph."})
        #     save_chat(chat_id, messages)
        #     return jsonify({
        #         "chat_id": chat_id,
        #         "type": "plot",
        #         "data": [{"x": [1, 2, 3], "y": [3, 1, 6], "type": "scatter"}],
        #         "layout": {"title": "Example Graph", "width": 600, "height": 400}
        #     })

        # else:
        #     fallback = f"Auf die Frage oder Eingabe: {user_input}, kann ich dir leider momentan noch keine Antwort geben."
        #     messages.append({"role": "assistant", "content": fallback})
        #     save_chat(chat_id, messages)
        #     return jsonify({
        #         "chat_id": chat_id,
        #         "type": "text",
        #         "content": fallback
        #     })

    except Exception as e:
        print("Error in /chat endpoint:", str(e))
        traceback.print_exc()
        return jsonify({
            "status": "error",
            "chat_id": chat_id,
            "message": "An error occurred. Please try again later."
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
    # print("backend: set_model: ", data)
    provider = data.get('provider')
    model = data.get('model')
    # print(f"backend: set_model: provider: {provider}, model: {model}")
    if model:
        # print(f"backend: model set to '{model}'")
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

# returns a single chat
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
        return jsonify({"status": "Title cannot be empty"}), 400

    chat = ChatData.load(chat_id)
    if not chat:
        return jsonify({"status": "Chat not found"}), 404

    # rename the chat
    try:
        chat.rename_chat(new_title)
        return jsonify({"status": "renamed"}), 200
    except Exception as e:
        return jsonify({"status": "error"}), 500

# deletes a chat by his id
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
    return jsonify({"chat_id": new_chat.chat_id, "title": new_chat.title})


if __name__ == '__main__':
    app.run(debug=True)