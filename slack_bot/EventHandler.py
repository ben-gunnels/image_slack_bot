import os
import datetime
from slack_helper import *
from generate_prompt import *
from generate_image import *
from utils import *
from reformat_image import resize_image
from dotenv import load_dotenv

load_dotenv()

EVENTS = {
    "message",
    "app_mention",
    "file_shared"
}

VALID_FLAGS = {
    "verbose",
    "help",
    "reformat"
}

VALID_CHANNEL = os.getenv("VALID_CHANNEL")

class EventHandler:
    def __init__(self, logger, event_type: str, channel_id: str, private_url: str, user: str, text: str, files):
        if channel_id != VALID_CHANNEL:
            return 
        
        if event_type not in EVENTS:
            return 
        
        self.event_type = event_type
        self.channel_id = channel_id
        
        self.private_url = private_url
        self.user = user
        self.text = text
        self.files = files
        self.logger = logger

        # Flags passed by user
        self.verbose = False
        self.help = False
        self.reformat = False

        remove_directory_recursively("user_submitted_files")
        remove_directory_recursively("image_outputs")

        self._mkdirs("user_submitted_files")
        self._mkdirs("image_outputs")

        self._set_flags()

    def handle_event(self):
        """
            Delegates the handling of the message to the specified function. 
        """
        if self.event_type == "message":
            self._handle_message()
        elif self.event_type == "app_mention":
            self.logger.info("Handling app_mention...")
            self._handle_app_mention()
        elif self.event_type == "file_shared":
            self._handle_file_shared()

    def _handle_message(self):
        """
            Used to handle vanilla messages sent in the specified slack channel. 
        """
        send_message(self.channel_id, f"Hello {self.user} -- from Slack Bot")

    def _handle_app_mention(self):
        self.logger.info(f"Handling app_mention {self.private_url}")
        if self.help:
            message = (
                f"Hello <@{self.user}>! :wave:\n\n"
                "To generate an AI image, please follow these steps:\n"
                "1. **Mention me** in your message (`@ImageGeneratorBot`).\n"
                "2. **Attach a valid image file** that I can use as a seed for your prompt.\n\n"
                "I'll handle the rest and create your AI-generated image! :art:"
            )
            send_message(self.channel_id, message)
        if self.private_url:
            self._handle_file_shared()
    

    def _handle_file_shared(self):
        if self.files:
            ext = self.files[0].get("filetype").lower()
        else:
            ext = "png"
        now = datetime.datetime.now()
        self.input_filename = f"user_submitted_files/{now.strftime('%Y-%m-%d-%H-%M-%S')}.{ext}"

        download_slack_file(self.private_url, self.input_filename)
        if self.verbose:
            send_message(self.channel_id, "Your submitted image has been downloaded...")

        if self.reformat:
            output_filename = f"image_outputs/gen_image_{self.input_filename.split('/')[-1][:-4]}.{ext}"
            send_message(self.channel_id, f"Slack Bot will send a file with the name {output_filename.split('/')[-1]} here... :hourglass_flowing_sand:")

            self._handle_image_reformatting(output_filename)
            self._cleanup()
            return

        output_filename = f"image_outputs/gen_image_{self.input_filename.split('/')[-1][:-4]}.png" # Unconditionally set the extension to png if it is being generated
        send_message(self.channel_id, f"Slack Bot will send a file with the name {output_filename.split('/')[-1]} here... :hourglass_flowing_sand:")

        if self.verbose:
            send_message(self.channel_id, "I will generate verbose update messages. Keeping you up to date on my task completion.")

        if self._handle_image_prompt_and_generation(self.input_filename, output_filename) == 200:
            send_file(self.channel_id, output_filename)
            self._cleanup(output_filename)
        else:
            send_message(self.channel_id, f"Something went wrong with ImageGeneratorBot :( Image request could not be generated.")

    def _handle_image_prompt_and_generation(self, input_filename, output_filename):
        try:
            # Get the dense prompt
            generated_prompt = generate_prompt()
            self.logger.info("Prompt generated")
            if self.verbose:
                send_message(self.channel_id, "Seed prompt has been generated:")
                send_message(self.channel_id, generate_prompt)

            # Make a call to OpenAi image generation model based on the prompt
            generated_image = generate_image(self.logger, generated_prompt, input_filename)
            self.logger.info("Image generated")
            if self.verbose: 
                send_message(self.channel_id, "Image has been generated...")

            # Reformat the image to proper dimensions and specs
            generated_image = resize_image(generated_image)
            self.logger.info("Image Resized")
            if self.verbose:
                send_message(self.channel_id, "Image has been resized...")

            generated_image.save(output_filename, dpi=(300, 300))
            if self.verbose:
                send_message(self.channel_id, "Image has been saved locally. I will try sending it in this channel...")
            self.logger.info(f"Generated image saved to {output_filename}")
            return 200
        except Exception:
            print(f"Image generation could not be completed.")

    def _handle_image_reformatting(self, output_filename):
        # Only handle tasks related to reformating the image submitted.
        with open(self.input_filename, "rb") as f:
            image_bytes = f.read()

        if self.verbose:
            send_message(self.channel_id, "Resizing image...")
        resized_image = resize_image(image_bytes)
        
        if self.verbose:
            send_message(self.channel_id, "Saving result...")
        resized_image.save(output_filename, dpi=(300, 300))

        if self.verbose:
            send_message(self.channel_id, "Image has been saved locally. I will try sending it in this channel...")
        # Send the output to slack    
        send_file(self.channel_id, output_filename, "Here's your reformatted image!")

    def _mkdirs(self, folder_path):
        # Check if the folder exists
        if not os.path.exists(folder_path):
            os.makedirs(folder_path)
            self.logger.info(f"Created directory: {folder_path}")
        else:
            self.logger.info(f"Directory already exists: {folder_path}")

    def _set_flags(self):
        self.flags = find_flags(self.text)

        for flag in VALID_FLAGS:
            if flag in self.flags:
                setattr(self, flag, True) 

    def _cleanup(self, output_filename):
        # Remove stored slack image
        if os.path.exists(self.input_filename):
            os.remove(self.input_filename)

        if os.path.exists(output_filename):
            os.remove(output_filename)



