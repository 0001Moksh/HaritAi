from PIL import Image
from io import BytesIO
import re
from flask import Flask, render_template, request, jsonify
import os
import PIL.Image
from google import genai
from google.genai import types
from dotenv import dotenv_values

app = Flask(__name__)

config = dotenv_values(".env")
key=config.get('gemini_key')
key = "AIzaSyDBiMuUtYvPI2WuDqF1NqdOgd8EtRr72So"
# Upload folder
UPLOAD_FOLDER = 'uploads/'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Store garbage descriptions
garbage_descriptions = []
# Store the suggested product
suggested_product = ""

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/upload_image', methods=['POST'])
def upload_image():
    from google import genai
    from google.genai import types
    client = genai.Client(api_key=key)
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'})
    
    file = request.files['file']
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
    file.save(file_path)
    image = PIL.Image.open(file_path)
    content = """
if any of the following items is human being or animal waste, please say "Not garbage".
else garbage or you can say "reuse it " + "description of that item in 2 lines only """

    response = client.models.generate_content(
        model="gemini-2.0-flash",
        contents=[content, image])

    description = response.text

    # If it's garbage, store the description
    if "Not garbage" not in description:
        garbage_descriptions.append(description)

    return jsonify({'description': description})

@app.route('/predict_product', methods=['GET'])
def predict_product():
    global suggested_product
    if not garbage_descriptions:
        return jsonify({'message': "No garbage detected in uploaded images."})

    # Call your function to generate a product from garbage descriptions
    suggested_product = generate_product_from_waste(garbage_descriptions)

    return jsonify({'suggested_product': suggested_product})

def generate_product_from_waste(descriptions):
    client = genai.Client(api_key=key)
    prompt = f"Using the following waste materials: {descriptions}, suggest an innovative, eco-friendly product that can be practically manufactured. Ensure the product is sustainable, biodegradable, or recyclable, and explain how it benefits the environment."
    response = client.models.generate_content(
        model="gemini-2.0-flash",
        contents=[prompt]
    )
    
    input_string = response.text

    # Remove Markdown symbols using regex
    output_string = re.sub(r"\*\*|\*", "", input_string)
    return output_string

@app.route('/generate_product_image', methods=['GET'])
def generate_product_image():
    global suggested_product
    if not suggested_product:
        return jsonify({"error": "No product suggested yet. Please run /predict_product first."}), 400
    
    client = genai.Client(api_key=key)
    
    contents = [f"Generate an image of: {suggested_product}"]
    
    response = client.models.generate_content(
        model="gemini-2.0-flash-exp-image-generation",
        contents=contents,
        config=types.GenerateContentConfig(
            response_modalities=['Text', 'Image']
        )
    )
    
    for part in response.candidates[0].content.parts:
        if part.text is not None:
            pass
        elif part.inline_data is not None:
            image = Image.open(BytesIO(part.inline_data.data))
            image.save('static/gemini-native-image.png')
            return jsonify({"image_url": "/static/gemini-native-image.png"})
        else:
            return jsonify({"error": "No image data found"}), 500
    return jsonify({"error": "No image data found"}), 500

if __name__ == '__main__':
    app.run(debug=True)



