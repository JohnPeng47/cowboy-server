import functools
import random
import string
import uuid


# nested level get() function
def resolve_attr(obj, attr, default=None):
    """Attempts to access attr via dotted notation, returns none if attr does not exist."""
    try:
        return functools.reduce(getattr, attr.split("."), obj)
    except AttributeError:
        return default


def gen_random_name():
    """
    Generates a random name using ASCII, 8 characters in length
    """

    return "".join(random.choices(string.ascii_lowercase, k=8))


def generate_id():
    """
    Generates a random UUID
    """
    return str(uuid.uuid4())
