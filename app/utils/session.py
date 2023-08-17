from cryptography.fernet import Fernet
from flask.sessions import SessionMixin

REQUIRED_SESSION_VALUES = ['uuid', 'config', 'key', 'auth']


def generate_key() -> bytes:
    """Generates a key for encrypting searches and element URLs

    Returns:
        str: A unique Fernet key

    """
    # Generate/regenerate unique key per user
    return Fernet.generate_key()


def valid_user_session(session: dict | SessionMixin) -> bool:
    """Validates the current user session

    Args:
        session: The current Flask user session

    Returns:
        bool: True/False indicating that all required session values are
              available

    """
    # Generate secret key for user if unavailable
    for value in REQUIRED_SESSION_VALUES:
        if value not in session:
            return False

    return True
