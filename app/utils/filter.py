import os

from requests import request
import logging
import json


class Question:

    def __init__(self) -> None:
        self.open_ai_token: str = os.getenv("WHOOGLE_OPEN_AI_TOKEN")

    def open_ai_moderation(self, input_text: str) -> bool:
        """
        Checks if the input text is flagged as potentially violating OpenAI's moderation policy.

        Args:
            input_text (str): The text to be checked for moderation.

        Returns:
            bool: True if the input text is flagged, False otherwise.
        """
        if not self.open_ai_token:
            return False

        response = request(
            "POST", "https://api.openai.com/v1/moderations",
            headers={
                "Authorization": "Bearer %s" % self.open_ai_token
            },
            data=json.dumps({
                "input": input_text
            })
        )
        if response.status_code != 200:
            logging.warning("OpenAI moderation error. Status code is %d" % response.status_code)
            return False

        try:
            return response.json()["results"][0]["flagged"]
        except Exception as e:
            logging.warning("Error parsing response OpenAI API (moderation). Exception: %s" % e)
            return False
