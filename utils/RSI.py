import pandas as pd

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


def identify_rsi_signals(data):
    """
    Identify RSI signals (Overbought, Oversold, Crossovers, Divergence) and append them to the DataFrame.

    Parameters:
        data (pd.DataFrame): DataFrame containing 'RSI' and 'Close' columns.
                             Assumes new data is appended to the end of the DataFrame.

    Returns:
        pd.DataFrame: Updated DataFrame with signal information in new columns.
    """
    # Ensure there are enough rows to calculate signals
    if len(data) < 3:
        # Initialize empty columns if not already present
        for col in ["Signal_Type", "Bullish_Divergence", "Bearish_Divergence"]:
            if col not in data.columns:
                data[col] = None
        return data

    # Initialize signal columns if they don't exist
    if "Signal_Type" not in data.columns:
        data["Signal_Type"] = None
    if "Bullish_Divergence" not in data.columns:
        data["Bullish_Divergence"] = False
    if "Bearish_Divergence" not in data.columns:
        data["Bearish_Divergence"] = False

    # Get the latest row and its preceding rows
    latest_row = data.iloc[-1]
    prev_row = data.iloc[-2]
    prev_prev_row = data.iloc[-3]

    # Signal type for the latest row
    signal_type = None

    # Overbought (RSI > 70)
    if latest_row["RSI"] > 70:
        signal_type = "Overbought"

    # Oversold (RSI < 30)
    elif latest_row["RSI"] < 30:
        signal_type = "Oversold"

    # Bullish Crossover (RSI crosses above 30)
    elif prev_row["RSI"] < 30 and latest_row["RSI"] >= 30:
        signal_type = "Bullish Crossover"

    # Bearish Crossover (RSI crosses below 70)
    elif prev_row["RSI"] > 70 and latest_row["RSI"] <= 70:
        signal_type = "Bearish Crossover"

    # Divergences
    bullish_divergence = (
        prev_row["Close"] < prev_prev_row["Close"]  # Price making lower lows
        and prev_row["RSI"] > prev_prev_row["RSI"]  # RSI making higher highs
    )

    bearish_divergence = (
        prev_row["Close"] > prev_prev_row["Close"]  # Price making higher highs
        and prev_row["RSI"] < prev_prev_row["RSI"]  # RSI making lower lows
    )

    # Append signal type to the latest row
    data.at[data.index[-1], "Signal_Type"] = signal_type
    data.at[data.index[-1], "Bullish_Divergence"] = bullish_divergence
    data.at[data.index[-1], "Bearish_Divergence"] = bearish_divergence

    return data

# def identify_rsi_signals(data):
#     """
#     Identify RSI signals (Overbought, Oversold, Crossovers, Divergence) only for the latest row.

#     Parameters:
#         data (pd.DataFrame): DataFrame containing 'RSI' and 'Close' columns.
#                              Assumes new data is appended to the end of the DataFrame.

#     Returns:
#         dict: A dictionary containing the latest signal details or None if no signal.
#     """
#     # Ensure there are enough rows to calculate signals
#     if len(data) < 3:
#         return None

#     # Get the latest row and its preceding rows
#     latest_row = data.iloc[-1]
#     prev_row = data.iloc[-2]
#     prev_prev_row = data.iloc[-3]

#     signal = {
#         "type": None,
#         "time": latest_row["Time"],
#         "RSI": latest_row["RSI"],
#         "Close": latest_row["Close"],
#     }

#     # Overbought (RSI > 70)
#     if latest_row["RSI"] > 70:
#         signal["type"] = "Overbought"

#     # Oversold (RSI < 30)
#     elif latest_row["RSI"] < 30:
#         signal["type"] = "Oversold"

#     # Bullish Crossover (RSI crosses above 30)
#     elif prev_row["RSI"] < 30 and latest_row["RSI"] >= 30:
#         signal["type"] = "Bullish Crossover"

#     # Bearish Crossover (RSI crosses below 70)
#     elif prev_row["RSI"] > 70 and latest_row["RSI"] <= 70:
#         signal["type"] = "Bearish Crossover"

#     # Bullish Divergence (requires 3 rows for comparison)
#     elif (
#         prev_row["Close"] < prev_prev_row["Close"]  # Price making lower lows
#         and prev_row["RSI"] > prev_prev_row["RSI"]  # RSI making higher highs
#     ):
#         signal["type"] = "Bullish Divergence"

#     # Bearish Divergence
#     elif (
#         prev_row["Close"] > prev_prev_row["Close"]  # Price making higher highs
#         and prev_row["RSI"] < prev_prev_row["RSI"]  # RSI making lower lows
#     ):
#         signal["type"] = "Bearish Divergence"

#     # If no signal is detected
#     if signal["type"] is None:
#         return None

#     return signal


# # Function to identify RSI signals
# def identify_rsi_signals(data):
#     signals = []

#     for i in range(1, len(data)):
#         signal = {'id': i, 'type': None, 'time': data.index[i]}

#         # Overbought (RSI > 70)
#         if data['RSI'][i] > 70:
#             signal['type'] = 'Overbought'
#             signals.append(signal)

#         # Oversold (RSI < 30)
#         elif data['RSI'][i] < 30:
#             signal['type'] = 'Oversold'
#             signals.append(signal)

#         # RSI Crossover
#         if data['RSI'][i - 1] < 30 and data['RSI'][i] >= 30:
#             signal['type'] = 'Bullish Crossover'
#             signals.append(signal)
#         if data['RSI'][i - 1] > 70 and data['RSI'][i] <= 70:
#             signal['type'] = 'Bearish Crossover'
#             signals.append(signal)

#         # Divergence (requires price comparison)
#         if i > 1:
#             if data['Close'][i - 1] < data['Close'][i - 2] and data['RSI'][i - 1] > data['RSI'][i - 2]:
#                 signal['type'] = 'Bullish Divergence'
#                 signals.append(signal)
#             if data['Close'][i - 1] > data['Close'][i - 2] and data['RSI'][i - 1] < data['RSI'][i - 2]:
#                 signal['type'] = 'Bearish Divergence'
#                 signals.append(signal)

#     return pd.DataFrame(signals)