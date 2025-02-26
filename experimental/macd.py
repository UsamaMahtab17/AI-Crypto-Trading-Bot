import pandas as pd
import matplotlib.pyplot as plt
import requests
import datetime

# Function to fetch cryptocurrency data
def fetch_crypto_data(symbol, interval, start_date, end_date):
    base_url = "https://api.binance.com/api/v3/klines"
    params = {
        "symbol": symbol,
        "interval": interval,
        "startTime": int(datetime.datetime.strptime(start_date, "%Y-%m-%d").timestamp() * 1000),
        "endTime": int(datetime.datetime.strptime(end_date, "%Y-%m-%d").timestamp() * 1000),
        "limit": 1000
    }
    response = requests.get(base_url, params=params)
    data = response.json()

    if response.status_code != 200 or not data:
        raise Exception("Failed to fetch data. Check your symbol, interval, or date range.")

    # Create DataFrame from the fetched data
    df = pd.DataFrame(data, columns=[
        "Open Time", "Open", "High", "Low", "Close", "Volume", "Close Time", "Quote Asset Volume", "Number of Trades", "Taker Buy Base Asset Volume", "Taker Buy Quote Asset Volume", "Ignore"
    ])

    # Keep only relevant columns
    df = df[["Open Time", "Open", "High", "Low", "Close", "Volume"]]

    # Convert to proper data types
    df["Open Time"] = pd.to_datetime(df["Open Time"], unit="ms")
    df.set_index("Open Time", inplace=True)
    df = df.astype({"Open": "float", "High": "float", "Low": "float", "Close": "float", "Volume": "float"})

    return df

# Function to calculate MACD and Signal Line
def calculate_macd(data, short_window=12, long_window=26, signal_window=9):
    # Calculate Short-Term EMA (12 periods by default)
    data['EMA_12'] = data['Close'].ewm(span=short_window, adjust=False).mean()
    # Calculate Long-Term EMA (26 periods by default)
    data['EMA_26'] = data['Close'].ewm(span=long_window, adjust=False).mean()
    # MACD Line: Difference between Short-Term EMA and Long-Term EMA
    data['MACD'] = data['EMA_12'] - data['EMA_26']
    # Signal Line: EMA of the MACD Line
    data['Signal'] = data['MACD'].ewm(span=signal_window, adjust=False).mean()
    # Histogram: Difference between MACD Line and Signal Line
    data['Histogram'] = data['MACD'] - data['Signal']
    return data

# Function to visualize the MACD strategy
def plot_macd(data, title='MACD Strategy Visualization', save_path=None):
    plt.figure(figsize=(14, 7))

    # Plot the closing price
    plt.subplot(2, 1, 1)
    plt.plot(data['Close'], label='Closing Price', color='blue')
    plt.title(f'{title} - Closing Price')
    plt.legend()
    plt.grid()

    # Plot MACD, Signal Line, and Histogram
    plt.subplot(2, 1, 2)
    plt.plot(data['MACD'], label='MACD Line', color='green')
    plt.plot(data['Signal'], label='Signal Line', color='red')
    plt.bar(data.index, data['Histogram'], label='Histogram', color='gray', alpha=0.4)
    plt.axhline(0, color='black', linestyle='--', linewidth=0.7, alpha=0.7)
    plt.title('MACD Indicator')
    plt.legend()
    plt.grid()

    plt.tight_layout()
    if save_path:
        plt.savefig(save_path)
        print(f"Plot saved to {save_path}")
    plt.show()


# Function to identify signals (crossover and divergence)
def identify_signals(data):
    data['Signal_Crossover'] = 0
    data['Divergence'] = ''

    for i in range(1, len(data)):
        # Signal Line Crossovers
        if data['MACD'][i] > data['Signal'][i] and data['MACD'][i - 1] <= data['Signal'][i - 1]:
            data['Signal_Crossover'][i] = 1  # Bullish Crossover
        elif data['MACD'][i] < data['Signal'][i] and data['MACD'][i - 1] >= data['Signal'][i - 1]:
            data['Signal_Crossover'][i] = -1  # Bearish Crossover

        # Divergence (more comprehensive check)
        if data['Close'][i] < data['Close'][i - 1] and data['MACD'][i] > data['MACD'][i - 1]:
            data['Divergence'][i] = 'Bullish'
        elif data['Close'][i] > data['Close'][i - 1] and data['MACD'][i] < data['MACD'][i - 1]:
            data['Divergence'][i] = 'Bearish'

        # MACD Zero Line Crossings
        if data['MACD'][i] > 0 and data['MACD'][i - 1] <= 0:
            data['Zero_Line_Crossing'] = 1  # Bullish Momentum
        elif data['MACD'][i] < 0 and data['MACD'][i - 1] >= 0:
            data['Zero_Line_Crossing'] = -1  # Bearish Momentum

        # Histogram Trend Check
        if data['Histogram'][i] > 0 and data['Histogram'][i - 1] <= 0:
            data['Histogram_Trend'] = 'Increasing Bullish Momentum'
        elif data['Histogram'][i] < 0 and data['Histogram'][i - 1] >= 0:
            data['Histogram_Trend'] = 'Increasing Bearish Momentum'

    return data

# Main code
if __name__ == "__main__":
    # Parameters for fetching data
    symbol = "BTCUSDT"  # Cryptocurrency pair
    interval = "1h"  # Time interval (e.g., 1h, 1d)
    start_date = "2023-01-01"  # Start date
    end_date = "2023-12-31"  # End date

    # Fetch data
    data = fetch_crypto_data(symbol, interval, start_date, end_date)

    # Calculate MACD and Signal Line
    data = calculate_macd(data)

    # Identify signals (crossover and divergence)
    data = identify_signals(data)

    # Visualize the MACD strategy
    plot_macd(data, save_path='macd_strategy_plot.png')

    # Save results to a new CSV file
    data.to_csv('crypto_macd_signals-v2.csv')

