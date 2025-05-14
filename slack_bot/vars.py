import os
from dotenv import load_dotenv

__all__ = ["CHANNEL_MAP"]

VALID_CHANNEL_1 = os.getenv("VALID_CHANNEL_1")
DROPBOX_1 = os.getenv("DROPBOX_1")

VALID_CHANNEL_2 = os.getenv("VALID_CHANNEL_2")
DROPBOX_2 = os.getenv("DROPBOX_2")

VALID_CHANNEL_3 = os.getenv("VALID_CHANNEL_3")
DROPBOX_3 = os.getenv("DROPBOX_3")

VALID_CHANNEL_4 = os.getenv("VALID_CHANNEL_4")
DROPBOX_4 = os.getenv("DROPBOX_4")

DROPBOX_1 = os.getenv()

CHANNEL_MAP = {
    VALID_CHANNEL_1: DROPBOX_1,
    VALID_CHANNEL_2: DROPBOX_2,
    VALID_CHANNEL_3: DROPBOX_3,
    VALID_CHANNEL_4: DROPBOX_4
}