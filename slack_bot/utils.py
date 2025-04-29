import re
import shutil
import os

def remove_directory_recursively(path):
    """
    Removes a directory recursively.

    Args:
        path: The path to the directory to remove.
    """
    try:
        shutil.rmtree(path)
        print(f"Directory '{path}' and its contents have been removed successfully.")
    except FileNotFoundError:
        print(f"Error: Directory '{path}' not found.")
    except OSError as e:
       print(f"Error: Could not remove directory '{path}'. Reason: {e}")

def find_flags(text):
    pattern = r'--(\w+)'  # Look for -- followed by letters, digits, underscores
    flags = re.findall(pattern, text)
    return set(flags)