import hashlib
import os
import re
from urllib.parse import urlparse

from bs4 import BeautifulSoup as bsoup
from flask import Request
from requests import exceptions, get


def gen_file_hash(path: str, static_file: str) -> str:
    """
    Generates a unique hash for a static file based on its contents.

    The function reads the contents of the static file located at the given path,
    computes the MD5 hash of the contents, and returns a new filename that includes
    the first 8 characters of the hash, preserving the original file extension.

    Args:
        path (str): The path to the directory containing the static file.
        static_file (str): The name of the static file.

    Returns:
        str: A new filename with the first 8 characters of the MD5 hash
             concatenated with the original file extension.
    """
    file_contents = open(os.path.join(path, static_file), "rb").read()
    file_hash = hashlib.md5(file_contents).hexdigest()[:8]
    filename_split = os.path.splitext(static_file)

    return filename_split[0] + "." + file_hash + filename_split[-1]


def read_config_bool(var: str) -> bool:
    """
    Read a boolean configuration value from environment variables.

    This function takes a configuration variable name as input and reads its value
    from the environment variables. The function then converts the value to a boolean
    based on common boolean representations, returning the boolean result.

    Args:
        var (str): The name of the configuration variable to read.

    Returns:
        bool: The boolean representation of the configuration value.
              True if the value is one of ("true", "t", "1", "yes", "y") (case-insensitive).
              False otherwise.
    """
    val = os.getenv(var, "0")
    val = val.lower() in ("true", "t", "1", "yes", "y")
    return val


def get_client_ip(r: Request) -> str:
    """
    Get the client's IP address from the request object.

    This function takes a Flask request object as input and extracts the client's IP
    address from the request's environment variables. It first checks if the
    "HTTP_X_FORWARDED_FOR" header is present. If the header is not found, it returns
    the client's IP address directly from the "REMOTE_ADDR" environment variable. If
    the header is present, it returns the IP address provided in the header.

    Args:
        r (Request): The Flask request object containing information about the client
                     request.

    Returns:
        str: The client's IP address extracted from the request.
    """
    if r.environ.get("HTTP_X_FORWARDED_FOR") is None:
        return r.environ["REMOTE_ADDR"]
    else:
        return r.environ["HTTP_X_FORWARDED_FOR"]


def get_request_url(url: str) -> str:
    """
    Get the request URL with optional HTTPS protocol.

    This function takes a URL string as input and returns the URL with an optional
    "https://" protocol. If the environment variable "HTTPS_ONLY" is set to True or
    any non-empty value (e.g., "1", "True", "yes"), it will replace "http://" with
    "https://" in the URL. Otherwise, it returns the original URL unchanged.

    Args:
        url (str): The URL string to be processed.

    Returns:
        str: The processed URL with optional "https://" protocol.
    """
    if os.getenv("HTTPS_ONLY", False):
        return url.replace("http://", "https://", 1)

    return url


def get_proxy_host_url(r: Request, default: str, root=False) -> str:
    """
    Get the proxy host URL from the request headers.

    This function extracts the proxy host URL from the request headers, which is useful
    when the application is running behind a reverse proxy. The function first checks
    the "X-Forwarded-Proto" header to determine the scheme (e.g., "http" or "https").
    If the "X-Forwarded-Host" header is present, it uses that as the host part of the URL.
    Otherwise, it falls back to the provided `default` value.

    Additionally, the `root` argument allows specifying whether to include the root path
    of the request URL. If `root` is True, the function includes the root path in the
    resulting URL.

    Args:
        r (Request): The Flask request object containing the headers.
        default (str): The default URL to use if the "X-Forwarded-Host" header is not present.
        root (bool, optional): Whether to include the root path in the URL. Defaults to False.

    Returns:
        str: The proxy host URL extracted from the request headers or the provided `default`.
    """
    scheme = r.headers.get("X-Forwarded-Proto", "https")
    http_host = r.headers.get("X-Forwarded-Host")

    full_path = r.full_path if not root else ''
    if full_path.startswith('/'):
        full_path = f'/{full_path}'

    if http_host:
        prefix = os.environ.get('WHOOGLE_URL_PREFIX', '')
        if prefix:
            prefix = f'/{re.sub("[^0-9a-zA-Z]+", "", prefix)}'
        return f'{scheme}://{http_host}{prefix}{full_path}'

    return default


def check_for_update(version_url: str, current: str) -> int:
    """
    Check for the latest version of Whoogle.

    This function retrieves the latest version number of Whoogle from the provided
    `version_url` and compares it with the current version number passed as `current`.
    If the latest version number is greater than the current version number, it
    indicates that an update is available.

    Args:
        version_url (str): The URL where the latest version of Whoogle is available.
        current (str): The current version number of Whoogle.

    Returns:
        int: The latest version number if an update is available, otherwise an empty string.
    """
    try:
        update = bsoup(get(version_url).text, "lxml")
        latest = update.select_one("[class=\"Link--primary\"]").string[1:]
        current = int("".join(filter(str.isdigit, current)))
        latest = int("".join(filter(str.isdigit, latest)))
        has_update = "" if current >= latest else latest
    except (exceptions.ConnectionError, AttributeError):
        # Ignore failures, assume current version is up to date
        has_update = ""

    return has_update


def get_abs_url(url, page_url):
    """
    Creates a valid absolute URL using a partial or relative URL and a base page URL.

    This function takes a `url` (partial or relative URL) and a `page_url` (base page URL).
    It returns the corresponding absolute URL based on the provided inputs.

    Args:
        url (str): The partial or relative URL to convert to an absolute URL.
        page_url (str): The base page URL from which the `url` is relative to.

    Returns:
        str: The absolute URL derived from the `url` and `page_url` inputs.
    """
    if url.startswith("//"):
        return f"https:{url}"
    elif url.startswith("/"):
        return f"{urlparse(page_url).netloc}{url}"
    elif url.startswith("./"):
        return f"{page_url}{url[2:]}"
    return url


def list_to_dict(lst: list) -> dict:
    """
    Convert a list into a dictionary.

    This function takes a list as input and returns a dictionary by pairing adjacent elements of the list.
    Each even-indexed element of the list becomes the key, and the next odd-indexed element becomes its corresponding value.
    The function assumes that the list contains an even number of elements.

    Args:
        lst (list): The list to be converted into a dictionary.

    Returns:
        dict: A dictionary created from the list elements, where each even-indexed element is a key and the next odd-indexed element is its corresponding value.
        If the input list has fewer than two elements, an empty dictionary is returned.
    """
    if len(lst) < 2:
        return {}
    return {lst[i].replace(' ', ''): lst[i+1].replace(' ', '')
            for i in range(0, len(lst), 2)}
