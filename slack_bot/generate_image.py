import requests 
import os
import base64
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

__all__ = ["generate_image", "edit_image"]

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
model = "gpt-image-1"  # "dall-e-2 "

def edit_image(logger, prompt, input_filename):
    try:
        if os.path.exists(input_filename):
            print(f"File is valid and can be used for image generation.")
        
        else:
            print(f"File is invalid and cannot be used for image generation.")

        if model == "dall-e-2":
            response = client.images.generate(
                model=model,
                prompt=prompt[:1000],
                size="1024x1024",
                n=1,
                response_format="b64_json", # Comment this line when using gpt-image-1 model
            )
        
        elif model == "gpt-image-1":
            response = client.images.edit(
                model=model,
                prompt=prompt[:1000], # Input prompt is restricted to 100 characters
                image=(
                    open(input_filename, 'rb')
                ),
                size="1024x1024",
                n=1,
            )

        image_base64 = response.data[0].b64_json
        image_bytes = base64.b64decode(image_base64)

        return image_bytes
    except Exception as e:
        print(f"Error during image generation: {e}")
        logger.info(f"Error during image generation: {e}")
        return {"error": str(e), "exception": e}

def generate_image(logger, prompt):
    try:
        if model == "dall-e-2":
            response = client.images.generate(
                model=model,
                prompt=prompt[:1000],
                size="1024x1024",
                n=1,
                response_format="b64_json", # Comment this line when using gpt-image-1 model
            )
        
        elif model == "gpt-image-1":
            response = client.images.generate(
                model=model,
                prompt=prompt[:1000], # Input prompt is restricted to 100 characters
                size="1024x1024",
                n=1,
            )

        image_base64 = response.data[0].b64_json
        image_bytes = base64.b64decode(image_base64)

        return image_bytes
    except Exception as e:
        print(f"Error during image generation: {e}")
        logger.info(f"Error during image generation: {e}")
        return {"error": str(e), "exception": e}