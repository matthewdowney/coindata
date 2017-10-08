import abc
import itertools
import json
import urllib.request
from datetime import datetime, timedelta
from decimal import Decimal

_ONE_DAY = timedelta(days=1)


class Source(object):
    __metaclass__ = abc.ABCMeta

    @abc.abstractmethod
    def price(self, date):
        """
        :param date: The date for which to retrieve the price.
        :return: The price as a decimal, or None if it's not available.
        """
        pass

    def range(self, date_start, date_end):
        """
        A generator for (date, price) data within some range.
        :param date_start: The start date, inclusive.
        :param date_end: The end date, inclusive.
        :return: A generator of (date, price) data points over the given range. Dates without corresponding price data
        are ignored.
        """
        current = date_start
        while current <= date_end:
            while self.price(current) is None and current <= date_end:
                current += _ONE_DAY
            if current <= date_end:
                yield (current, self.price(current))
                current += _ONE_DAY

        return


class ETHPrice(Source):
    def __init__(self):
        # List of {time=timestamp, usd=price} objects
        time_series_data = json_query_utf_8("https://etherchain.org/api/statistics/price")['data']

        def get_date(ts_str):
            return datetime.strptime(ts_str.split("T")[0], "%Y-%m-%d")

        self._data = {}
        idx = 0
        while idx < len(time_series_data):
            # Aggregate data for this day
            day = get_date(time_series_data[idx]['time'])
            for_day = [x for x in
                       itertools.takewhile(lambda datum: get_date(datum['time']) == day, time_series_data[idx:])]

            # Average price data for the day and insert it into our data set
            self._data[day] = round(Decimal(sum([Decimal(str(d['usd'])) for d in for_day])) / Decimal(len(for_day)), 2)
            idx += len(for_day)

    def price(self, date):
        return self._data.get(datetime(date.year, date.month, date.day))


class BTCPrice(Source):
    def __init__(self):
        now = datetime.now()
        self._data = {datetime.strptime(date_str, "%Y-%m-%d"): round(Decimal(str(price)), 2) for date_str, price in
                      json_query_utf_8(
                          "https://api.coindesk.com/v1/bpi/historical/close.json?start=2010-07-17&end={}"
                              .format(datetime.strftime(now, "%Y-%m-%d")))['bpi'].items()}

    def price(self, date):
        return self._data.get(datetime(date.year, date.month, date.day))


def json_query_utf_8(url, headers=None):
    """
    Send an HTTP GET and attempt to interpret the response as utf-8 JSON.
    :param headers:
    :param url: The URL to request.
    :return: Object representation of the JSON hierarchy.
    """
    rq = urllib.request.Request(url)
    SPOOF_AGENT = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_1) AppleWebKit/537.36 (KHTML, like Gecko) ' \
                  'Chrome/39.0.2171.95 Safari/537.36 '
    rq.add_header('User-Agent', SPOOF_AGENT)
    if headers is not None:
        rq.headers.update(headers)
    with urllib.request.urlopen(rq) as page:
        data = page.read()
        encoding = page.info().get_content_charset("utf-8")
        js = json.loads(data.decode(encoding))
        return js
