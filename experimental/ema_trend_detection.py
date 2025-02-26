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

# Function to calculate EMA
def calculate_ema(data, period, column='Close'):
    data[f'EMA_{period}'] = data[column].ewm(span=period, adjust=False).mean()
    return data

# Function to identify EMA signals
def identify_ema_signals(data, short_period=12, long_period=26):
    data = calculate_ema(data, short_period)
    data = calculate_ema(data, long_period)

    signals = []

    for i in range(1, len(data)):
        signal = {'id': i, 'type': None, 'time': data.index[i]}

        # Bullish Crossover
        if data[f'EMA_{short_period}'][i - 1] < data[f'EMA_{long_period}'][i - 1] and data[f'EMA_{short_period}'][i] >= data[f'EMA_{long_period}'][i]:
            signal['type'] = 'Bullish Crossover'
            signals.append(signal)

        # Bearish Crossover
        elif data[f'EMA_{short_period}'][i - 1] > data[f'EMA_{long_period}'][i - 1] and data[f'EMA_{short_period}'][i] <= data[f'EMA_{long_period}'][i]:
            signal['type'] = 'Bearish Crossover'
            signals.append(signal)

    signals_df = pd.DataFrame(signals)
    signals_df = signals_df.merge(data, left_on='time', right_index=True, how='left')

    return signals_df

# Function to plot EMA and trading signals
def plot_ema(data, signals, short_period, long_period, title='EMA Strategy', save_path=None):
    plt.figure(figsize=(14, 8))

    # Plot price data and EMAs
    plt.plot(data.index, data['Close'], label='Close Price', color='blue', linewidth=1)
    plt.plot(data.index, data[f'EMA_{short_period}'], label=f'EMA {short_period}', color='green', linestyle='--', linewidth=1)
    plt.plot(data.index, data[f'EMA_{long_period}'], label=f'EMA {long_period}', color='red', linestyle='--', linewidth=1)

    # Track whether a label for each signal type has been added
    added_labels = {'Bullish Crossover': False, 'Bearish Crossover': False}

    # Plot signals
    for _, signal in signals.iterrows():
        if signal['type'] == 'Bullish Crossover':
            plt.scatter(signal['time'], signal['Close'], 
                        color='lime', s=50,
                        label='Bullish Crossover' if not added_labels['Bullish Crossover'] else "")
            added_labels['Bullish Crossover'] = True
        elif signal['type'] == 'Bearish Crossover':
            plt.scatter(signal['time'], signal['Close'], 
                        color='orange', s=50,
                        label='Bearish Crossover' if not added_labels['Bearish Crossover'] else "")
            added_labels['Bearish Crossover'] = True

    plt.title(f'{title}')
    plt.xlabel('Date')
    plt.ylabel('Price')
    plt.legend(loc='best')
    plt.grid()

    if save_path:
        plt.savefig(save_path)

    plt.show()

# Function to save the entire dataset with signals
def save_data_with_signals(data, signals, file_path):
    # Combine the data and signals
    combined_data = data.copy()

    # Merge signals into the data DataFrame on the index (time)
    signals = signals.set_index('time')  # Ensure 'time' is the index for merging
    combined_data = combined_data.merge(signals[['id', 'type']], how='left', left_index=True, right_index=True)

    # Save the combined dataset to a CSV file
    combined_data.to_csv(file_path)
    print(f"Data with signals saved to {file_path}")

# Main script to execute the strategy
if __name__ == "__main__":
    # Fetch data
    symbol = "BTCUSDT"
    interval = "1d"
    # Calculate dynamic date range
    end_date = datetime.datetime.now().strftime("%Y-%m-%d")
    start_date = (datetime.datetime.now() - datetime.timedelta(days=180)).strftime("%Y-%m-%d")

    data = fetch_crypto_data(symbol, interval, start_date, end_date)

    # Identify signals
    short_period = 12
    long_period = 26
    signals = identify_ema_signals(data, short_period, long_period)

    # Plot signals
    plot_ema(data, signals, short_period, long_period, save_path='ema_strategy_plot.png')

    # Save signals to CSV
    save_data_with_signals(data, signals, "ema_signals.csv")
