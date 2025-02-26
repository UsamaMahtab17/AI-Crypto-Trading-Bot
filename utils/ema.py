import pandas as pd

# Function to calculate EMA
def calculate_ema(data, period, column='Close'):
    data[f'EMA_{period}'] = data[column].ewm(span=period, adjust=False).mean()
    return data


# Function to identify EMA signals
def identify_ema_signals(data, short_period=12, long_period=26):
    """
    Identify EMA signals (Bullish or Bearish Crossovers) only for the latest row.

    Parameters:
        data (pd.DataFrame): DataFrame containing 'Close' column.
                             Assumes new data is appended to the end of the DataFrame.
        short_period (int): Short EMA period (default: 12).
        long_period (int): Long EMA period (default: 26).

    Returns:
        pd.DataFrame: Updated DataFrame with EMA signals appended.
    """
    # Ensure there are enough rows to calculate signals
    if len(data) < max(short_period, long_period):
        for col in [f"EMA_{short_period}", f"EMA_{long_period}", "EMA_Signal"]:
            if col not in data.columns:
                data[col] = None
        return data

    # Calculate EMAs
    data = calculate_ema(data, short_period)
    data = calculate_ema(data, long_period)

    # Initialize signal column if missing
    if "EMA_Signal" not in data.columns:
        data["EMA_Signal"] = None

    # Get the latest row and the previous row
    latest_row = data.iloc[-1]
    prev_row = data.iloc[-2]

    signal_type = None

    # Identify Bullish Crossover
    if (
        prev_row[f"EMA_{short_period}"] < prev_row[f"EMA_{long_period}"]
        and latest_row[f"EMA_{short_period}"] >= latest_row[f"EMA_{long_period}"]
    ):
        signal_type = "Bullish Crossover"

    # Identify Bearish Crossover
    elif (
        prev_row[f"EMA_{short_period}"] > prev_row[f"EMA_{long_period}"]
        and latest_row[f"EMA_{short_period}"] <= latest_row[f"EMA_{long_period}"]
    ):
        signal_type = "Bearish Crossover"

    # Update the latest row with the signal
    data.at[data.index[-1], "EMA_Signal"] = signal_type

    return data



# # Function to identify EMA signals
# def identify_ema_signals(data, short_period=12, long_period=26):
#     data = calculate_ema(data, short_period)
#     data = calculate_ema(data, long_period)

#     signals = []

#     for i in range(1, len(data)):
#         signal = {'id': i, 'type': None, 'time': data.index[i]}

#         # Bullish Crossover
#         if data[f'EMA_{short_period}'][i - 1] < data[f'EMA_{long_period}'][i - 1] and data[f'EMA_{short_period}'][i] >= data[f'EMA_{long_period}'][i]:
#             signal['type'] = 'Bullish Crossover'
#             signals.append(signal)

#         # Bearish Crossover
#         elif data[f'EMA_{short_period}'][i - 1] > data[f'EMA_{long_period}'][i - 1] and data[f'EMA_{short_period}'][i] <= data[f'EMA_{long_period}'][i]:
#             signal['type'] = 'Bearish Crossover'
#             signals.append(signal)

#     signals_df = pd.DataFrame(signals)
#     signals_df = signals_df.merge(data, left_on='time', right_index=True, how='left')

#     return signals_df
