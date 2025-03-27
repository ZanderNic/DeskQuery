from flask import Flask, request, jsonify, render_template, send_file
from io import BytesIO
import matplotlib.pyplot as plt
import uuid

app = Flask(__name__)
generated_images = {}

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/chat', methods=['POST'])
def chat():
    data = request.get_json()
    msg = data.get('message', '').lower()

    if "image and text" in msg:
        img_id = str(uuid.uuid4())
        generated_images[img_id] = create_image()
        return jsonify({
            "type": "mixed",
            "text": "Here is an image with some text.",
            "image": f"/image/{img_id}"
        })

    elif "graph and text" in msg:
        return jsonify({
            "type": "mixed",
            "text": "This is a graph with some explanation.",
            "plot": {
                "data": [{"x": [1, 2, 3], "y": [3, 1, 6], "type": "scatter"}],
                "layout": {"title": "Example Graph", "width": 600, "height": 400}
            }
        })

    elif "image" in msg:
        img_id = str(uuid.uuid4())
        generated_images[img_id] = create_image()
        return jsonify({
            "type": "image",
            "content": f"/image/{img_id}"
        })

    elif "graph" in msg:
        return jsonify({
            "type": "plot",
            "data": [{"x": [1, 2, 3], "y": [3, 1, 6], "type": "scatter"}],
            "layout": {"title": "Example Graph", "width": 600, "height": 400}
        })

    return jsonify({
        "type": "text",
        "content": "You said: " + msg
    })


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
