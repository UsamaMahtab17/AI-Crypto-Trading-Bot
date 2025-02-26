import websocket
import json
from datetime import datetime
import pandas as pd
from utils.kraken import KrakenAPI
import websockets
import logging
import asyncio
from socket_manager import ws_manager
from utils.macd import calculate_macd, identify_signals
from utils.RSI import calculate_rsi, identify_rsi_signals
from utils.ema import identify_ema_signals
from utils.bollinger_bands import calculate_bollinger_bands, identify_bollinger_signals
from asyncio import Lock
import aiohttp
import pymongo
from pymongo import MongoClient
from datetime import datetime


data_lock = Lock()
# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s: %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# MongoDB connection string and client initialization
mongo_client = MongoClient("mongodb+srv://octalooptech:kPi2iaTtqEebfY3k@crypto-trading-bot.g62cx.mongodb.net/?retryWrites=true&w=majority&appName=crypto-trading-bot")
db = mongo_client['test']  # Specify the database name
trades_collection = db['trades']  # Specify the collection name


# Async WebSocket Handler for Public Market Data using Kraken API
async def fetch_kraken_data(pair, callback):
    ws_url = "wss://ws.kraken.com"
    try:
        async with websockets.connect(ws_url) as websocket:
            logger.info(f"Connected to Kraken WebSocket for pair {pair}")
            message = {
                "event": "subscribe",
                "pair": [pair],
                "subscription": {"name": "trade"}
            }
            await websocket.send(json.dumps(message))
            logger.info(f"Subscribed to trade feed for {pair}")

            while True:
                try:
                    response = await websocket.recv()
                    response = json.loads(response)
                    if isinstance(response, list):
                        logger.info(f"Received data for {pair}: {response[1][0][0]}")
                        await callback(response)
                except Exception as e:
                    logger.error(f"Error processing WebSocket data for {pair}: {e}")
    except Exception as e:
        logger.error(f"WebSocket connection failed for {pair}: {e}")


# Function to save trade data to MongoDB
async def save_trade_to_db(trade_data):
    try:
        # Add timestamp to the trade data
        trade_data["timestamp"] = datetime.now()

        # Insert the trade data into MongoDB
        trades_collection.insert_one(trade_data)
        logger.info(f"Trade data saved to MongoDB: {trade_data}")
    except Exception as e:
        logger.error(f"Failed to save trade data to MongoDB: {e}")

# Updated execute_strategy
async def execute_strategy(pair, strategy, strategy_id, stop_loss=None, take_profit=None, **kwargs):
    prices = pd.DataFrame(columns=["Time", "Close"])
    kraken = KrakenAPI()  # Initialize authenticated Kraken API client

    logger.info(f"Started strategy execution for pair {pair} using {strategy}")

    # Determine the minimum required data length dynamically
    def get_required_data_length():
        if strategy == "MACD":
            short_window = kwargs.get('short_window', 12)
            long_window = kwargs.get('long_window', 26)
            return max(short_window, long_window) + kwargs.get('signal_window', 9)
        elif strategy == "RSI":
            return kwargs.get('period', 14)
        elif strategy == "EMA":
            short_period = kwargs.get('short_period', 12)
            long_period = kwargs.get('long_period', 26)
            return max(short_period, long_period)
        elif strategy == "Bollinger Bands":
            return kwargs.get('window', 20)
        else:
            return 30  # Default fallback for any future strategies

    required_data_length = get_required_data_length()

    async def process_data(data):
        nonlocal prices
        try:
            async with data_lock:  # Ensure thread safety
                close_price = float(data[1][0][0])
                time = datetime.now()
                logger.info(f"Received data for {pair}: {close_price}")
                # Append to DataFrame
                prices = pd.concat([prices, pd.DataFrame({"Time": [time], "Close": [close_price]})])
                prices = prices.tail(100)  # Limit data for performance
                # logger.info(prices.tail(5))
                        # Ensure sufficient data length for the selected strategy
                if len(prices) < required_data_length:
                    return

                if strategy == "MACD": # Ensure enough data for MACD
                    short_window = kwargs.get('short_window', 12)
                    long_window = kwargs.get('long_window', 26)
                    signal_window = kwargs.get('signal_window', 9)
                    logger.info(f"Calculating MACD for {pair} with short={short_window}, long={long_window}, signal={signal_window}")

                    prices = calculate_macd(prices, short_window, long_window, signal_window)
                    prices = identify_signals(prices)
                    last_row = prices.iloc[-1]
                    signal_crossover = last_row['Signal_Crossover']
                    divergence = last_row['Divergence']
                    zero_line_crossing = last_row['Zero_Line_Crossing']
                    histogram_trend = last_row['Histogram_Trend']
                    
                    logger.info(f"MACD Signal: {signal_crossover}, Divergence: {divergence}, Zero Line Crossing: {zero_line_crossing}, Histogram Trend: {histogram_trend}")
                    # Fetch the latest and previous MACD/Signal values
                    last_macd = prices['MACD'].iloc[-1]
                    last_signal = prices['Signal'].iloc[-1]
                    prev_macd = prices['MACD'].iloc[-2]
                    prev_signal = prices['Signal'].iloc[-2]

                    logger.info(f"[{datetime.now()}] MACD: {last_macd}, Signal: {last_signal}")
                    logger.info(f"[{datetime.now()}] Previous MACD: {prev_macd}, Previous Signal: {prev_signal}")

                    # Prepare data for WebSocket
                    info_data = {
                        "strategy_id": strategy_id,
                        "info_status": "Information",
                        "pair": pair,
                        "close_price": close_price,
                        "strategy": strategy,
                    }
                    await ws_manager.send_message(strategy_id=strategy_id, message=str(info_data))

                    # Generate buy/sell signals
                    if signal_crossover == 1:  # Bullish crossover
                        logger.info(f"Buy Signal for {pair} at {close_price}")
                        # kraken.place_order(pair=pair.replace('/', ''), ordertype='buy', volume=0.01)
                        trade_data = {
                            "strategy_id": strategy_id,
                            "pair": pair,
                            "trade_type": "buy",
                            "close_price": close_price,
                            "strategy": strategy
                        }
                        # Send the trade data via WebSocket
                        await ws_manager.send_message(strategy_id=strategy_id, message=str(trade_data))
                        # Save the trade data via the API
                        await save_trade_to_db(trade_data)
                    elif signal_crossover == -1:  # Bearish crossover
                        logger.info(f"Sell Signal for {pair} at {close_price}")
                        # kraken.place_order(pair=pair.replace('/', ''), ordertype='sell', volume=0.01)
                        trade_data = {
                            "strategy_id": strategy_id,
                            "pair": pair,
                            "trade_type": "sell",
                            "close_price": close_price,
                            "strategy": strategy
                        }
                        # Send the trade data via WebSocket
                        await ws_manager.send_message(strategy_id=strategy_id, message=str(trade_data))
                        # Save the trade data via the API
                        await save_trade_to_db(trade_data)
                
                    elif divergence == 'Bullish':
                        logger.info(f"Bullish Divergence detected for {pair}")
                    elif divergence == 'Bearish':
                        logger.info(f"Bearish Divergence detected for {pair}")
                    elif zero_line_crossing == 1:
                        logger.info(f"Bullish Momentum detected for {pair}")
                    elif zero_line_crossing == -1:
                        logger.info(f"Bearish Momentum detected for {pair}")

                elif strategy == "RSI":
                    period = kwargs.get('period', 14)
                    prices = calculate_rsi(prices, period)
                    logger.info(f"Calculating RSI for {pair} with period={period}")
                    
                    # Identify RSI signals for the latest row
                    prices = identify_rsi_signals(prices)
                    last_row = prices.iloc[-1]

                    rsi_signal = last_row['Signal_Type']
                    bullish_divergence = last_row['Bullish_Divergence']
                    bearish_divergence = last_row['Bearish_Divergence']

                    logger.info(f"RSI Signal: {rsi_signal}, Bullish Divergence: {bullish_divergence}, Bearish Divergence: {bearish_divergence}")

                    # Prepare data for WebSocket
                    info_data = {
                        "strategy_id": strategy_id,
                        "info_status": "Information",
                        "pair": pair,
                        "close_price": close_price,
                        "strategy": strategy,
                    }
                    await ws_manager.send_message(strategy_id=strategy_id, message=str(info_data))

                    # Generate buy/sell signals based on RSI
                    if rsi_signal == "Overbought":
                        logger.info(f"Overbought Signal for {pair}, consider Sell at {close_price}")
                        # kraken.place_order(pair=pair.replace('/', ''), ordertype='sell', volume=0.01)
                        trade_data = {
                        "strategy_id": strategy_id,
                        "pair": pair,
                        "trade_type": "sell",
                        "close_price": close_price,
                        "strategy": strategy
                    }
                        # Send the trade data via WebSocket
                        await ws_manager.send_message(strategy_id=strategy_id, message=str(trade_data))
                        # Save the trade data via the API
                        await save_trade_to_db(trade_data)
                    elif rsi_signal == "Oversold":
                        logger.info(f"Oversold Signal for {pair}, consider Buy at {close_price}")
                        # kraken.place_order(pair=pair.replace('/', ''), ordertype='buy', volume=0.01)
                        trade_data = {
                        "strategy_id": strategy_id,
                        "pair": pair,
                        "trade_type": "buy",
                        "close_price": close_price,
                        "strategy": strategy
                    }
                        # Send the trade data via WebSocket
                        await ws_manager.send_message(strategy_id=strategy_id, message=str(trade_data))
                        # Save the trade data via the API
                        await save_trade_to_db(trade_data)
                    elif bullish_divergence:
                        logger.info(f"Bullish Divergence detected for {pair}, potential Buy opportunity at {close_price}")
                    elif bearish_divergence:
                        logger.info(f"Bearish Divergence detected for {pair}, potential Sell opportunity at {close_price}")

                elif strategy == "EMA":
                    short_period = kwargs.get("short_period", 12)
                    long_period = kwargs.get("long_period", 26)

                    # Identify EMA signals only for the latest data
                    prices = identify_ema_signals(prices, short_period, long_period)
                    last_row = prices.iloc[-1]  # Get the latest row

                    # Extract the signal from the latest row
                    ema_signal = last_row["EMA_Signal"]
                    logger.info(f"EMA Signal for {pair}: {ema_signal}")

                    # Prepare data for WebSocket message
                    info_data = {
                        "strategy_id": strategy_id,
                        "info_status": "Information",
                        "pair": pair,
                        "close_price": close_price,
                        "strategy": strategy,
                    }
                    # Send the WebSocket message
                    await ws_manager.send_message(strategy_id, message=str(info_data))

                    # Generate buy/sell signals
                    if ema_signal == "Bullish Crossover":
                        logger.info(f"Buy Signal for {pair} at {last_row['Close']}")
                        # kraken.place_order(pair=pair.replace("/", ""), ordertype="buy", volume=0.01)
                        trade_data = {
                        "strategy_id": strategy_id,
                        "pair": pair,
                        "trade_type": "buy",
                        "close_price": close_price,
                        "strategy": strategy
                    }
                        # Send the trade data via WebSocket
                        await ws_manager.send_message(strategy_id=strategy_id, message=str(trade_data))
                        # Save the trade data via the API
                        await save_trade_to_db(trade_data)
                    elif ema_signal == "Bearish Crossover":
                        logger.info(f"Sell Signal for {pair} at {last_row['Close']}")
                        # kraken.place_order(pair=pair.replace("/", ""), ordertype="sell", volume=0.01)
                        trade_data = {
                        "strategy_id": strategy_id,
                        "pair": pair,
                        "trade_type": "buy",
                        "close_price": close_price,
                        "strategy": strategy
                    }
                        # Send the trade data via WebSocket
                        await ws_manager.send_message(strategy_id=strategy_id, message=str(trade_data))
                        # Save the trade data via the API
                        await save_trade_to_db(trade_data)


                elif strategy == "Bollinger Bands":
                    window = kwargs.get('window', 20)
                    multiplier = kwargs.get('multiplier', 2)

                    prices = calculate_bollinger_bands(prices, window, multiplier)
                    prices = identify_bollinger_signals(prices)

                    # Send Bollinger Band signals
                    last_row = prices.iloc[-1]
                    signal_data = {
                        "pair": pair,
                        "close_price": close_price,
                        "bollinger_bounce_buy": last_row['Bollinger Bounce Buy'],
                        "bollinger_bounce_sell": last_row['Bollinger Bounce Sell'],
                    }
                    logger.info(f"Bollinger Signal: {signal_data}")
                    await ws_manager.send_message(strategy_id, message=str(signal_data))

        except Exception as e:
            logger.error(f"Error processing WebSocket data for {pair}: {e}")

    try:
        await fetch_kraken_data(pair, process_data)
    except asyncio.CancelledError:
        logger.info(f"Strategy execution for pair {pair} has been cancelled.")
        raise
    except Exception as e:
        logger.error(f"Error during strategy execution for pair {pair}: {e}")


# def macd_strategy(prices, short_window=12, long_window=26, signal_window=9):
#     prices['EMA_12'] = prices['Close'].ewm(span=short_window, adjust=False).mean()
#     prices['EMA_26'] = prices['Close'].ewm(span=long_window, adjust=False).mean()
#     prices['MACD'] = prices['EMA_12'] - prices['EMA_26']
#     prices['Signal'] = prices['MACD'].ewm(span=signal_window, adjust=False).mean()
#     return prices['MACD'], prices['Signal']


# # Async Strategy Execution
# async def execute_strategy(pair, strategy,strategy_id, stop_loss, take_profit):
#     prices = pd.DataFrame(columns=["Time", "Close"])
#     kraken = KrakenAPI()  # Initialize authenticated Kraken API client

#     logger.info(f"Started strategy execution for pair {pair} using {strategy}")

#     async def process_data(data):
#         nonlocal prices
#         close_price = float(data[1][0][0])
#         time = datetime.now()

#         # Append to DataFrame
#         prices = pd.concat([prices, pd.DataFrame({"Time": [time], "Close": [close_price]})])
#         prices = prices.tail(100)  # Limit data for performance

#         print(f"[{datetime.now()}] {pair} Close Price: {close_price}")
#         print(prices.tail(5))

#         if len(prices) > 26:  # Ensure enough data for MACD
#             macd, signal = macd_strategy(prices)
#             last_macd, last_signal = macd.iloc[-1], signal.iloc[-1]
#             prev_macd, prev_signal = macd.iloc[-2], signal.iloc[-2]
#             print(f"MACD: {last_macd}, Signal: {last_signal}")
#             print(f"Prev MACD: {prev_macd}, Prev Signal: {prev_signal}")
#             info_data={
#                 "strategy_id": strategy_id,
#                 "info_status": "Information",
#                 "trade_type": None,
#                 "Previous_macd":prev_macd,
#                 "Previous_signal":prev_signal,
#                 "pair":pair,
#                 "close_price":None

#             }
#             await ws_manager.send_message(strategy_id=strategy_id,message=str(info_data))
#             # Generate buy/sell signals
#             if last_macd > last_signal and prev_macd <= prev_signal:
#                 print(f"[{datetime.now()}] Buy Signal for {pair} at {close_price}")
#                 info_data={
#                 "strategy_id": strategy_id,
#                 "info_status": "information",
#                 "trade_type": "Buy",
#                 "previous_macd":None,
#                 "previous_signal":None,
#                 "pair":pair,
#                 "close_price":close_price

#             }
#                 await ws_manager.send_message(strategy_id=strategy_id,message=str(info_data))
#                 kraken.place_order(pair=pair.replace('/', ''), ordertype='buy', volume=0.01)
#             elif last_macd < last_signal and prev_macd >= prev_signal:
#                 print(f"[{datetime.now()}] Sell Signal for {pair} at {close_price}")
#                 info_data={
#                 "strategy_id": strategy_id,
#                 "info_status": "information",
#                 "trade_type": "Sell",
#                 "previous_macd":None,
#                 "previous_signal":None,
#                 "pair":pair,
#                 "close_price":close_price

#             }
#                 await ws_manager.send_message(strategy_id=strategy_id,message=str(info_data))
#                 kraken.place_order(pair=pair.replace('/', ''), ordertype='sell', volume=0.01)

#     try:
#         await fetch_kraken_data(pair, process_data)
#     except asyncio.CancelledError:
#         logger.info(f"Strategy execution for pair {pair} has been cancelled.")
#         raise
#     except Exception as e:
#         logger.error(f"Error during strategy execution for pair {pair}: {e}")
