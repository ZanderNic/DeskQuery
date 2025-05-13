# std lib imports
from io import BytesIO
import uuid
import json
from pathlib import Path

# 3 Party-import 
from flask import Flask, request, jsonify, render_template, send_file
import matplotlib.pyplot as plt


# import from projekt files
from deskquery.main import main as desk_query
from deskquery.webapp.helpers.helper import *
from deskquery.webapp.helpers.chat_history import save_chat, load_chat, list_chats, delete_chat, rename_chat

from deskquery.llm.llm_api import models_to_json


# webapp\llm_chat\choose_function.py
app = Flask(__name__)

generated_images = {}
global current_model
current_model = None



@app.route('/')
def index():
    return render_template('index.html')


@app.route('/chat', methods=['POST'])
def chat():
    try:
        data = request.get_json()
        user_input = data.get('message', '').lower()  # FIXME: For what is the lowercase? Might the case be relevant for the LLM?
        chat_id = data.get('chat_id', None) or str(uuid.uuid4())

        global current_model
        print("backend: chat: current_model:", current_model)

        chat_data = load_chat(chat_id)
        messages = chat_data["messages"] if chat_data else []

        if user_input:
            messages.append({"role": "user", "content": user_input})

        response = desk_query(user_input, model=current_model)
        print(response)

        if isinstance(response, str):
            messages.append({"role": "assistant", "content": response})
            save_chat(chat_id, messages)
            return jsonify({
                "chat_id": chat_id,
                "messages": messages
            })

        elif isinstance(response, dict) and response.get("message"):
            messages.append({"role": "assistant", "content": response["message"]})
            save_chat(chat_id, messages)
            return jsonify({
                "chat_id": chat_id,
                "messages": messages
            })

        if isinstance(response, dict) and response.get("type") == "html_table":
            messages.append({"role": "assistant", "content": response.get("text", "[Table]")})
            save_chat(chat_id, messages)
            return jsonify({
                "chat_id": chat_id,
                "type": "mixed",
                **response
            })

        elif isinstance(response, dict) and response.get("type") == "plot":
            messages.append({"role": "assistant", "content": response.get("text", "[Plot]")})
            save_chat(chat_id, messages)
            return jsonify({
                "chat_id": chat_id,
                "type": "mixed",
                **response
            })

        elif isinstance(response, dict) and response.get("type") == "text":
            messages.append({"role": "assistant", "content": response["content"]})
            save_chat(chat_id, messages)
            return jsonify({
                "chat_id": chat_id,
                "type": "text",
                "content": response["content"]
            })

        elif "image and text" in user_input:
            img_id = str(uuid.uuid4())
            generated_images[img_id] = create_image()
            messages.append({"role": "assistant", "content": "Here is an image with some text."})
            save_chat(chat_id, messages)
            return jsonify({
                "chat_id": chat_id,
                "type": "mixed",
                "text": "Here is an image with some text.",
                "image": f"/image/{img_id}"
            })

        elif "graph and text" in user_input:
            messages.append({"role": "assistant", "content": "This is a graph with some explanation."})
            save_chat(chat_id, messages)
            return jsonify({
                "chat_id": chat_id,
                "type": "mixed",
                "text": "This is a graph with some explanation.",
                "plot": {
                    "data": [{"x": [1, 2, 3], "y": [3, 1, 6], "type": "scatter"}],
                    "layout": {"title": "Example Graph", "width": 600, "height": 400}
                }
            })

        elif "image" in user_input:
            img_id = str(uuid.uuid4())
            generated_images[img_id] = create_image()
            return jsonify({
                "chat_id": chat_id,
                "type": "image",
                "content": f"/image/{img_id}"
            })

        elif "graph" in user_input:
            messages.append({"role": "assistant", "content": "Here is a graph."})
            save_chat(chat_id, messages)
            return jsonify({
                "chat_id": chat_id,
                "type": "plot",
                "data": [{"x": [1, 2, 3], "y": [3, 1, 6], "type": "scatter"}],
                "layout": {"title": "Example Graph", "width": 600, "height": 400}
            })

        else:
            fallback = f"Auf die Frage oder Eingabe: {user_input}, kann ich dir leider momentan noch keine Antwort geben."
            messages.append({"role": "assistant", "content": fallback})
            save_chat(chat_id, messages)
            return jsonify({
                "chat_id": chat_id,
                "type": "text",
                "content": fallback
            })

    except Exception as e:
        print("Fehler im /chat-Endpoint:", str(e))
        return jsonify({
            "type": "error",
            "message": "Ein Fehler ist aufgetreten. Bitte versuche es erneut."
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
    return jsonify(list_chats())

# returns a singel chat
@app.route('/chats/<chat_id>', methods=['GET'])
def get_single_chat(chat_id):
    chat = load_chat(chat_id)
    if chat:
        return jsonify(chat)
    return jsonify({'error': 'Not found'}), 404

# renames a chat 
@app.route('/chats/<chat_id>/rename', methods=['POST'])
def rename_chat_route(chat_id):
    data = request.get_json()
    new_title = data.get("title", "").strip()
    if not new_title:
        return jsonify({"error": "Title cannot be empty"}), 400
    success = rename_chat(chat_id, new_title)
    return jsonify({"status": "renamed" if success else "not found"}), 200 if success else 404

# deletes a chat by his id
@app.route('/chats/delete/<chat_id>', methods=['DELETE'])
def delete_chat_route(chat_id):
    success = delete_chat(chat_id)
    return jsonify({"status": "deleted" if success else "not found"}), 200 if success else 404

# creates a new chat
@app.route('/chats/new', methods=['POST'])
def create_new_chat():
    new_id = str(uuid.uuid4())
    title = "Neuer Chat"
    save_chat(new_id, [], title=title)
    return jsonify({"chat_id": new_id, "title": title})



if __name__ == '__main__':
    app.run(debug=True)