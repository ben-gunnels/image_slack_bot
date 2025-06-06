import os
import datetime
from slack_helper import *
from generate_prompt import *
from generate_image import *
from utils import *
from archiver import *
from vars import *
from SlackbotMessages import SlackBotMessages
from reformat_image import resize_image
from dropbox_helper import upload_to_shared_folder
from archiver import list_files_in_channel

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
    "inject",
    "series",
    "archive"
}

valid_channels = set(CHANNEL_MAP.keys())

class EventHandler:
    def __init__(self, logger, event_type: str, channel_id: str, user: str, text: str, files: list):
        if channel_id not in valid_channels:
            return 
        
        if event_type not in EVENTS:
            return 
        
        self.event_type = event_type # app_mention, file_shared, message, etc.
        self.channel_id = channel_id
        self.input_filename = None

        self.dropbox_folder_id = CHANNEL_MAP[channel_id]
        
        self.user = user # The Slack User ID of the message sender
        self.text = text # The text body of the slack message
        self.files = files # Files embedded in the slack message
        self.logger = logger # Common logging object

        self.mode = None # image-edit, prompt-only

        # Flags passed by user
        self.verbose = False # Gives step by step feedback of the generation process
        self.help = False # User invokes help instructions from the bot
        self.reformat = False # User only requires the uploaded image to be reformatted to the appropriate dimensions
        self.inject = False # Allows the user to add text to the image generation prompt directly
        self.series = False # Allows the user to enter iterative arguments to create a batch from one image or prompt. 
        self.archive = False # Will prompt the bot to output all of the generated files to Dropbox
        self.allow_archive = False # This parameter must be manually changed to True to allow archiving

        # Series Attributes
        self.series_params = None
        self.series_iterator = 0

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

        if self.archive and self.allow_archive:
            self._handle_archive()
            
        if self.series: # Returns the list of series params
            self.series_params = get_series_params(clean_text(self.text))
            if not (len(self.series_params[0])) or (len(self.files) > 1): # The series must contain parameters and only 1 file
                send_message(self.channel_id, messages.SeriesError)
                return

        if self.files: # The user has submitted a file to be edited
            self._handle_files_shared()
        else: # The user has not submitted a file to be edited
            self._handle_direct_prompt()

    def _handle_files_shared(self):
        """
            Sends each file in the batch off to be handled by the file handler.
            Treats a batch continuously.
        """
        self.mode = "image-edit"
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

        if self.reformat:
            self._get_file_from_user(file, ext)
            # Just reformat the image and send it
            output_filename = f"image_outputs/gen_image_{self.input_filename.split('/')[-1][:-4]}.{ext}"
            send_message(self.channel_id, messages.GeneratorConfirmation(output_filename.split('/')[-1]))

            self._handle_image_reformatting(output_filename)
            self._cleanup()
            return
        
        # SERIES Handling
        if self.series:
            while self.series_iterator < len(self.series_params[0]):
                self._get_file_from_user(file, ext)
                self._facilitate_output(self.input_filename.split('/')[-1][:-4])
                self.series_iterator += 1
        
        else:
            self._get_file_from_user(file, ext)
            self._facilitate_output(self.input_filename.split('/')[-1][:-4])
    
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
        
        self.mode = "prompt-only"
        
        # SERIES Handling
        if self.series:
            while self.series_iterator < len(self.series_params[0]):
                # Name the file for output
                now = datetime.datetime.now()
                self._facilitate_output(now.strftime('%Y-%m-%d-%H-%M-%S'))
                self.series_iterator += 1

        else:
            # Name the file for output
            now = datetime.datetime.now()
            self._facilitate_output(now.strftime('%Y-%m-%d-%H-%M-%S'))

    def _handle_archive(self):
        """
            Archives the image files sent by slack bot and sends them to the dropbox folder 
            corresponding to the current channel.
        """
        successes = 0
        send_message(self.channel_id, messages.ArchiveConfirmation)
        start_ts = to_unix_timestamp("2025-01-01") # Start of the year
        _, end_ts = get_today_unix_range()

        files = list_files_in_channel(self.channel_id, start_ts, end_ts)

        send_message(self.channel_id, f"{len(files)} # of files found.")

        for file in files:
            endpoint = file.get('name')
            if not endpoint or endpoint == "error":
                continue
            filename = "image_outputs/" + endpoint
            url = file.get('url_private', '')
            if url:
                download_slack_file(url, filename)
                response = upload_to_shared_folder(filename, self.dropbox_folder_id)
                if (response.get("error")):
                    pass
                else:
                    successes += 1
                    
        if successes == len(files):
            send_message(self.channel_id, messages.DropboxSuccessful + " for all files in batch.")
                

    def _facilitate_output(self, input_filename):
        """
            Handles the naming of the output file, sending confirmation messages.
            Calls the generate image and send function. 
        """
        # Unconditionally set the extension to png if it is being generated
        output_filename = f"image_outputs/gen_image_{input_filename}.png" 
        send_message(self.channel_id, messages.GeneratorConfirmation(output_filename.split('/')[-1]))

        if self.verbose:
            send_message(self.channel_id, messages.VerboseConfirmation)

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
            # Send the output to dropbox
            send_message(self.channel_id, messages.AttemptingDropbox)

            try:
                response = upload_to_shared_folder(output_filename, self.dropbox_folder_id)
                if response.get("error"):
                    send_message(self.channel_id, messages.DropboxUploadError(response))
                else:
                    send_message(self.channel_id, messages.DropboxSuccessful)
            except Exception as e:
                print(f"Dropbox file upload failed: {e}")

            send_file(self.channel_id, output_filename)
            self._cleanup(output_filename)

        
    def _handle_image_prompt_and_generation(self, output_filename):
        """"
            Generates the image prompt and the generation of an Ai generated image.
            It handles the cases of prompt-only and image-edit.
                prompt-only: No image has been uploaded to the message. The generator will use the client.image.create method to
                    try to create an an image based on the text body given by the sender.
                image-edit: An image has been uploaded to the message. The generator will use the client.image.edit method
                    to try to edit the given image and return a suitable design.
        """
        try:
            generated_prompt = self._generate_prompt(self.mode)

            generated_image = self._generate_image(self.mode, generated_prompt)

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
        
        except Exception as e:
            send_message(self.channel_id, messages.GeneratorError(e))
            print(f"Image generation could not be completed. {e}")

    def _generate_prompt(self, mode):
        """
            Create the prompt needed to generate the image. 
            Handles the case where a vanilla prompt is entered and when an Image is being edited. 
        
        """
        if self.inject:
            # Inject the clean text into the prompt to help add instructions.
            text = clean_text(self.text)

            # SERIES Handling
            if self.series:
                series_replacements = get_series(self.text)

                for i, s in enumerate(series_replacements):
                    # Replace the series arguments with the current argument via the iterator.
                    text = text.replace(s, self.series_params[i][self.series_iterator])
            
        # Get the dense prompt
        if mode == "prompt-only":
            # This will only run if inject is true as it's being handled in the parent function
            generated_prompt = generate_prompt(mode="prompt-only", injection=text)
            generated_prompt += " Ensure the image has a transparent background."
        
        if mode == "image-edit":
            # Just return the boilerplate prompt
            if self.inject:
                generated_prompt = generate_prompt(mode="image-edit") + text
            else:
                print("generating prompt...")
                generated_prompt = generate_prompt(mode="image-edit")

        self.logger.info("Prompt generated")
        if self.verbose:
            send_message(self.channel_id, messages.PromptGenerated)
            send_message(self.channel_id, generated_prompt)
        
        return generated_prompt
    
    def _generate_image(self, mode, generated_prompt):
        """
            Makes the call to generate the image based on whether the mode is prompt-only or image-edit. 
        """
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

        # Send the output to dropbox
        send_message(self.channel_id, messages.AttemptingDropbox)
        try:    
            upload_to_shared_folder(output_filename, self.dropbox_folder_id)
        except Exception as e:
            send_message(self.channel_id, messages.DropboxUploadError(e))

        send_message(self.channel_id, messages.DropboxSuccessful)

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
        if self.input_filename and os.path.exists(self.input_filename):
            os.remove(self.input_filename)
   
        if output_filename and os.path.exists(output_filename):
            os.remove(output_filename)



