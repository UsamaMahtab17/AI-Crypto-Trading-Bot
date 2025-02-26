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

# Function to calculate RSI
def calculate_rsi(data, period=14):
    delta = data['Close'].diff()

    # Calculate gains and losses
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)

    # Calculate average gain and loss
    avg_gain = gain.rolling(window=period, min_periods=1).mean()
    avg_loss = loss.rolling(window=period, min_periods=1).mean()

    # Calculate RS and RSI
    rs = avg_gain / avg_loss
    data['RSI'] = 100 - (100 / (1 + rs))

    return data

# Function to identify RSI signals
def identify_rsi_signals(data):
    signals = []

    for i in range(1, len(data)):
        signal = {'id': i, 'type': None, 'time': data.index[i]}

        # Overbought (RSI > 70)
        if data['RSI'][i] > 70:
            signal['type'] = 'Overbought'
            signals.append(signal)

        # Oversold (RSI < 30)
        elif data['RSI'][i] < 30:
            signal['type'] = 'Oversold'
            signals.append(signal)

        # RSI Crossover
        if data['RSI'][i - 1] < 30 and data['RSI'][i] >= 30:
            signal['type'] = 'Bullish Crossover'
            signals.append(signal)
        if data['RSI'][i - 1] > 70 and data['RSI'][i] <= 70:
            signal['type'] = 'Bearish Crossover'
            signals.append(signal)

        # Divergence (requires price comparison)
        if i > 1:
            if data['Close'][i - 1] < data['Close'][i - 2] and data['RSI'][i - 1] > data['RSI'][i - 2]:
                signal['type'] = 'Bullish Divergence'
                signals.append(signal)
            if data['Close'][i - 1] > data['Close'][i - 2] and data['RSI'][i - 1] < data['RSI'][i - 2]:
                signal['type'] = 'Bearish Divergence'
                signals.append(signal)

    return pd.DataFrame(signals)

# Function to plot RSI and trading signals
def plot_rsi(data, signals, title='RSI Strategy', save_path=None):
    fig, ax = plt.subplots(2, 1, figsize=(14, 10), gridspec_kw={'height_ratios': [3, 2]})

    # Plot price data
    ax[0].plot(data.index, data['Close'], label='Close Price', color='blue', linewidth=1)
    ax[0].set_title(f'{title} - Price')
    ax[0].set_ylabel('Price')
    # ax[0].legend(loc='upper left')
    ax[0].grid()

    # Plot RSI
    ax[1].plot(data.index, data['RSI'], label='RSI', color='purple', linewidth=1)
    ax[1].axhline(70, color='red', linestyle='--', linewidth=0.5, label='Overbought (70)')
    ax[1].axhline(30, color='green', linestyle='--', linewidth=0.5, label='Oversold (30)')
    ax[1].set_title('RSI')
    ax[1].set_ylabel('RSI')
    ax[1].set_xlabel('Date')
    # ax[1].legend(loc='upper left')
    ax[1].grid()

    # Plot signals
    for _, signal in signals.iterrows():
        if signal['type'] in ['Overbought', 'Oversold']:
            ax[0].scatter(signal['time'], data.loc[signal['time'], 'Close'],
                          label=signal['type'], color='red' if signal['type'] == 'Overbought' else 'green', s=50)
        if signal['type'] in ['Bullish Crossover', 'Bearish Crossover']:
            ax[1].scatter(signal['time'], data.loc[signal['time'], 'RSI'],
                          label=signal['type'], color='lime' if signal['type'] == 'Bullish Crossover' else 'orange', s=50)

    # Remove duplicate labels from the legend
    handles_0, labels_0 = ax[0].get_legend_handles_labels()
    by_label_0 = dict(zip(labels_0, handles_0))
    ax[0].legend(by_label_0.values(), by_label_0.keys(), loc='upper left')

    handles_1, labels_1 = ax[1].get_legend_handles_labels()
    by_label_1 = dict(zip(labels_1, handles_1))
    ax[1].legend(by_label_1.values(), by_label_1.keys(), loc='upper left')

    plt.tight_layout()

    if save_path:
        plt.savefig(save_path)
        print(f"Plot saved to {save_path}")

    plt.show()

# Function to save RSI signals with all relevant data
def save_rsi_signals(data, signals, file_name='rsi_signals.csv'):
    # Merge signals with the main data
    signals_with_data = pd.DataFrame(index=data.index)
    signals_with_data['Type'] = None  # Initialize Type column for signals
    
    # Fill in signals in the main DataFrame
    for _, signal in signals.iterrows():
        signals_with_data.loc[signal['time'], 'Type'] = signal['type']
    
    # Combine the data and signals
    combined_data = pd.concat([data, signals_with_data['Type']], axis=1)
    combined_data.reset_index(inplace=True)  # Reset index for saving
    
    # Save to CSV
    combined_data.to_csv(file_name, index=False)
    print(f"Signals and data saved to '{file_name}'")


# Main code
if __name__ == "__main__":
    # Parameters for fetching data
    symbol = "BTCUSDT"  # Cryptocurrency pair
    interval = "1h"  # Time interval (e.g., 1h, 1d)
    start_date = (datetime.datetime.now() - datetime.timedelta(days=180)).strftime("%Y-%m-%d")  # Start date (6 months)
    end_date = datetime.datetime.now().strftime("%Y-%m-%d")  # End date

    # Fetch data
    data = fetch_crypto_data(symbol, interval, start_date, end_date)

    # Calculate RSI
    data = calculate_rsi(data)

    # Identify signals
    signals = identify_rsi_signals(data)

    # Visualize RSI strategy
    plot_rsi(data, signals, save_path='rsi_strategy_plot.png')

    # Save results to a CSV
    # signals.to_csv('rsi_signals.csv', index=False)
    save_rsi_signals(data, signals, file_name='rsi_signals.csv')

    print("Signals saved to 'rsi_signals.csv'")
