import base64
import os
import io
from PIL import Image
# from dotenv import load_dotenv
# from openai import OpenAI


__all__ = ["generate_prompt"]

# load_dotenv()

# client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Function to encode the image
def encode_image(image_path):
    with Image.open(image_path) as image_file:
        buffered = io.BytesIO()
        resized_img = image_file.resize((150, 150))
        resized_img.save(buffered, format="PNG")
        return base64.b64encode(buffered.getvalue()).decode("utf-8")

def generate_prompt():
    # Getting the Base64 string
    # base64_image = encode_image(image_path)
    
    dense_prompt = """
    Analyze and assess this image for its aesthetic qualities. Return a prompt that will be used to generate
    a design based on the characteristics of the image. Accurately and faithfully recreate the graphic image 
    with your description. 
    I want the design just with a transparent background. Keep the prompt to less than 1000 words.
    """

    # response = client.responses.create(
    #     model="gpt-4o",
    #     input=[
    #         {
    #             "role": "user",
    #             "content": [
    #                 { "type": "input_text", "text": dense_prompt },
    #                 {
    #                     "type": "input_image",
    #                     "image_url": f"data:image/jpeg;base64,{base64_image}",
    #                 },
    #             ],
    #         }
    #     ],
    # ) Deprecated

    return dense_prompt