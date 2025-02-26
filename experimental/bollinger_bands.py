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

    df = pd.DataFrame(data, columns=[
        "Open Time", "Open", "High", "Low", "Close", "Volume", "Close Time", "Quote Asset Volume", "Number of Trades", "Taker Buy Base Asset Volume", "Taker Buy Quote Asset Volume", "Ignore"
    ])

    df = df[["Open Time", "Open", "High", "Low", "Close", "Volume"]]

    df["Open Time"] = pd.to_datetime(df["Open Time"], unit="ms")
    df.set_index("Open Time", inplace=True)
    df = df.astype({"Open": "float", "High": "float", "Low": "float", "Close": "float", "Volume": "float"})

    return df

# Function to calculate Bollinger Bands
def calculate_bollinger_bands(data, window=20, multiplier=2):
    data['Middle Band'] = data['Close'].rolling(window=window).mean()
    data['Standard Deviation'] = data['Close'].rolling(window=window).std()
    data['Upper Band'] = data['Middle Band'] + (multiplier * data['Standard Deviation'])
    data['Lower Band'] = data['Middle Band'] - (multiplier * data['Standard Deviation'])
    return data

# Function to identify Bollinger Band signals
def identify_bollinger_signals(data):
    data['Upper Touch'] = data['Close'] > data['Upper Band']
    data['Lower Touch'] = data['Close'] < data['Lower Band']
    data['Reentry Upper'] = (data['Close'] < data['Upper Band']) & data['Upper Touch'].shift(1)
    data['Reentry Lower'] = (data['Close'] > data['Lower Band']) & data['Lower Touch'].shift(1)

    data['Squeeze'] = data['Upper Band'] - data['Lower Band']
    data['Squeeze Signal'] = data['Squeeze'] < data['Squeeze'].rolling(window=20).mean()

    data['Bollinger Bounce Buy'] = (data['Close'] == data['Lower Band'])
    data['Bollinger Bounce Sell'] = (data['Close'] == data['Upper Band'])

    # Identify double tops and bottoms
    data['Double Bottom'] = ((data['Close'].shift(1) < data['Lower Band'].shift(1)) &
                             (data['Close'] > data['Lower Band']) &
                             (data['Close'].rolling(window=5).min() == data['Close']))

    data['Double Top'] = ((data['Close'].shift(1) > data['Upper Band'].shift(1)) &
                          (data['Close'] < data['Upper Band']) &
                          (data['Close'].rolling(window=5).max() == data['Close']))
    return data

# Function to visualize Bollinger Band strategy
def plot_bollinger_bands(data, title='Bollinger Bands Strategy', save_path=None):
    plt.figure(figsize=(14, 7))
    
    # Plot price and bands
    plt.plot(data['Close'], label='Closing Price', color='blue')
    plt.plot(data['Middle Band'], label='Middle Band (MA)', color='green')
    plt.plot(data['Upper Band'], label='Upper Band', color='red', linestyle='--')
    plt.plot(data['Lower Band'], label='Lower Band', color='red', linestyle='--')
    
    # Highlight signals
    plt.scatter(data[data['Upper Touch']].index, data[data['Upper Touch']]['Close'], marker='^', color='orange', label='Upper Touch')
    plt.scatter(data[data['Lower Touch']].index, data[data['Lower Touch']]['Close'], marker='v', color='purple', label='Lower Touch')
    plt.scatter(data[data['Reentry Upper']].index, data[data['Reentry Upper']]['Close'], marker='x', color='lime', label='Reentry Upper')
    plt.scatter(data[data['Reentry Lower']].index, data[data['Reentry Lower']]['Close'], marker='x', color='pink', label='Reentry Lower')
    plt.scatter(data[data['Double Bottom']].index, data[data['Double Bottom']]['Close'], marker='o', color='cyan', label='Double Bottom')
    plt.scatter(data[data['Double Top']].index, data[data['Double Top']]['Close'], marker='o', color='magenta', label='Double Top')

    #     # Plot signals
    # colors = {
    #     'Touching Upper Band': 'orange',
    #     'Touching Lower Band': 'purple',
    #     'Bollinger Band Squeeze': 'brown',
    #     'Bollinger Bounce (Buy)': 'lime',
    #     'Bollinger Bounce (Sell)': 'pink',
    #     'Double Bottom': 'cyan',
    #     'Double Top': 'magenta'
    # }

    # for _, signal in signals.iterrows():
    #     plt.scatter(signal['time'], data.loc[signal['time'], 'Close'], 
    #                 label=signal['type'], color=colors[signal['type']], s=50, edgecolors='black')

    plt.title(title)
    plt.legend()
    plt.grid()

    if save_path:
        plt.savefig(save_path)
        print(f"Plot saved to {save_path}")

    plt.show()

# Main code
if __name__ == "__main__":
    # Parameters for fetching data
    symbol = "BTCUSDT"  # Cryptocurrency pair
    interval = "1d"  # Time interval (e.g., 1h, 1d)
    start_date = (datetime.datetime.now() - datetime.timedelta(days=180)).strftime("%Y-%m-%d")  # Start date (6 months)
    end_date = datetime.datetime.now().strftime("%Y-%m-%d")  # End date
    # Fetch data
    data = fetch_crypto_data(symbol, interval, start_date, end_date)

    # Calculate Bollinger Bands
    data = calculate_bollinger_bands(data)

    # Identify signals
    data = identify_bollinger_signals(data)

    # Visualize the Bollinger Bands strategy
    plot_bollinger_bands(data, save_path='bollinger_bands_strategy_plot.png')

    # Save results to a CSV file
    data.to_csv('bollinger_bands_signals.csv')
