from kraken import KrakenAPI


balance = KrakenAPI().get_balance()

print(balance)