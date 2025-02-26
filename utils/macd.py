# Function to calculate MACD parameters
def calculate_macd(prices, short_window=12, long_window=26, signal_window=9):
    prices['EMA_12'] = prices['Close'].ewm(span=short_window, adjust=False).mean()
    prices['EMA_26'] = prices['Close'].ewm(span=long_window, adjust=False).mean()
    prices['MACD'] = prices['EMA_12'] - prices['EMA_26']
    prices['Signal'] = prices['MACD'].ewm(span=signal_window, adjust=False).mean()
    prices['Histogram'] = prices['MACD'] - prices['Signal']
    return prices

# Function to identify MACD signals
def identify_signals(data, long_window=26):
    # Focus only on the relevant subset of data
    subset = data.tail(long_window + 1)  # Include the last `long_window` + 1 rows for comparison
    latest_index = subset.index[-1]  # Get the index of the latest row

    # Initialize columns if missing
    if 'Signal_Crossover' not in data.columns:
        data['Signal_Crossover'] = 0
    if 'Divergence' not in data.columns:
        data['Divergence'] = ''
    if 'Zero_Line_Crossing' not in data.columns:
        data['Zero_Line_Crossing'] = 0
    if 'Histogram_Trend' not in data.columns:
        data['Histogram_Trend'] = ''

    # Ensure there are enough rows in the subset
    if len(subset) < 2:
        return data  # Not enough data to calculate signals

    # Calculate signals only for the latest row
    latest_row = subset.iloc[-1]
    prev_row = subset.iloc[-2]

    # Signal Line Crossovers
    if latest_row['MACD'] > latest_row['Signal'] and prev_row['MACD'] <= prev_row['Signal']:
        data.at[latest_index, 'Signal_Crossover'] = 1  # Bullish Crossover
    elif latest_row['MACD'] < latest_row['Signal'] and prev_row['MACD'] >= prev_row['Signal']:
        data.at[latest_index, 'Signal_Crossover'] = -1  # Bearish Crossover

    # Divergence
    if latest_row['Close'] < prev_row['Close'] and latest_row['MACD'] > prev_row['MACD']:
        data.at[latest_index, 'Divergence'] = 'Bullish'
    elif latest_row['Close'] > prev_row['Close'] and latest_row['MACD'] < prev_row['MACD']:
        data.at[latest_index, 'Divergence'] = 'Bearish'

    # Zero Line Crossings
    if latest_row['MACD'] > 0 and prev_row['MACD'] <= 0:
        data.at[latest_index, 'Zero_Line_Crossing'] = 1  # Bullish Momentum
    elif latest_row['MACD'] < 0 and prev_row['MACD'] >= 0:
        data.at[latest_index, 'Zero_Line_Crossing'] = -1  # Bearish Momentum

    # Histogram Trends
    if latest_row['Histogram'] > 0 and prev_row['Histogram'] <= 0:
        data.at[latest_index, 'Histogram_Trend'] = 'Increasing Bullish Momentum'
    elif latest_row['Histogram'] < 0 and prev_row['Histogram'] >= 0:
        data.at[latest_index, 'Histogram_Trend'] = 'Increasing Bearish Momentum'

    return data

