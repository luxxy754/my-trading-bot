import os
import sys
from binance.client import Client
from binance.exceptions import BinanceAPIException

# GitHub Secrets ya Environment Variables se API Keys lena
API_KEY = os.getenv("BINANCE_API_KEY")
API_SECRET = os.getenv("BINANCE_SECRET_KEY")

if not API_KEY or not API_SECRET:
    print("Error: BINANCE_API_KEY or BINANCE_SECRET_KEY environment variables not set.")
    sys.exit(1)

# Binance Client initialize karna
client = Client(API_KEY, API_SECRET)

# Trading pair (Aap apni marzi ka pair rakh sakte hain, jese 'BTCUSDT' ya 'ETHUSDT')
SYMBOL = "BTCUSDT"

def execute_trade():
    try:
        print("Checking account balance...")
        # USDT ka balance check karna
        balance = client.get_asset_balance(asset="USDT")
        free_balance = float(balance['free'])
        print(f"Available USDT Balance: {free_balance}")

        # Minimum balance requirement (Binance ki taraf se min notional check)
        if free_balance < 10.0:
            print("Error: Balance is too low to place a trade (Minimum usually $10 required).")
            return

        # Double / All available amount use karne ke liye balance ka hisaab lagana
        # Agar aap chahte hain ke har run par saara available balance use ho:
        # Note: Binance par exact asset price ke mutabiq quantity nikalni parti hai.
        
        ticker = client.get_symbol_ticker(symbol=SYMBOL)
        current_price = float(ticker['price'])
        print(f"Current {SYMBOL} Price: {current_price}")

        # Total free balance se maximum possible quantity nikalna (Thora buffer rakh kar taake insufficient funds ka error na aaye)
        target_usdt = free_balance * 0.99  # 99% of free balance to account for fees
        raw_quantity = target_usdt / current_price

        # Binance ke rules ke mutabiq quantity ka decimal precision set karna (BTC ke liye aam taur par 5 decimals hote hain)
        # Behtar hai ke hum step size handle karein, yahan standard 5 decimal use kar rahe hain:
        quantity = round(raw_quantity, 5)

        print(f"Attempting to buy {quantity} {SYMBOL} using ~{target_usdt} USDT...")

        # Market Buy Order Place karna (Direct Trading)
        order = client.order_market_buy(
            symbol=SYMBOL,
            quantity=quantity
        )
        
        print("Trade executed successfully!")
        print(order)

    except BinanceAPIException as e:
        print(f"Binance API Error: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

if __name__ == "__main__":
    print("Starting Automated Trading Bot Script...")
    execute_trade()
