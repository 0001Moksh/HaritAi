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
If any of the following items is related to human or animal biological waste (e.g., poop, urine, blood, hair, nails, body parts, vomit, dead animal), please respond with "Not garbage".

Else:
1. Categorize the item into one of the following types: Plastic, Metal, Organic, Paper, Glass, E-waste, Textile, or Unknown.
2. Then say: "reuse it"
3. Follow with two lines:
   "Category: <category>"
   "Description: <short physical description>, Unit: <unit>, Shape: <shape>, Color: <color>"

Additionally, ensure that the generated description or prompt can be reused to regenerate the same or visually similar image using image generation AI tools. Maintain consistent and descriptive phrasing for reliable image reproduction.
"""
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
    prompt = f"""
Using these waste materials: {descriptions}, suggest a simple eco-friendly product that can be made easily.

Include:
1. Product Name  
2. Use/Purpose  
3. How to Make (in 3-4 points with bullet points)  
4. Extra Items Needed (like glue, scissors, etc.)  
5. Environmental Benefit (1 line)
6. Detailed Description of image to be generated
"""    
    response = client.models.generate_content(
        model="gemini-2.0-flash",
        contents=[prompt]
    )
    
    input_string = response.text
    
    output_string = re.sub(r"\*\*(.*?)\*\*", r"<b>\1</b>", input_string)

    # Step 2: Add newline before each numbered heading (except if it's at the beginning)
    output_string = re.sub(r"(?<!^)(\d+\.\s[^:\n]+:)", r"\n\1", output_string)

    # Step 3: Boldify numbered headings
    output_string = re.sub(r"(\d+\.\s[^:\n]+:)", r"<b>\1</b>", output_string)

    # Step 4: Convert bullet points (* or •) to <br>• 
    output_string = re.sub(r"\n\s*[•*]\s*", r"<br>• ", output_string)

    # Step 5: Replace final \n with <br> for HTML display
    output_string = output_string.replace('\n', '<br>')

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



