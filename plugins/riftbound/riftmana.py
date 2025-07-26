from re import compile, sub
from api import request_api

def fetch_card_number(name: str) -> str:
    
    # Get the internal information based on the card name to route to the card itself
    url = f'https://riftmana.com/wp-json/wp/v2/card-name?search={sub(r'\s+', '-', sub(r'[^A-Za-z0-9 ]+', '', name)).lower()}'
    success, name_response = request_api(url)
    if not success:
        raise ValueError(f'Issue retrieving card information for {name}')
    card_link = name_response.json()[0].get('_links', {}).get('wp:post_type')[0].get('href')

    # Now we can retrieve the card number
    success, card_response = request_api(card_link)
    if not success:
        raise ValueError(f'Issue retrieving card information for {name}')
    card_number_and_name = card_response.json()[0].get('title').get('rendered')

    pattern = compile(r'^([A-Z0-9]+-\d+[a-z]?)(\s+|-)(.*)$') # '{Card Number} {Card Name}'
    match = pattern.match(card_number_and_name)

    if match:
        return match.group(1).strip()