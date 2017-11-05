I got tired of downloading a new CSV from coindesk--then writing the same boilerplate to read it--every time. Prices are daily, but feel free to send a PR & upgrade it if there's a more granular data source out there.

## Example

```python
from decimal import Decimal, getcontext
from functools import reduce

from coindata.source import get_source
from datetime import datetime, timedelta

# Set decimal precision
getcontext().prec = 500

for asset in ("BTC", "ETH"):
    # Create a data source
    data_source = get_source(asset)
    now = datetime.now()

    # Print the most recent price (either today or yesterday)
    if data_source.price(now):
        print("Today's price for {} is {}".format(asset, data_source.price(now)))
    else:
        print("Today's price for {} is unestablished, but yesterday's price was {}"
              .format(asset, data_source.price(now-timedelta(days=1))))

    # Track daily performance over the month
    month_start = datetime(now.year, now.month, 1)
    daily_performance = []
    last_price = None
    for date, price in data_source.range(month_start, now):  # Range of price data
        if last_price:
            percent_change = ((price - last_price) / Decimal(last_price)) * Decimal(100)
            daily_performance.append(percent_change)
        last_price = price

    avg_performance = round(sum(daily_performance) / Decimal(len(daily_performance)), 2)
    print("Average daily change of {}%, best and worst daily change of {}% and {}%"
          .format(avg_performance, round(max(daily_performance), 2), round(min(daily_performance), 2)))
    print("")
```

## Contribute
To add a different data source, create a subclass of the `Source` class (`coindata/source.py`) and add your data source to the factory `get_source`.

E.g. to add an hourly historical BTC price source:

```python
class BTCHourly(Source):
    def __init__(self):
        cache = query_and_cache_magical_public_hourly_price_source()

    def price(self, date):
        return get_price_from_cache(date)
```

```python
def get_source(source_name):
    constructor = {
        "btc": lambda: BTCPrice(),
        "eth": lambda: ETHPrice(),
        "btc-hourly": lambda: BTCHourly(),  # Add the new data source
    }.get(source_name.lower())

    if constructor:
        return constructor()
    else:
        raise Exception("No market is present for " + source_name)
```

```python
# Use
data_source = get_source("btc-hourly")
now = datetime.now()

if data_source.price(now):
    print("This hour's price for BTC is {}".format(data_source.price(now)))
else:
    print("This hour's price for BTC is unestablished, but last hour's price was {}"
          .format(data_source.price(now-timedelta(hours=1))))
```
