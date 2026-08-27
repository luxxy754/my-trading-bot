import os
import pandas as pd
from binance.client import Client

API_KEY = os.getenv('BINANCE_API_KEY')
API_SECRET = os.getenv('BINANCE_SECRET_KEY')

client = Client(API_KEY, API_SECRET)

SYMBOL = 'BTCUSDT'
QUANTITY = 0.001  # Trade size

def get_rsi(symbol, interval='1m', lookback='100m'):
    # Market data fetch karna
    klines = client.get_historical_klines(symbol, interval, lookback)
    df = pd.DataFrame(klines)
    close = df[4].astype(float)
    
    # RSI Calculation (14 period)
    delta = close.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi.iloc[-1]

def execute_trade():
    try:
        rsi = get_rsi(SYMBOL)
        print(f"Current RSI for {SYMBOL}: {rsi:.2f}")

        # Buy Logic: Oversold condition (RSI < 30)
        if rsi < 30:
            print("RSI Low! Executing Buy Order...")
            order = client.order_market_buy(symbol=SYMBOL, quantity=QUANTITY)
            print(f"Buy Successful: {order['orderId']}")

        # Sell Logic: Overbought condition (RSI > 70)
        elif rsi > 70:
            print("RSI High! Executing Sell Order...")
            order = client.order_market_sell(symbol=SYMBOL, quantity=QUANTITY)
            print(f"Sell Successful: {order['orderId']}")

        else:
            print("RSI normal zone mein hai. Koi trade nahi lagai gayi.")

    except Exception as e:
        print(f"Trading Error: {e}")

if __name__ == "__main__":
    execute_trade()
