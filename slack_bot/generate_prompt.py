import base64
import os
import io
from PIL import Image
from dotenv import load_dotenv
from openai import OpenAI


__all__ = ["generate_prompt"]

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Function to encode the image
def encode_image(image_path):
    with Image.open(image_path) as image_file:
        buffered = io.BytesIO()
        resized_img = image_file.resize((150, 150))
        resized_img.save(buffered, format="PNG")
        return base64.b64encode(buffered.getvalue()).decode("utf-8")

def generate_prompt(image_path):
    # Getting the Base64 string
    base64_image = encode_image(image_path)
    
    dense_prompt = """
    Analyze and assess this image for its aesthetic qualities. Return a prompt that will be used to generate
    a design based on the characteristics of the image. Create a bold, eye-catching T-shirt graphic 
    using the central design in this photo. 
    Regenerate the design as a clean, high-impact vector-style illustration with a transparent background. 
    Emphasize strong contrast, simplified forms, and visual clarity suitable for screen-printing. 
    Retain the core symbolic or visual elements from the original image, give it a modern, 
    graphic-art twist—perfect for a streetwear-style T-shirt.
    Return me just the design with a transparent background. Keep the prompt to less than 1000 words.
    """

    response = client.responses.create(
        model="gpt-4o",
        input=[
            {
                "role": "user",
                "content": [
                    { "type": "input_text", "text": dense_prompt },
                    {
                        "type": "input_image",
                        "image_url": f"data:image/jpeg;base64,{base64_image}",
                    },
                ],
            }
        ],
    )

    return response.output_text