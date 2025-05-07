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

def generate_prompt(mode="static", injection=""):
    # Getting the Base64 string
    # base64_image = encode_image(image_path)
    
    dense_prompt = """
    Recreate the central design of this image.
    The design must be by itself without any of the background context. 
    The design should be immediately transferrable as printable for a T-Shirt.
    I want just the central design with a transparent background.
    Ensure the design is centered on the canvas with at least 15% transparent margin so nothing is cropped.
    Transparent background is very important.
    """
    if mode == "static": return dense_prompt

    if mode == "inject":
        dense_prompt = """
        Add details to this prompt so that it can be used as a prompt for a graphic design. 
        The design should be immediately transferrable as printable for a T-Shirt.
        I want just the central design described with a transparent background.
        Ensure the design is centered on the canvas with at least 15% transparent margin so nothing is cropped.
        Transparent background is very important.
        """
        try:
            response = client.responses.create(
                model="gpt-4o",
                input=[
                    {
                        "role": "user",
                        "content": [
                            { "type": "input_text", "text": dense_prompt + " " + injection },
                        ],
                    }
                ],
            )
            
            return response.output[0].content[0].text

        except Exception as e:
            print(e)
