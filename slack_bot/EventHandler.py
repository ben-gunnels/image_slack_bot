import os
import datetime
from dotenv import load_dotenv
from slack_helper import *
from generate_prompt import *
from generate_image import *
from utils import *
from SlackbotMessages import SlackBotMessages
from reformat_image import resize_image

load_dotenv()

messages = SlackBotMessages()

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
VALID_CHANNEL_3 = os.getenv("VALID_CHANNEL_3")

valid_channels = set({VALID_CHANNEL_1, VALID_CHANNEL_2, VALID_CHANNEL_3})

class EventHandler:
    def __init__(self, logger, event_type: str, channel_id: str, user: str, text: str, files: list):
        if channel_id not in valid_channels:
            return 
        
        if event_type not in EVENTS:
            return 
        
        self.event_type = event_type # app_mention, file_shared, message, etc.
        self.channel_id = channel_id
        
        self.user = user # The Slack User ID of the message sender
        self.text = text # The text body of the slack message
        self.files = files # Files embedded in the slack message
        self.logger = logger # Common logging object

        # Flags passed by user
        self.verbose = False # Gives step by step feedback of the generation process
        self.help = False # User invokes help instructions from the bot
        self.reformat = False # User only requires the uploaded image to be reformatted to the appropriate dimensions
        self.inject = False # Allows the user to add text to the image generation prompt directly

        try:
            # Save memory by removing any existing folder structures from the app
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
        if self.event_type == "app_mention":
            self.logger.info("Handling app_mention...")
            self._handle_app_mention()
        elif self.event_type == "file_shared":
            self._handle_files_shared()

    def _handle_app_mention(self):
        """
            Main entry when the bot is mentioned in the message. 
            It facilitates the functionality that the user is seeking.
            Sends a help message if the user solicits help.
            Initiates the process for file download and image generation.
            If no file is submitted it invokes the direct prompt image generator.
        """
        if self.help: # If the help flag is present
            message = messages.HelpMessage(self.user)
            send_message(self.channel_id, message)
        if self.files:
            self._handle_files_shared()
        else:
            self._handle_direct_prompt()

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

        self._get_file_from_user(file, ext)

        if self.reformat:
            # Just reformat the image and send it
            output_filename = f"image_outputs/gen_image_{self.input_filename.split('/')[-1][:-4]}.{ext}"
            send_message(self.channel_id, messages.GeneratorConfirmation(output_filename.split('/')[-1]))

            self._handle_image_reformatting(output_filename)
            self._cleanup()
            return
        
        # Unconditionally set the extension to png if it is being generated
        output_filename = f"image_outputs/gen_image_{self.input_filename.split('/')[-1][:-4]}.png" 
        send_message(self.channel_id, messages.GeneratorConfirmation(output_filename.split('/')[-1]))

        if self.verbose:
            send_message(self.channel_id, messages.VerboseConfirmation)

        self._generate_image_and_send(output_filename)
    
    def _handle_direct_prompt(self):
        """
        The function directly takes a prompt as a message and delivers an image directly.
        It calls the openAiClient.image.generate method.
        This function requires a body to be given in the message. 
        """
        if not self.inject:
            self.logger.error("No valid message body.")
            send_message(self.channel_id, messages.PromptError)
            return
        
        # Name the file for output
        now = datetime.datetime.now()
        output_filename = f"image_outputs/gen_image_{now.strftime('%Y-%m-%d-%H-%M-%S')}.png"
        send_message(self.channel_id, messages.GeneratorConfirmation(output_filename.split('/')[-1]))

        self._generate_image_and_send(output_filename)

    def _get_file_from_user(self, file, ext):
        """
            Function handles trying to download the file that a user attached to the message.
            As a side effect it generates the input filename for use later. 
        """
        # Name the file that will be saved from the User's message
        now = datetime.datetime.now()
        self.input_filename = f"user_submitted_files/{now.strftime('%Y-%m-%d-%H-%M-%S')}.{ext}"

        # From slack helper
        download_slack_file(file["url_private"], self.input_filename)
        if self.verbose:
            send_message(self.channel_id, messages.Download)
    
    def _generate_image_and_send(self, output_filename):
        """
            Handles the end stage of the image generation process. It makes a call to the image prompter and generator.
            Handles the resizing and sends the message. 
            This function acts as an intermediary between the caller and the _handle_image_prompt_and_generation function.
        
        """
        if self._handle_image_prompt_and_generation(output_filename) == 200:
            send_file(self.channel_id, output_filename)
            self._cleanup(output_filename)
        else:
            send_message(self.channel_id, messages.GeneratorError)

        
    def _handle_image_prompt_and_generation(self, output_filename, mode="image-edit"):
        """"
            Generates the image prompt and the generation of an Ai generated image.
            It handles the cases of prompt-only and image-edit.
                prompt-only: No image has been uploaded to the message. The generator will use the client.image.create method to
                    try to create an an image based on the text body given by the sender.
                image-edit: An image has been uploaded to the message. The generator will use the client.image.edit method
                    to try to edit the given image and return a suitable design.
        """
        try:
            generated_prompt = self._generate_prompt(mode)

            generated_image = self._generate_image(mode, generated_prompt)

            # Reformat the image to proper dimensions and specs
            generated_image = resize_image(generated_image)
            
            self.logger.info("Image Resized")
            if self.verbose:
                send_message(self.channel_id, messages.ImageResized)

            generated_image.save(output_filename, dpi=(300, 300))
            if self.verbose:
                send_message(self.channel_id, messages.TrySending)
            self.logger.info(f"Generated image saved to {output_filename}")

            return 200
        
        except Exception:
            send_message(self.channel_id, messages.GeneratorError)
            print(f"Image generation could not be completed.")

    def _generate_prompt(self, mode):
        if self.inject:
                # Inject the clean text into the prompt to help add instructions.
                self.text = clean_text(self.text)
            
        # Get the dense prompt
        if mode == "prompt-only":
            # This will only run if inject is true as it's being handled in the parent function
            generated_prompt = generate_prompt(mode="prompt-only", injection=self.text)
            generated_prompt += " Ensure the image has a transparent background."
        
        if mode == "image-edit":
            # Just return the boilerplate prompt
            if self.inject:
                generated_prompt = generate_prompt(mode="image-edit") + self.text
            else:
                generated_prompt = generate_prompt(mode="image-edit")

        self.logger.info("Prompt generated")
        if self.verbose:
            send_message(self.channel_id, messages.PromptGenerated)
            send_message(self.channel_id, generated_prompt)
        
        return generated_prompt
    
    def _generate_image(self, mode, generated_prompt):
        # Make a call to OpenAi image generation model based on the prompt
        if mode == "prompt-only":
            generated_image = generate_image(self.logger, generated_prompt)

        if mode == "image-edit":
            generated_image = edit_image(self.logger, generated_prompt, self.input_filename)

        if self.verbose: 
            send_message(self.channel_id, messages.ImageGenerated)
        
        return generated_image

    def _handle_image_reformatting(self, output_filename):
        """
            Function is called when the --reformat flag is invoked.
            It more directly and succinctly downloads the submitted image and reformats it to the correct size.
        """
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
            send_message(self.channel_id, messages.ImageSaved)

        # Send the output to slack    
        send_file(self.channel_id, output_filename, "Here's your reformatted image!")

    def _mkdirs(self, folder_path):
        """
            Initializes the necessary folders used for image saving and generation.
        """
        # Check if the folder exists
        if not os.path.exists(folder_path):
            os.makedirs(folder_path)
            self.logger.info(f"Created directory: {folder_path}")
        else:
            self.logger.info(f"Directory already exists: {folder_path}")

    def _set_flags(self):
        """
            Initializes the flag properties for the object. 
            Finds the flags in the message which are prepended by --.
        """
        self.flags = find_flags(self.text)

        for flag in VALID_FLAGS:
            if flag in self.flags:
                setattr(self, flag, True) 

    def _cleanup(self, output_filename):
        """
            Removes the images that have been saved locally and temporarily.
            Removes the input image files and the generated output files.
        """
        # Remove stored slack image
        if os.path.exists(self.input_filename):
            os.remove(self.input_filename)
   
        if os.path.exists(output_filename):
            os.remove(output_filename)



