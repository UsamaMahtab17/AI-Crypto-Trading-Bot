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
