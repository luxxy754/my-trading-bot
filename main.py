import os
from binance.client import Client

# GitHub Secrets se API Keys fetch karein
API_KEY = os.getenv('BINANCE_API_KEY')
API_SECRET = os.getenv('BINANCE_SECRET_KEY')

def run_bot():
    if not API_KEY or not API_SECRET:
        print("Error: API Keys nahi mili! GitHub Secrets check karein.")
        return

    try:
        # Client Setup
        client = Client(API_KEY, API_SECRET)
        print("Binance se connection successful!")

        # BTC Market Price check karein
        ticker = client.get_symbol_ticker(symbol="BTCUSDT")
        print(f"Current BTC Price: ${ticker['price']}")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    run_bot()
