import re
import shutil
import time
import datetime
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

def clean_text(text):
    # Remove things in angle brackets
    text = re.sub(r'<[^>]+>', '', text)

    # Remove flags starting with --
    text = re.sub(r'\s--\S+', '', text)

    # Strip leading/trailing whitespace
    text = text.strip()

    return text

def get_series(text):
    """
        Gets the series literals and returns them in a list.
    """
    series = list(re.findall(r"\{.*?\}", text))
    return series


def get_series_params(text):
    """
        Returns a 2D list of parameters for the image generator prompt.
        The index of the inner list signifies the relative location of a series variable in the injection.
        E.g.
            text = 'Replace the number with {1, 2, 3, 4} and the fruit with {orange, grape, apple, banana}
            returns [[1, 2, 3, 4], [orange, grape, apple, banana]]
    """
    series_params = []
    series = list(re.findall(r"\{(.*?)\}", text))

    if not series:   
        return None
    
    for s in series:
        series_params.append([c.strip() for c in s.split(",")])

    length_counts = {len(s) for s in series_params}

    if len(length_counts) != 1: # Invalid, all arguments must be the same length
        return None

    return series_params

# Convert a date string to Unix timestamp
def to_unix_timestamp(date_str):
    return int(time.mktime(datetime.datetime.strptime(date_str, "%Y-%m-%d").timetuple()))

def get_today_unix_range():
    # Get today's date at midnight
    today = datetime.datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    start_ts = int(time.mktime(today.timetuple()))
    
    # Get end of today (11:59:59 PM)
    end_ts = int(time.mktime((today + datetime.timedelta(days=1, seconds=-1)).timetuple()))

    return start_ts, end_ts