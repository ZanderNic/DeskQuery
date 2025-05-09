# std lib imports
from io import BytesIO
import uuid

# 3 Party-import 
from flask import Flask, request, jsonify, render_template, send_file
import matplotlib.pyplot as plt


# import sys
# import os

# # Add the parent directory to sys.path
# parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
# sys.path.append(parent_dir)


# import from projekt files
from ..main import main
from helpers.helper import *


# webapp\llm_chat\choose_function.py
app = Flask(__name__)
generated_images = {}

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/chat', methods=['POST'])
def chat():
    try:
        data = request.get_json()
        user_input = data.get('message', '').lower()

        response = main(user_input)
        print(response)
        
        if isinstance(response, dict) and response.get("type") == "html_table":
            return jsonify({
                "type": "mixed" if "text" in response else "html",
                "text": response.get("text"),
                "html": response.get("html")
            })
           
        elif isinstance(response, dict) and response.get("type") == "plot":
            return jsonify({
                "type": "mixed" if "text" in response else "plot",
                "text": response.get("text", ""),
                "plot": {
                    "data": response["data"],
                    "layout": response["layout"]
                }
            })

        # image + text
        elif "image and text" in user_input:
            img_id = str(uuid.uuid4())
            generated_images[img_id] = create_image()
            return jsonify({
                "type": "mixed",
                "text": "Here is an image with some text.",
                "image": f"/image/{img_id}"
            })

        # plot (as JSON) + text
        elif "graph and text" in user_input:
            return jsonify({
                "type": "mixed",
                "text": "This is a graph with some explanation.",
                "plot": {
                    "data": [{"x": [1, 2, 3], "y": [3, 1, 6], "type": "scatter"}],
                    "layout": {"title": "Example Graph", "width": 600, "height": 400}
                }
            })

        # image
        elif "image" in user_input:
            img_id = str(uuid.uuid4())
            generated_images[img_id] = create_image()
            return jsonify({
                "type": "image",
                "content": f"/image/{img_id}"
            })

        # Plot (Plotly JSON)
        elif "graph" in user_input:
            return jsonify({
                "type": "plot",
                "data": [{"x": [1, 2, 3], "y": [3, 1, 6], "type": "scatter"}],
                "layout": {"title": "Example Graph", "width": 600, "height": 400}
            })

        # Fallback: only text
        else:
            return jsonify({
                "type": "text",
                "content": f"Auf die Frage oder Eingabe: {user_input}, kann ich dir leider momentan noch keine Antwort geben. Versuche etwas anderes!"
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


def create_image():
    fig, ax = plt.subplots(figsize=(6, 4))  # Match Plotly dimensions
    ax.plot([0, 1, 2], [0, 1, 4])
    ax.set_title("Generated Image")
    img_io = BytesIO()
    plt.savefig(img_io, format='png', bbox_inches='tight')
    plt.close(fig)
    return img_io


if __name__ == '__main__':
    app.run(debug=True)