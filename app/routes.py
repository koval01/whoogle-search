import argparse
import base64
import io
import json
import logging
import multiprocessing
import os
import pickle
import urllib.parse as urlparse
import uuid
from datetime import datetime, timedelta
from functools import wraps

import requests
import waitress
from bs4 import BeautifulSoup as bsoup
from cryptography.exceptions import InvalidSignature
from cryptography.fernet import Fernet, InvalidToken
from flask import jsonify, make_response, request, redirect, render_template, \
    send_file, session, url_for, g, Response, abort
from requests import exceptions, get as http_get

from app import app
from app.filter import Filter
from app.models.config import Config
from app.models.endpoint import Endpoint
from app.request import Request, TorError
from app.utils.bangs import resolve_bang
from app.utils.filter import Question
from app.utils.misc import read_config_bool, get_client_ip, get_request_url, \
    check_for_update
from app.utils.results import bold_search_terms, \
    add_currency_card, check_currency, get_tabs_content
from app.utils.search import Search, needs_https, has_captcha
from app.utils.session import valid_user_session
from app.utils.widgets import *

# Load DDG bang json files only on init
bang_json = json.load(open(app.config.get("BANG_FILE"))) or {}

ac_var = "WHOOGLE_AUTOCOMPLETE"
autocomplete_enabled = os.getenv(ac_var, "1")


def get_search_name(tbm):
    """
    Get the name of a search type (tbm) from the configuration of header tabs.

    This function takes a search type (tbm) as input and searches for its corresponding name in the configuration of header
    tabs. The configuration is defined in the Flask app.config and contains a mapping of search types to their respective
    names.

    Parameters:
        tbm (str): The search type (tbm) for which the name is to be retrieved.

    Returns:
        str: The name of the search type (tbm), or None if not found.
    """
    for tab in app.config.get("HEADER_TABS").values():
        if tab["tbm"] == tbm:
            return tab["name"]


def auth_required(f):
    """
    Decorator function to enforce basic authentication for specified routes.

    This decorator function checks whether basic authentication credentials are provided by the user in the request
    headers. If valid credentials are present and match the configured username and password (obtained from the
    environment variables WHOOGLE_USER and WHOOGLE_PASS), the user is considered authenticated and the wrapped route
    handler function (`f`) is called with the provided arguments. If the user has already been authenticated through a
    valid user session, the decorator also allows access without requiring credentials, assuming that cookies are not
    disabled.

    If the user does not provide valid credentials or if the WHOOGLE_USER and WHOOGLE_PASS environment variables are not
    set, the function returns a 401 Unauthorized response with a "WWW-Authenticate" header to prompt for basic
    authentication.

    Parameters:
        f (function): The route handler function to be decorated.

    Returns:
        function: The decorated route handler function.
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        # do not ask password if cookies already present
        if (
                valid_user_session(session)
                and 'cookies_disabled' not in request.args
                and session['auth']
        ):
            return f(*args, **kwargs)

        auth = request.authorization

        # Skip if username/password not set
        whoogle_user = os.getenv("WHOOGLE_USER", "")
        whoogle_pass = os.getenv("WHOOGLE_PASS", "")
        if (not whoogle_user or not whoogle_pass) or (
                auth
                and whoogle_user == auth.username
                and whoogle_pass == auth.password):
            session['auth'] = True
            return f(*args, **kwargs)
        else:
            return make_response("Not logged in", 401, {
                "WWW-Authenticate": "Basic realm=\"Login Required\""})

    return decorated


def session_required(f):
    """
    Decorator function to enforce the presence of a valid user session.

    This decorator function checks whether a valid user session exists before executing the wrapped route handler
    function (`f`). If a valid session is present, the `f` function is called with the provided arguments. Otherwise,
    the function removes any existing "_permanent" attribute from the session and proceeds to clear out old sessions by
    checking the session files in the `SESSION_FILE_DIR`. It removes sessions that are larger than the specified maximum
    session size (`MAX_SESSION_SIZE`) or sessions that don't have a "valid" flag in their data.

    The decorator then returns the decorated function (`f`) after performing the session checks and cleanup.

    Parameters:
        f (function): The route handler function to be decorated.

    Returns:
        function: The decorated route handler function.
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        if not valid_user_session(session):
            session.pop("_permanent", None)

        # Note: This sets all requests to use the encryption key determined per
        # instance on app init. This can be updated in the future to use a key
        # that is unique for their session (session['key']) but this should use
        # a config setting to enable the session based key. Otherwise there can
        # be problems with searches performed by users with cookies blocked if
        # a session based key is always used.
        g.session_key = app.enc_key

        # Clear out old sessions
        invalid_sessions = []
        for user_session in os.listdir(app.config.get("SESSION_FILE_DIR")):
            file_path = os.path.join(
                app.config.get("SESSION_FILE_DIR"),
                user_session)

            try:
                # Ignore files that are larger than the max session file size
                if os.path.getsize(file_path) > app.config.get("MAX_SESSION_SIZE"):
                    continue

                with open(file_path, "rb") as session_file:
                    _ = pickle.load(session_file)
                    data = pickle.load(session_file)
                    if isinstance(data, dict) and "valid" in data:
                        continue
                    invalid_sessions.append(file_path)
            except Exception as e:
                # Broad exception handling here due to how instances installed
                # with pip seem to have issues storing unrelated files in the
                # same directory as sessions
                logging.debug(e)
                pass

        for invalid_session in invalid_sessions:
            try:
                os.remove(invalid_session)
            except FileNotFoundError:
                # Don"t throw error if the invalid session has been removed
                pass

        return f(*args, **kwargs)

    return decorated


@app.before_request
def before_request_func():
    """
    Callback function executed before processing each request.

    This Flask `before_request` function performs the following tasks before processing each incoming request:
    1. Sets the `session.permanent` attribute to True to make the session permanent.
    2. Checks for the latest version of the application and updates the `HAS_UPDATE` flag accordingly if needed.
    3. Sets the `g.request_params` attribute based on the request method (GET or POST).
    4. Loads the default configuration from the `DEFAULT_CONFIG` file and generates session values for the user if
       unavailable. It populates session values such as "config", "uuid", "key", and "auth".
    5. Establishes configuration values (`g.user_config`) for the user session based on the loaded session values.
    6. Updates the user config if specified in search arguments (`g.request_params`).
    7. Sets the `g.user_request` attribute based on the user agent and request URL. It also includes the user config.
    8. Sets the `g.app_location` attribute to the user config's URL.
    9. Attempts to reload the `bang_json` if it is not yet generated. The `bang_json` contains information about search
       bangs (e.g., "!g" for Google search).

    The function does not return anything since it is executed before each request to set up the necessary configuration
    for request processing.
    """
    global bang_json
    session.permanent = True

    # Check for latest version if needed
    now = datetime.now()
    if now - timedelta(hours=24) > app.config.get("LAST_UPDATE_CHECK"):
        app.config["LAST_UPDATE_CHECK"] = now
        app.config["HAS_UPDATE"] = check_for_update(
            app.config.get("RELEASES_URL"),
            app.config.get("VERSION_NUMBER"))

    g.request_params = (
        request.args if request.method == "GET" else request.form
    )

    default_config = json.load(open(app.config.get("DEFAULT_CONFIG"))) \
        if os.path.exists(app.config.get("DEFAULT_CONFIG")) else {}

    # Generate session values for user if unavailable
    if not valid_user_session(session):
        session["config"] = default_config
        session["uuid"] = str(uuid.uuid4())
        session['key'] = app.enc_key
        session['auth'] = False

    # Establish config values per user session
    g.user_config = Config(**session["config"])

    # Update user config if specified in search args
    g.user_config = g.user_config.from_params(g.request_params)

    if not g.user_config.url:
        g.user_config.url = get_request_url(request.url_root)

    g.user_request = Request(
        request.headers.get("User-Agent"),
        get_request_url(request.url_root),
        config=g.user_config)

    g.app_location = g.user_config.url

    # Attempt to reload bangs json if not generated yet
    if not bang_json and os.path.getsize(app.config.get("BANG_FILE")) > 4:
        try:
            bang_json = json.load(open(app.config.get("BANG_FILE")))
        except json.decoder.JSONDecodeError:
            # Ignore decoding error, can occur if file is still
            # being written
            pass


@app.after_request
def after_request_func(resp):
    """
    Callback function executed after processing each request.

    This Flask `after_request` function sets various security-related response headers for the HTTP response.

    The function sets the following headers:
    - "X-Content-Type-Options": Specifies that the browser should not automatically interpret files as a different MIME type
                                 (nosniff).
    - "X-Frame-Options": Specifies that the page should not be displayed in a frame or iframe (DENY).

    If the environment variable "WHOOGLE_CSP" is set to True (non-empty), the function also sets the "Content-Security-Policy"
    header. The value for this header is retrieved from the Flask application's configuration using "app.config.get("CSP")".
    Additionally, if the environment variable "HTTPS_ONLY" is set to True (non-empty), the function adds "upgrade-insecure-requests"
    to the "Content-Security-Policy" header.

    Parameters:
        resp (Response): The HTTP response object.

    Returns:
        Response: The modified HTTP response object with the security-related headers set.
    """
    resp.headers["X-Content-Type-Options"] = "nosniff"
    resp.headers["X-Frame-Options"] = "DENY"

    if os.getenv("WHOOGLE_CSP", False):
        resp.headers["Content-Security-Policy"] = app.config.get("CSP")
        if os.environ.get("HTTPS_ONLY", False):
            resp.headers["Content-Security-Policy"] += \
                "upgrade-insecure-requests"

    return resp


# @app.errorhandler(404)
# def unknown_page(e):
#     """
#     Error handler for 404 (Not Found) errors.
#
#     This Flask error handler is triggered when a request results in a 404 (Not Found) error, indicating that the requested
#     page or resource was not found.
#
#     The function logs the error message using 'app.logger.warn(e)' to provide information about the specific 404 error.
#
#     The function then redirects the user to the 'g.app_location', which appears to be the application location. This redirect
#     helps to handle the 404 error gracefully and may direct the user to a default or home page instead of displaying an
#     unfriendly error message.
#
#     Parameters:
#         e (Exception): The exception object representing the 404 error.
#
#     Returns:
#         Response: A redirect response to the 'g.app_location' to handle the 404 error gracefully.
#     """
#     app.logger.warn(e)
#     return redirect(g.app_location)


@app.route(f"/{Endpoint.healthz}", methods=["GET"])
def healthz():
    """
    Endpoint for health checks (healthz).

    This Flask route handles health checks at the "/healthz" endpoint. The route only supports the GET method.

    Returns:
        Response: An empty response. The response is used to indicate the health status of the application during health
                  checks.
    """
    return ""


@app.route("/", methods=["GET"])
@app.route(f"/{Endpoint.home}", methods=["GET"])
@auth_required
def index():
    """
    Renders the "index.html" template for the home page.

    This Flask route renders the "index.html" template at the root endpoint ("/") and the "/home" endpoint. The route only
    supports the GET method.

    If an error message is present in the session and the session["error_message"] is not empty, the function redirects to
    the "error.html" template to display the error message. The error message is then cleared from the session.

    The function passes various variables to the "index.html" template for rendering, including:

        - 'has_update': A boolean indicating whether an update is available.
        - 'languages': A list of supported languages.
        - 'countries': A list of supported countries.
        - 'time_periods': A dictionary containing supported time periods.
        - 'themes': A dictionary containing supported themes.
        - 'autocomplete_enabled': A boolean indicating whether autocomplete is enabled.
        - 'translation': A dictionary containing translation strings for the user's localization language.
        - 'logo': The rendered "logo.html" template with the 'dark' parameter based on the user's configuration.
        - 'config_disabled': A boolean indicating whether the user configuration is disabled.
        - 'config_save_allow': A boolean indicating whether saving configurations is allowed.
        - 'config': The user configuration object.
        - 'tor_available': An integer indicating whether Tor is available (0 for not available, 1 for available).
        - 'version_number': The version number of the application.

    Returns:
        Response: The rendered template "index.html" for the home page.
    """
    # Redirect if an error was raised
    if "error_message" in session and session["error_message"]:
        error_message = session["error_message"]
        session["error_message"] = ""
        return render_template("error.html", error_message=error_message)

    return render_template("index.html",
                           has_update=app.config.get("HAS_UPDATE"),
                           languages=app.config.get("LANGUAGES"),
                           countries=app.config.get("COUNTRIES"),
                           time_periods=app.config['TIME_PERIODS'],
                           themes=app.config.get("THEMES"),
                           autocomplete_enabled=autocomplete_enabled,
                           translation=app.config.get("TRANSLATIONS")[
                               g.user_config.get_localization_lang()
                           ],
                           logo=render_template(
                               "logo.html",
                               dark=g.user_config.dark),
                           config_disabled=(
                                   app.config.get("CONFIG_DISABLE") or
                                   not valid_user_session(session)),
                           config_save_allow=app.config.get("CONFIG_SAVE_ALLOW"),
                           config=g.user_config,
                           tor_available=int(os.environ.get("TOR_AVAILABLE")),
                           version_number=app.config.get("VERSION_NUMBER"))


@app.route(f"/{Endpoint.opensearch}", methods=["GET"])
def opensearch():
    """
    Renders the "opensearch.xml" template for OpenSearch support.

    This Flask route renders the "opensearch.xml" template at the "/opensearch" endpoint. The route only supports the GET
    method.

    The function retrieves the application location from 'g.app_location'. If the application location ends with a "/", it
    removes it to get the 'opensearch_url'. If the 'opensearch_url' needs HTTPS (as determined by 'needs_https()' function),
    it enforces HTTPS for the URL by replacing "http://" with "https://".

    The function checks if the user configuration has "get_only" enabled or if the User-Agent header contains "Chrome". If
    either of these conditions is met, it sets the 'get_only' variable to True.

    The function then passes the 'opensearch_url', 'get_only', 'request.args.get("tbm")', and the search name for the given
    search type to the "opensearch.xml" template for rendering.

    Returns:
        Response: The rendered template "opensearch.xml" with the appropriate HTTP status code (200) and the
                  "Content-Type" header set to "application/xml".
    """
    opensearch_url = g.app_location
    if opensearch_url.endswith("/"):
        opensearch_url = opensearch_url[:-1]

    # Enforce https for opensearch template
    if needs_https(opensearch_url):
        opensearch_url = opensearch_url.replace("http://", "https://", 1)

    get_only = g.user_config.get_only or "Chrome" in request.headers.get(
        "User-Agent")

    return render_template(
        "opensearch.xml",
        main_url=opensearch_url,
        request_type="" if get_only else "method=\"post\"",
        search_type=request.args.get("tbm"),
        search_name=get_search_name(request.args.get('tbm'))
    ), 200, {"Content-Type": "application/xml"}


@app.route(f"/{Endpoint.search_html}", methods=["GET"])
def search_html():
    """
    Renders the "search.html" template.

    This Flask route renders the "search.html" template at the "/search_html" endpoint. The route only supports the GET
    method.

    The function retrieves the application location from 'g.app_location'. If the application location ends with a "/", it
    removes it to get the 'search_url'. It then passes the 'search_url' variable to the "search.html" template to be used
    in the template.

    Returns:
        Response: The rendered template "search.html" with the 'search_url' variable available for use in the template.
    """
    search_url = g.app_location
    if search_url.endswith("/"):
        search_url = search_url[:-1]
    return render_template("search.html", url=search_url)


@app.route(f"/{Endpoint.autocomplete}", methods=["GET", "POST"])
def autocomplete():
    """
    Handles autocomplete functionality to provide search suggestions.

    This Flask route handles the autocomplete functionality at the "/autocomplete" endpoint. The route supports both GET
    and POST methods. It provides search suggestions based on the user's query (parameter "q").

    If the environment variable "ac_var" is set and its corresponding configuration is False, it returns an empty JSON
    response, effectively disabling autocomplete.

    If the "q" parameter is not provided as part of the request, the function tries to extract it from the "request.data"
    field (used by Firefox).

    If the query starts with "!" (exclamation mark) and is not a "feeling lucky" search (not starting with "! "), it
    returns a list of suggestions for the bang search.

    If the query is empty, it returns a JSON response with an empty list of suggestions.

    Otherwise, the function returns a list of suggestions based on the user's query using 'g.user_request.autocomplete()'
    method. If Tor is enabled (g.user_config.tor is True), the suggestions are not returned, as the request is almost
    always rejected in this case.

    Returns:
        Response: The JSON response containing a list of search suggestions for the user's query or an empty JSON
                  response (if autocomplete is disabled or Tor is enabled).
    """
    if os.getenv(ac_var) and not read_config_bool(ac_var):
        return jsonify({})

    q = g.request_params.get("q")
    if not q:
        # FF will occasionally (incorrectly) send the q field without a
        # mimetype in the format "b"q=<query>"" through the request.data field
        q = str(request.data).replace("q=", "")

    # Search bangs if the query begins with "!", but not "! " (feeling lucky)
    if q.startswith("!") and len(q) > 1 and not q.startswith("! "):
        return jsonify([q, [bang_json[_]["suggestion"] for _ in bang_json if
                            _.startswith(q)]])

    if not q and not request.data:
        return jsonify({"?": []})
    elif request.data:
        q = urlparse.unquote_plus(
            request.data.decode("utf-8").replace("q=", ""))

    # Return a list of suggestions for the query
    #
    # Note: If Tor is enabled, this returns nothing, as the request is
    # almost always rejected
    return jsonify([
        q,
        g.user_request.autocomplete(q) if not g.user_config.tor else []
    ])


@app.route(f"/{Endpoint.search}", methods=["GET", "POST"])
@session_required
@auth_required
def search():
    """
    Handles the search functionality and generates search results.

    This Flask route handles the search functionality at the "/search" endpoint. The route supports both GET and POST
    methods and is protected with two decorators '@session_required' and '@auth_required' to ensure the user has an active
    session and is authenticated.

    The function starts by creating a 'Search' object ('search_util') with the current request, user configuration
    ('g.user_config'), and session key ('g.session_key'). It then generates a new search query using 'search_util.new_search_query()'
    method.

    If the query contains a "bang" (e.g., "!g", "!yt", etc.), it resolves the "bang" using 'resolve_bang()' function and
    redirects the user to the corresponding search engine or website.

    If the query is blank or invalid, it redirects the user to the home page ("/").

    If the user is attempting to translate a string, it determines the correct URL for the lingva.ml translation service.

    It checks if the question has been moderated using 'Question().open_ai_moderation()' method. If the question has not
    been moderated, it generates the response using 'search_util.generate_response()' method. If Tor configuration is
    disabled, it logs an error and redirects the user to the home page.

    If the search_util indicates a "feeling lucky" search, it performs a 303 redirect to the generated response.

    The function processes the response by removing the "st-card" to use only the whoogle time selector. It checks for
    widgets (e.g., IP card, calculator) and adds them to the response if requested. It also updates the tabs content
    according to the search type, preferences, and translation.

    Additionally, it checks for a currency conversion card and adds it to the response if applicable.

    The final step is to render the 'display.html' template to display the search results, passing various variables to
    the template for rendering.

    Returns:
        Response: The response containing the search results to be rendered in the 'display.html' template.
    """
    search_util = Search(request, g.user_config, g.session_key)
    query = search_util.new_search_query()

    bang = resolve_bang(query, bang_json)
    if bang:
        return redirect(bang)

    # Redirect to home if invalid/blank search
    if not query:
        return redirect(url_for(".index"))

    # If the user is attempting to translate a string, determine the correct
    # string for formatting the lingva.ml url
    localization_lang = g.user_config.get_localization_lang()
    translation = app.config.get("TRANSLATIONS")[localization_lang]
    translate_to = localization_lang.replace("lang_", "")

    # Return 400 if question has not been moderated
    if Question(query).open_ai_moderation:
        app.logger.error('400 (MODERATION)')
        return render_template(
            "error.html",
            blocked=True,
            error_message=translation["moderated"],
            translation=translation,
            farside="https://farside.link",
            config=g.user_config,
            query=urlparse.unquote(query),
            params=g.user_config.to_params(keys=['preferences'])), 400

    # Generate response and number of external elements from the page
    try:
        response = search_util.generate_response()
    except TorError as e:
        session["error_message"] = e.message + (
            "\\n\\nTor config is now disabled!" if e.disable else "")
        session["config"]["tor"] = False if e.disable else session["config"][
            "tor"]
        return redirect(url_for(".index"))

    if search_util.feeling_lucky:
        return redirect(response, code=303)

    # removing st-card to only use whoogle time selector
    soup = bsoup(response, "html.parser")
    for x in soup.find_all(attrs={"id": "st-card"}):
        x.replace_with("")
    response = str(soup)

    # Return 503 if temporarily blocked by captcha
    if has_captcha(str(response)):
        app.logger.error('503 (CAPTCHA)')
        return render_template(
            "error.html",
            blocked=True,
            error_message=translation["ratelimit"],
            translation=translation,
            farside="https://farside.link",
            config=g.user_config,
            query=urlparse.unquote(query),
            params=g.user_config.to_params(keys=['preferences'])), 503

    response = bold_search_terms(response, query)

    # check for widgets and add if requested
    if search_util.widget != '':
        html_soup = bsoup(str(response), "html.parser")
        if search_util.widget == 'ip':
            response = add_ip_card(html_soup, get_client_ip(request))
        elif search_util.widget == 'calculator' and not ('nojs' in request.args):
            response = add_calculator_card(html_soup)

    # Update tabs content
    tabs = get_tabs_content(app.config.get("HEADER_TABS"),
                            search_util.full_query,
                            search_util.search_type,
                            g.user_config.preferences,
                            translation)

    # Feature to display currency_card
    # Since this is determined by more than just the
    # query is it not defined as a standard widget
    conversion = check_currency(str(response))
    if conversion:
        html_soup = bsoup(str(response), "html.parser")
        response = add_currency_card(html_soup, conversion)

    preferences = g.user_config.preferences
    home_url = f"home?preferences={preferences}" if preferences else "home"
    cleanresponse = str(response).replace("andlt;", "&lt;").replace("andgt;", "&gt;")

    return render_template(
        "display.html",
        has_update=app.config.get("HAS_UPDATE"),
        has_captcha=has_captcha(str(response)),
        query=urlparse.unquote(query),
        search_type=search_util.search_type,
        search_name=get_search_name(search_util.search_type),
        config=g.user_config,
        autocomplete_enabled=autocomplete_enabled,
        lingva_url=app.config.get("TRANSLATE_URL"),
        translation=translation,
        translate_to=translate_to,
        translate_str=query.replace(
            "translate", ""
        ).replace(
            translation["translate"], ""
        ),
        is_translation=any(
            _ in query.lower() for _ in [translation["translate"], "translate"]
        ) and not search_util.search_type,  # Standard search queries only
        response=cleanresponse,
        version_number=app.config.get("VERSION_NUMBER"),
        search_header=render_template(
            "header.html",
            home_url=home_url,
            config=g.user_config,
            translation=translation,
            languages=app.config.get("LANGUAGES"),
            countries=app.config.get("COUNTRIES"),
            time_periods=app.config['TIME_PERIODS'],
            logo=render_template("logo.html", dark=g.user_config.dark),
            query=urlparse.unquote(query),
            search_type=search_util.search_type,
            mobile=g.user_request.mobile,
            tabs=tabs)).replace("  ", "")


@app.route(f"/{Endpoint.config}", methods=["GET", "POST", "PUT"])
@session_required
@auth_required
def config():
    """
    Handles configuration related operations.

    This Flask route handles configuration related operations at the "/config" endpoint. It supports three HTTP methods:
    GET, POST, and PUT. The route is protected with two decorators '@session_required' and '@auth_required' to ensure
    the user has an active session and is authenticated.

    - GET: If a GET request is received, the function returns the user's configuration data in JSON format as a response.

    - PUT: If a PUT request is received and configuration saving is allowed ('CONFIG_SAVE_ALLOW' flag in app.config), the
      function updates the user's configuration with the data provided in the request form. If a "name" query parameter is
      provided, it saves the configuration with the specified name to allow the user to easily load it later. If "name" is
      not provided, it returns a JSON response indicating an error (status code 503) since a configuration name is required
      for saving.

    - POST: If a POST request is received and configuration is not disabled ('CONFIG_DISABLE' flag in app.config), the
      function updates the user's configuration with the data provided in the request form. It also saves the configuration
      by name (if "name" query parameter is provided and saving is allowed). Finally, it redirects the user to the updated
      configuration URL ('url' field in the configuration data).

    Returns:
        Response: The response with configuration data in JSON format (for GET request), an error JSON response (for PUT
                  request without a "name" query parameter), or a redirection response (for successful POST and PUT
                  requests).
    """
    config_disabled = (
            app.config.get("CONFIG_DISABLE") or
            not valid_user_session(session))
    saving_allow = app.config.get("CONFIG_SAVE_ALLOW")
    if request.method == "GET":
        return jsonify(g.user_config.__dict__)
    elif request.method == "PUT" and saving_allow:
        if "name" in request.args:
            config_pkl = os.path.join(
                app.config.get("CONFIG_PATH"),
                request.args.get("name"))
            session["config"] = (pickle.load(open(config_pkl, "rb"))
                                 if os.path.exists(config_pkl)
                                 else session["config"])
            return jsonify(session["config"])
        else:
            return jsonify({"error": True}), 503
    elif not config_disabled:
        config_data = request.form.to_dict()
        if "url" not in config_data or not config_data["url"]:
            config_data["url"] = g.user_config.url

        # Save config by name to allow a user to easily load later
        if "name" in request.args and saving_allow:
            pickle.dump(
                config_data,
                open(os.path.join(
                    app.config.get("CONFIG_PATH"),
                    request.args.get("name")), "wb"))

        session["config"] = config_data
        return redirect(config_data["url"])
    else:
        return redirect(url_for(".index"), code=403)


@app.route(f"/{Endpoint.imgres}")
@session_required
@auth_required
def imgres():
    """
    Redirect to the image URL specified in the 'imgurl' query parameter.

    This route is accessible only to authenticated users and requires a valid user session. It is intended to handle image
    search results. When a user clicks on an image search result, the URL of the image is passed as a query parameter
    'imgurl' to this route, and this route then redirects the user to the actual image URL.

    Returns:
        werkzeug.wrappers.response.Response: A redirection response that takes the user to the image URL.
    """
    return redirect(request.args.get("imgurl"))


@app.route(f"/{Endpoint.element}")
@session_required
@auth_required
def element():
    """
    Fetches an element from the provided URL and returns it as a response.

    This function handles an endpoint to fetch an element (e.g., an image, video, etc.) from the given URL. The URL is
    obtained from the "url" query parameter. If the URL starts with "gAAAAA", it is assumed to be encrypted, and it is
    decrypted using the session key ("g.session_key") as a Fernet cipher suite.

    The element type is obtained from the "type" query parameter. The function sends a request to the URL using the
    "g.user_request" object, and if successful, the fetched element is returned as a response with the corresponding
    mimetype. In case of a failed request, an empty gif image is returned as a response.

    Returns:
        Response: The fetched element as a response with the corresponding mimetype or an empty gif image response.
    """
    element_url = src_url = request.args.get("url")
    if element_url.startswith("gAAAAA"):
        try:
            cipher_suite = Fernet(g.session_key)
            src_url = cipher_suite.decrypt(element_url.encode()).decode()
        except (InvalidSignature, InvalidToken) as e:
            return render_template(
                "error.html",
                error_message=str(e)), 401

    src_type = request.args.get("type")

    try:
        file_data = g.user_request.send(base_url=src_url).content
        tmp_mem = io.BytesIO()
        tmp_mem.write(file_data)
        tmp_mem.seek(0)

        return send_file(tmp_mem, mimetype=src_type)
    except exceptions.RequestException:
        pass

    empty_gif = base64.b64decode(
        "R0lGODlhAQABAIAAAP///////yH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==")
    return send_file(io.BytesIO(empty_gif), mimetype="image/gif")


@app.route(f"/{Endpoint.window}")
@session_required
@auth_required
def window():
    """
    Open a new window and display the content of the specified URL.

    This route is accessible only to authenticated users and requires a valid user session. It takes a query parameter
    'location', which contains the URL of the content to be displayed. If the URL starts with 'gAAAAA', it is decrypted
    using the session key. The HTML content of the specified URL is fetched, and relative links are replaced with absolute
    links based on the host URL. The JavaScript sources are either replaced or removed based on the 'nojs' query parameter.
    Similarly, image and stylesheet sources are replaced with absolute URLs.

    Returns:
        werkzeug.wrappers.response.Response: A response containing the HTML content of the specified URL, with all
        relative links replaced by absolute links, and JavaScript, image, and stylesheet sources updated.
    """
    target_url = request.args.get("location")
    if target_url.startswith("gAAAAA"):
        cipher_suite = Fernet(g.session_key)
        target_url = cipher_suite.decrypt(target_url.encode()).decode()

    content_filter = Filter(
        g.session_key,
        root_url=request.url_root,
        config=g.user_config)
    target = urlparse.urlparse(target_url)
    host_url = f"{target.scheme}://{target.netloc}"

    get_body = g.user_request.send(base_url=target_url).text

    results = bsoup(get_body, "html.parser")
    src_attrs = ["src", "href", "srcset", "data-srcset", "data-src"]

    # Parse HTML response and replace relative links w/ absolute
    for element in results.find_all():
        for attr in src_attrs:
            if not element.has_attr(attr) or not element[attr].startswith("/"):
                continue

            element[attr] = host_url + element[attr]

    # Replace or remove javascript sources
    for script in results.find_all("script", {"src": True}):
        if "nojs" in request.args:
            script.decompose()
        else:
            content_filter.update_element_src(script, "application/javascript")

    # Replace all possible image attributes
    img_sources = ["src", "data-src", "data-srcset", "srcset"]
    for img in results.find_all("img"):
        _ = [
            content_filter.update_element_src(img, "image/png", attr=_)
            for _ in img_sources if img.has_attr(_)
        ]

    # Replace all stylesheet sources
    for link in results.find_all("link", {"href": True}):
        content_filter.update_element_src(link, "text/css", attr="href")

    # Use anonymous view for all links on page
    for a in results.find_all("a", {"href": True}):
        a["href"] = f"{Endpoint.window}?location=" + a["href"] + (
            "&nojs=1" if "nojs" in request.args else "")

    # Remove all iframes -- these are commonly used inside of <noscript> tags
    # to enforce loading Google Analytics
    for iframe in results.find_all("iframe"):
        iframe.decompose()

    return render_template(
        "display.html",
        response=results,
        translation=app.config.get("TRANSLATIONS")[
            g.user_config.get_localization_lang()
        ]
    )


def __remove_source_map(body: bytes) -> bytes:
    """
    Remove the sourceMappingURL comment from the provided HTML content.

    This function takes the HTML content as bytes, decodes it to a string, and then replaces the sourceMappingURL comment
    with the word "map". The updated HTML content is then re-encoded to bytes and returned.

    Args:
        body (bytes): The HTML content as bytes.

    Returns:
        bytes: The HTML content with the sourceMappingURL comment removed.
    """
    try:
        return body.decode().replace("# sourceMappingURL=", " map ").encode()
    except Exception as e:
        logging.debug(e)
        return body


def proxy_pattern(resp: requests.Response, content: bytes = b"", only_resp: bool = True) -> Response:
    """
    Create a new Response object based on the provided requests.Response and content.

    This function takes the original response from a remote server represented by requests.Response, and customizes
    the response headers and content before returning the new Response object.

    Args:
        resp (requests.Response): The original response from the remote server.
        content (bytes, optional): Custom content to replace the original response content. Defaults to an empty byte string (b"").
        only_resp (bool, optional): If True, the function uses the response content from the provided requests.Response. If False, it uses the custom content. Defaults to True.

    Returns:
        Response: The new Response object with customized headers and content.
    """
    excluded_headers = ['content-encoding', 'content-length', 'transfer-encoding', 'connection']
    use_headers = ['cache-control', 'content-type', 'etag']
    headers = [
        (name, value) for (name, value) in resp.raw.headers.items()
        if name.lower() not in excluded_headers and name.lower() in use_headers
    ]
    content = resp.content if only_resp else content
    content = __remove_source_map(content)
    return Response(content, resp.status_code, headers)


@app.route(f"/{Endpoint.currency_history}", methods=["GET"])
def currency_history():
    """
    Handle the "/currency_history" endpoint to retrieve currency exchange rate history.

    Returns:
        Response: The response containing the currency exchange rate history data.
    Raises:
        abort(400): If any required query parameter is missing.
        abort(503): If the request to the currency API is not successful.
    """
    params = {
        "start_date": g.request_params.get('start_date'),
        "end_date": g.request_params.get('end_date'),
        "symbols": g.request_params.get('symbols'),
        "base": g.request_params.get('base')
    }
    for key in params.items():
        if not key[1]:
            return abort(400)

    resp = http_get("https://api.exchangerate.host/timeseries", params=params)
    json_body = resp.json()
    if not json_body["success"]:
        return abort(503)
    del json_body["motd"]
    return proxy_pattern(resp, str.encode(json.dumps(json_body)), only_resp=False)


@app.route(f"/{Endpoint.gfont}", methods=["GET"])
def g_font():
    """
    Handle the "/gfont" endpoint to proxy Google Fonts API requests and serve custom fonts.

    Returns:
        Response: The response containing the font data or CSS with modified URLs.
    Raises:
        abort(400): If the required parameters are missing in the request query.
    """
    replace_urls = lambda body: str.encode(body.replace(
        "https://fonts.gstatic.com/s/",
        f"{request.base_url}?font_data="
    ))
    if g.request_params.get("css_get"):
        params = {
            "family": g.request_params.get("family"), "display": g.request_params.get("display")
        }
        if not params["family"] or not params["display"]:
            return abort(400)
        resp = http_get("https://fonts.googleapis.com/css2", params=params)
        content = replace_urls(resp.text) if resp.status_code == 200 else None
    else:
        font_data = g.request_params.get('font_data')
        if not font_data:
            return abort(400)
        resp = http_get(f"https://fonts.gstatic.com/s/{font_data}")
        content = resp.content

    return proxy_pattern(resp, content, only_resp=False)


@app.route(f"/{Endpoint.cdnjs}", methods=["GET"])
def cdnjs_proxy():
    """
    Handle the "/cdnjs" endpoint to proxy requests to the cdnjs.cloudflare.com API and serve requested libraries.

    Returns:
        Response: The response containing the requested library data.
    Raises:
        abort(400): If the "lib_path" parameter is missing in the request query.
    """
    lib_path = g.request_params.get('lib_path')
    if not lib_path:
        return abort(400)

    return proxy_pattern(http_get(f"https://cdnjs.cloudflare.com/{lib_path}"))


@app.route(f'/robots.txt')
def robots():
    """
    Serve the robots.txt file to inform web crawlers about access permissions.

    Returns:
        Response: The response containing the content of the robots.txt file.
    """
    response = make_response(
        "User-Agent: * \nDisallow: /", 200)
    response.mimetype = 'text/plain'
    return response


@app.errorhandler(404)
def page_not_found(e):
    """
    Handle the 404 Not Found error and display a custom error page.

    Args:
        e (Exception): The exception object representing the 404 Not Found error.

    Returns:
        Response: The response containing the custom error page with the error message.
    """
    return render_template('error.html', error_message=str(e)), 404


def run_app() -> None:
    parser = argparse.ArgumentParser(
        description="Whoogle Search console runner")
    parser.add_argument(
        "--port",
        default=5000,
        metavar="<port number>",
        help="Specifies a port to run on (default 5000)")
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        metavar="<ip address>",
        help="Specifies the host address to use (default 127.0.0.1)")
    parser.add_argument(
        "--unix-socket",
        default="",
        metavar="</path/to/unix.sock>",
        help="Listen for app on unix socket instead of host:port")
    parser.add_argument(
        "--debug",
        default=False,
        action="store_true",
        help="Activates debug mode for the server (default False)")
    parser.add_argument(
        "--https-only",
        default=False,
        action="store_true",
        help="Enforces HTTPS redirects for all requests")
    parser.add_argument(
        "--userpass",
        default="",
        metavar="<username:password>",
        help="Sets a username/password basic auth combo (default None)")
    parser.add_argument(
        "--proxyauth",
        default="",
        metavar="<username:password>",
        help="Sets a username/password for a HTTP/SOCKS proxy (default None)")
    parser.add_argument(
        "--proxytype",
        default="",
        metavar="<socks4|socks5|http>",
        help="Sets a proxy type for all connections (default None)")
    parser.add_argument(
        "--proxyloc",
        default="",
        metavar="<location:port>",
        help="Sets a proxy location for all connections (default None)")
    args = parser.parse_args()

    if args.userpass:
        user_pass = args.userpass.split(":")
        os.environ["WHOOGLE_USER"] = user_pass[0]
        os.environ["WHOOGLE_PASS"] = user_pass[1]

    if args.proxytype and args.proxyloc:
        if args.proxyauth:
            proxy_user_pass = args.proxyauth.split(":")
            os.environ["WHOOGLE_PROXY_USER"] = proxy_user_pass[0]
            os.environ["WHOOGLE_PROXY_PASS"] = proxy_user_pass[1]
        os.environ["WHOOGLE_PROXY_TYPE"] = args.proxytype
        os.environ["WHOOGLE_PROXY_LOC"] = args.proxyloc

    if args.https_only:
        os.environ["HTTPS_ONLY"] = "1"

    threads = multiprocessing.cpu_count() * 2 + 1
    logging.info(f"Threads count: {threads}")

    if args.debug:
        app.run(host=args.host, port=args.port, debug=args.debug)
    elif args.unix_socket:
        waitress.serve(app, unix_socket=args.unix_socket, threads=threads)
    else:
        waitress.serve(
            app, threads=threads,
            listen="{}:{}".format(args.host, args.port),
            url_prefix=os.environ.get("WHOOGLE_URL_PREFIX", ""))
