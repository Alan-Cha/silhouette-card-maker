from requests import Response, get, HTTPError
from time import sleep
from typing import Tuple

response_tuple = Tuple[bool, Response]

def request_api(query: str) -> response_tuple:
    r = get(query, headers = {'user-agent': 'silhouette-card-maker/0.1', 'accept': '*/*'})

    try:
        r.raise_for_status()
        sleep(0.15)
    except HTTPError:
        return (False, r)

    return (True, r)