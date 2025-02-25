import uuid
import secrets
import string
import nanoid

def generate_random_string(length:int=6) -> str:
    choice_characters = string.ascii_uppercase+ string.digits
    random_string = ''.join(secrets.choice(choice_characters) for _ in range(length))
    return random_string

def generate_unique_socket_room_id() -> str:
    alphabet = string.ascii_lowercase+ string.digits
    return nanoid.generate(alphabet,50)

def generate_client_id() -> str:
    return str(uuid.uuid4())

def generate_client_secret() -> str:
    return secrets.token_urlsafe(50)