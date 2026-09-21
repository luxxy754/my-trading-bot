import time
import os
from binance.client import Client
from binance.exceptions import BinanceAPIException

# API Keys aur Proxy details GitHub Secrets (Environment Variables) se read hongi
BINANCE_API_KEY = os.environ.get("BINANCE_API_KEY")
BINANCE_SECRET_KEY = os.environ.get("BINANCE_SECRET_KEY")
PROXY_URL = os.environ.get("PROXY_URL")

# Configurations
TRADE_AMOUNT_USDT = 5.0  # Har trade ki investment (USDT)
LEVERAGE = 10
TARGET_PROFIT_PCT = 0.50  # 50% Profit target (leveraged)
CHECK_INTERVAL_SECONDS = 10

COINS_TO_SCAN = [
    "BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT",
    "ADAUSDT", "DOGEUSDT", "BNBUSDT", "AVAXUSDT"
]

previous_prices = {}
price_history = {symbol: [] for symbol in COINS_TO_SCAN}
last_trade_time = {symbol: 0 for symbol in COINS_TO_SCAN}
COOLDOWN_PERIOD = 300  # 5 minute cooldown per coin


def setup_futures_account(client, symbol):
    """Leverage aur margin type setup karna."""
    try:
        client.futures_change_leverage(symbol=symbol, leverage=LEVERAGE)
    except BinanceAPIException as e:
        # Log karo, lekin stop mat karo
        print(f"[{symbol}] Leverage set warning: {e}")

    try:
        client.futures_change_margin_type(symbol=symbol, marginType='ISOLATED')
    except BinanceAPIException as e:
        # BUG FIX #4: sirf error -4046 ignore karo ("No need to change margin type")
        # Baaki sab errors print karo taake silent fail na ho
        if e.code != -4046:
            print(f"[{symbol}] Margin type warning: {e}")


def calculate_targets(entry_price, side):
    if side == "BUY":
        take_profit = entry_price * (1 + (TARGET_PROFIT_PCT / LEVERAGE))
        stop_loss   = entry_price * (1 - (0.02 / LEVERAGE))
    else:
        take_profit = entry_price * (1 - (TARGET_PROFIT_PCT / LEVERAGE))
        stop_loss   = entry_price * (1 + (0.02 / LEVERAGE))
    return round(take_profit, 4), round(stop_loss, 4)


def execute_real_trade(client, symbol, side, current_price):
    try:
        setup_futures_account(client, symbol)

        # Quantity calculate karna ($5 ki value ke mutabiq)
        quantity = round((TRADE_AMOUNT_USDT * LEVERAGE) / current_price, 3)

        if quantity <= 0:
            print(f"[{symbol}] Quantity bohat choti hai!")
            return False

        print(f"\n[LIVE ORDER] {symbol} par {side} order lag raha hai...")

        # 1. Main Market Order
        order = client.futures_create_order(
            symbol=symbol,
            side=Client.SIDE_BUY if side == "BUY" else Client.SIDE_SELL,
            type=Client.FUTURE_ORDER_TYPE_MARKET,   # BUG FIX #3: futures constant use karo
            quantity=quantity
        )
        print(f"Order Successful! Order ID: {order['orderId']}")

        tp, sl = calculate_targets(current_price, side)

        # BUG FIX #1 (Dead code removed): 'exit_side' variable hatao —
        #   woh kabhi use nahi hua tha aur dono branches SIDE_SELL return karti thi (typo)
        # Long (BUY) ke liye exit = SELL, Short (SELL) ke liye exit = BUY
        close_side = Client.SIDE_SELL if side == "BUY" else Client.SIDE_BUY

        # 2. Stop-Loss Order
        client.futures_create_order(
            symbol=symbol,
            side=close_side,
            type=Client.FUTURE_ORDER_TYPE_STOP_MARKET,   # BUG FIX #3: FUTURE_ prefix
            stopPrice=str(sl),
            closePosition=True,
            workingType='MARK_PRICE'   # BUG FIX #3b: wick se early trigger se bachao
        )
        print(f"Server-Side Stop-Loss set at: {sl}")

        # 3. BUG FIX #2 (Critical): Take-Profit Order — yeh pehle bilkul missing tha!
        #    tp calculate hota tha lekin koi order place nahi hota tha.
        client.futures_create_order(
            symbol=symbol,
            side=close_side,
            type=Client.FUTURE_ORDER_TYPE_TAKE_PROFIT_MARKET,
            stopPrice=str(tp),
            closePosition=True,
            workingType='MARK_PRICE'
        )
        print(f"Server-Side Take-Profit set at: {tp}")

        return True

    except BinanceAPIException as e:
        print(f"Binance API Error during trade execution: {e}")
        return False
    except Exception as e:
        print(f"General Trade Error: {e}")
        return False


def run_bot():
    try:
        requests_params = {}
        if PROXY_URL:
            requests_params = {
                'http': PROXY_URL,
                'https': PROXY_URL
            }

        client = Client(
            BINANCE_API_KEY,
            BINANCE_SECRET_KEY,
            requests_params=requests_params if requests_params else None
        )

        print("Success: Connected to Binance Futures Live Trading Mode!")
        print(f"Bot ab live market scan aur trading karega ({len(COINS_TO_SCAN)} coins)...\n")

        while True:
            trade_taken = False
            current_time = time.time()

            for symbol in COINS_TO_SCAN:
                try:
                    # BUG FIX #0 (Critical): Spot ticker ki jagah Futures ticker use karo!
                    # get_symbol_ticker() → SPOT price deta hai
                    # futures_symbol_ticker() → actual Futures market price
                    ticker = client.futures_symbol_ticker(symbol=symbol)
                    current_price = float(ticker['price'])
                except Exception as e:
                    print(f"[{symbol}] Price fetch error: {e}")
                    continue

                price_history[symbol].append(current_price)
                if len(price_history[symbol]) > 5:
                    price_history[symbol].pop(0)

                if symbol not in previous_prices:
                    previous_prices[symbol] = current_price
                    continue

                old_price = previous_prices[symbol]
                price_change_pct = ((current_price - old_price) / old_price) * 100

                if current_time - last_trade_time[symbol] < COOLDOWN_PERIOD:
                    previous_prices[symbol] = current_price
                    continue

                avg_price = sum(price_history[symbol]) / len(price_history[symbol])

                print(f"[{time.strftime('%H:%M:%S')}] {symbol} | Price: {current_price} | Change: {price_change_pct:+.3f}%")

                side = None
                if price_change_pct >= 0.10 and current_price >= avg_price:
                    side = "BUY"
                elif price_change_pct <= -0.10 and current_price <= avg_price:
                    side = "SELL"

                if side:
                    print(f"\n>>> SIGNAL MATCHED! {symbol} par {side} ki trade execute ho rahi hai...")
                    success = execute_real_trade(client, symbol, side, current_price)

                    if success:
                        last_trade_time[symbol] = current_time
                        trade_taken = True
                        previous_prices[symbol] = current_price
                        break

                previous_prices[symbol] = current_price
                time.sleep(0.5)

            time.sleep(CHECK_INTERVAL_SECONDS)

    except KeyboardInterrupt:
        print("\nBot ko rok diya gaya hai.")
    except Exception as e:
        print(f"Main Loop Error: {e}")


if __name__ == "__main__":
    run_bot()
