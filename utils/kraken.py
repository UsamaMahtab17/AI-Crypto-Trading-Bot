import os
import hmac
import hashlib
import base64
import urllib.parse
import requests
import time
from dotenv import load_dotenv
# Load environment variables (API key and secret)
load_dotenv()

class KrakenAPI:
    def __init__(self):
        self.key, self.secret = auth()
        self.rest_url = 'https://api.kraken.com'

    def _request(self, endpoint, data):
        """Make an authenticated API request to Kraken."""
        urlpath = f'/0/private/{endpoint}'
        data['nonce'] = int(time.time() * 1000)
        headers = {
            'API-Key': self.key,
            'API-Sign': create_kraken_signature(urlpath, data, self.secret),
        }
        response = requests.post(self.rest_url + urlpath, headers=headers, data=data)
        return response.json()

    def get_balance(self):
        """Fetch account balances."""
        return self._request('Balance', {})

    def place_order(self, pair, ordertype, volume, price=None):
        """Place a trade order (buy/sell)."""
        data = {
            'pair': pair,
            'type': ordertype,
            'ordertype': 'limit' if price else 'market',
            'volume': volume,
        }
        if price:
            data['price'] = price
        return self._request('AddOrder', data)

def auth():
    """Fetch API key and secret from environment variables."""
    key = os.getenv("KRAKEN_API_KEY")
    secret = os.getenv("KRAKEN_SECRET")
    return key, secret

def create_kraken_signature(urlpath, data, secret):
    """Create an HMAC-SHA512 signature for Kraken API authentication."""
    postdata = urllib.parse.urlencode(data)
    encoded = (str(data['nonce']) + postdata).encode()
    message = urlpath.encode() + hashlib.sha256(encoded).digest()
    mac = hmac.new(base64.b64decode(secret), message, hashlib.sha512)
    sigdigest = base64.b64encode(mac.digest())
    return sigdigest.decode()