import re

def find_flags(text):
    pattern = r'--(\w+)'  # Look for -- followed by letters, digits, underscores
    flags = re.findall(pattern, text)
    return set(flags)