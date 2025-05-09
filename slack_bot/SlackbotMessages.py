class SlackBotMessages:
    VerboseConfirmation = "I will generate verbose update messages. Keeping you up to date on my task completion."
    Download = "Your submitted image has been downloaded..."
    PromptError = "There must be a flag and a body to this message to give the model direction. Try again using --inject followed by a prompt."
    GeneratorError = "Something went wrong with ImageGeneratorBot :( Image request did not pass the vibe check. Try being less vulgar?"
    PromptGenerated = "Seed prompt has been generated:"
    ImageGenerated = "Image has been generated..."
    ImageResized = "Image has been resized..."
    ImageSaved = "Image has been resized..."
    TrySending = "Image has been saved locally. I will try sending it in this channel..."

    def HelpMessage(self, user):
        return (f"Hello <@{user}>! :wave:\n\n"
                "To generate an AI image, please follow these steps:\n"
                "1. **Mention me** in your message (`@ImageGeneratorBot`).\n"
                "2. **Attach a valid image file** that I can use as a seed for your prompt.\n\n"
                "I'll handle the rest and create your AI-generated image! :art:")

    def GeneratorConfirmation(self, filename):
        f"Slack Bot will send a file with the name {filename} here... :hourglass_flowing_sand:"