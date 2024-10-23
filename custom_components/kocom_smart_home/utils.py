import random
import string
import hashlib

from .const import LOGGER

def generate_digest_header(username: str, password: str, uri: str, nonce: str) -> str:
    """Creates digest authentication header string."""
    username_hash = hashlib.md5(f"{username}:kbranch:{password}".encode()).hexdigest()
    uri_hash = hashlib.md5(f"GET:{uri}".encode()).hexdigest()
    response = hashlib.md5(f"{username_hash}:{nonce}:{uri_hash}".encode()).hexdigest()
    return f'Digest username="{username}", realm="kbranch", nonce="{nonce}", uri="{uri}", response="{response}"'

#def generate_fcm_token(input_string, length=163) -> str:
#    """Generates Firebase Cloud Messaging token."""
#    random.seed(input_string)
#    characters = string.ascii_letters + string.digits
#    fcm_token = ''.join(random.choice(characters) for _ in range(length))
#    LOGGER.debug("Generated FCM Token: %s", fcm_token)
#    return fcm_token

def generate_fcm_token(length: int = 163) -> str:
    """Generate a random FCM token."""
    token_chars = string.ascii_letters + string.digits + "-_"
    return ''.join(random.choice(token_chars) for _ in range(length))
