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
