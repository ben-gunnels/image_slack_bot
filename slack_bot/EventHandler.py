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
    "reformat",
    "inject"
}

VALID_CHANNEL_1 = os.getenv("VALID_CHANNEL_1")
VALID_CHANNEL_2 = os.getenv("VALID_CHANNEL_2")

valid_channels = set({VALID_CHANNEL_1, VALID_CHANNEL_2})

class EventHandler:
    def __init__(self, logger, event_type: str, channel_id: str, user: str, text: str, files: list):
        if channel_id not in valid_channels:
            return 
        
        if event_type not in EVENTS:
            return 
        
        self.event_type = event_type
        self.channel_id = channel_id
        
        self.user = user
        self.text = text
        self.files = files
        self.logger = logger

        # Flags passed by user
        self.verbose = False
        self.help = False
        self.reformat = False
        self.inject = False

        try:
            remove_directory_recursively("user_submitted_files")
            remove_directory_recursively("image_outputs")
        except:
            pass

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
            self._handle_files_shared()

    def _handle_message(self):
        """
            Used to handle vanilla messages sent in the specified slack channel. 
        """
        send_message(self.channel_id, f"Hello {self.user} -- from Slack Bot")

    def _handle_app_mention(self):
        if self.help:
            message = (
                f"Hello <@{self.user}>! :wave:\n\n"
                "To generate an AI image, please follow these steps:\n"
                "1. **Mention me** in your message (`@ImageGeneratorBot`).\n"
                "2. **Attach a valid image file** that I can use as a seed for your prompt.\n\n"
                "I'll handle the rest and create your AI-generated image! :art:"
            )
            send_message(self.channel_id, message)
        if self.files:
            self._handle_files_shared()
        else:
            self._handle_prompt()

    def _handle_files_shared(self):
        """
            Sends each file in the batch off to be handled by the file handler.
        """
        for file in self.files:
            self._handle_file_shared(file)
        return

    def _handle_file_shared(self, file):
        """
            This process downloads the file from slack through the channel.
            It then uploads the image along with the prompt to the OpenAI image generation API.
            The file is then sent through the slack channel. 
        """
        if file:
            ext = file.get("filetype").lower()
        else:
            ext = "png"
        now = datetime.datetime.now()
        self.input_filename = f"user_submitted_files/{now.strftime('%Y-%m-%d-%H-%M-%S')}.{ext}"

        download_slack_file(file["url_private"], self.input_filename)
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

        if self._handle_image_prompt_and_generation(output_filename) == 200:
            send_file(self.channel_id, output_filename)
            self._cleanup(output_filename)
        else:
            send_message(self.channel_id, f"Something went wrong with ImageGeneratorBot :( Image request could not be generated.")
    
    def _handle_prompt(self):
        if not self.inject:
            self.logger.error("No valid message body.")
            send_message(self.channel_id, "There must be a body to this message to give the model direction. Try again using --inject followed by a prompt.")
            return
        
        # Name the file for output
        now = datetime.datetime.now()
        output_filename = f"image_outputs/gen_image_{now.strftime('%Y-%m-%d-%H-%M-%S')}.png"
        send_message(self.channel_id, f"Slack Bot will send a file with the name {output_filename.split('/')[-1]} here... :hourglass_flowing_sand:")

        if self._handle_image_prompt_and_generation(output_filename, mode="prompt-only") == 200:
            send_file(self.channel_id, output_filename)
            self._cleanup(output_filename)
        else:
            send_message(self.channel_id, f"Something went wrong with ImageGeneratorBot :( Image request could not be generated.")

        
    def _handle_image_prompt_and_generation(self, output_filename, mode="image-edit"):
        try:
            if self.inject:
                # Inject the clean text into the prompt to help add instructions.
                self.text = clean_text(self.text)
            
            # Get the dense prompt
            if mode == "prompt-only":
                # This will only run if inject is true as it's being handled in the parent function
                generated_prompt = generate_prompt(mode="inject", injection=self.text)
                generated_prompt += " Ensure the image has a transparent background."
            
            if mode == "image-edit":
                # Just return the boilerplate prompt
                generated_prompt = generate_prompt(mode="static")
                
            self.logger.info("Prompt generated")
            if self.verbose:
                send_message(self.channel_id, "Seed prompt has been generated:")
                send_message(self.channel_id, generated_prompt)

            # Make a call to OpenAi image generation model based on the prompt
            if mode == "prompt-only":
                generated_image = generate_image(self.logger, generated_prompt)

            if mode == "image-edit":
                generated_image = edit_image(self.logger, generated_prompt, self.input_filename)

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



