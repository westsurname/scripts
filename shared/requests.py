import time
import requests
from typing import Callable, Optional
from shared.discord import discordError, discordUpdate


def retryRequest(
    requestFunc: Callable[[], requests.Response], 
    print: Callable[..., None] = print, 
    retries: int = 1, 
    delay: int = 1
) -> Optional[requests.Response]:
    """
    Retry a request if the response status code is not in the 200 range.

    :param requestFunc: A callable that returns an HTTP response.
    :param print: Optional print function for logging.
    :param retries: The number of times to retry the request after the initial attempt.
    :param delay: The delay between retries in seconds.
    :return: The response object or None if all attempts fail.
    """
    attempts = retries + 1  # Total attempts including the initial one
    for attempt in range(attempts):
        try:
            response = requestFunc()
            if 200 <= response.status_code < 300:
                return response
            else:
                message = [
                    f"URL: {response.url}",
                    f"Status code: {response.status_code}",
                    f"Message: {response.reason}",
                    f"Response: {response.content}",
                    f"Attempt {attempt + 1} failed"
                ]
                for line in message:
                    print(line)
                if attempt == retries:
                    discordError("Request Failed", "\n".join(message))
                else:
                    update_message = message + [f"Retrying in {delay} seconds..."]
                    discordUpdate("Retrying Request", "\n".join(update_message))
                    print(f"Retrying in {delay} seconds...")
                    time.sleep(delay)
        except requests.RequestException as e:
            message = [
                f"URL: {response.url if 'response' in locals() else 'unknown'}",
                f"Attempt {attempt + 1} encountered an error: {e}"
            ]
            for line in message:
                print(line)
            if attempt == retries:
                discordError("Request Exception", "\n".join(message))
            else:
                update_message = message + [f"Retrying in {delay} seconds..."]
                discordUpdate("Retrying Request", "\n".join(update_message))
                print(f"Retrying in {delay} seconds...")
                time.sleep(delay)
    
    return None