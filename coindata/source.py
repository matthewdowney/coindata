import abc
import itertools
import json
import os.path
import urllib.request
from datetime import datetime, timedelta
from decimal import Decimal

_ONE_DAY = timedelta(days=1)


def get_source(source_name):
    constructor = {
        "btc": lambda: BTCPrice(),
        "eth": lambda: ETHPrice()
    }.get(source_name.lower())

    if constructor:
        return constructor()
    else:
        raise Exception("No market is present for " + source_name)


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
        cache = JSONDataCache('eth', self.__query_raw_data, self.__validate_raw_data)
        self._data = self.__clean_raw_data(cache.get())

    def __query_raw_data(self):
        """
        Get etherchain's JSON data.
        """
        return json_query_utf_8("https://etherchain.org/api/statistics/price")['data']

    def __clean_raw_data(self, data):
        """
        Turn etherchain's raw data into a {datetime: Decimal} key/value dict.
        """

        def get_date(ts_str):
            return datetime.strptime(ts_str.split("T")[0], "%Y-%m-%d")

        cleaned = {}
        idx = 0
        while idx < len(data):
            # Aggregate data for this day
            day = get_date(data[idx]['time'])
            for_day = [x for x in
                       itertools.takewhile(lambda datum: get_date(datum['time']) == day, data[idx:])]

            # Average price data for the day and insert it into our data set
            cleaned[day] = round(Decimal(sum([Decimal(str(d['usd'])) for d in for_day])) / Decimal(len(for_day)), 2)
            idx += len(for_day)
        return cleaned

    def __validate_raw_data(self, data):
        """
        Check if the data are up to date.
        """
        cleaned = self.__clean_raw_data(data)
        today = datetime.now()
        return cleaned.get(datetime(today.year, today.month, today.day)) is not None

    def price(self, d):
        return self._data.get(datetime(d.year, d.month, d.day))


class BTCPrice(Source):
    def __init__(self):
        cache = JSONDataCache("btc", self.__query_raw_data, self.__validate_raw_data)
        self._data = self.__clean_raw_data(cache.get())

    def __query_raw_data(self):
        """
        Get coindesk's JSON data.
        """
        return json_query_utf_8("https://api.coindesk.com/v1/bpi/historical/close.json?start=2010-07-17&end={}"
                                .format(datetime.strftime(datetime.now(), "%Y-%m-%d")))

    def __clean_raw_data(self, data):
        """
        Turn coindesk's raw data into a {datetime: Decimal} key/value dict.
        """
        return {datetime.strptime(date_str, "%Y-%m-%d"): round(Decimal(str(price)), 2)
                for date_str, price in data['bpi'].items()}

    def __validate_raw_data(self, data):
        """
        Check if the data are up to date.
        """
        cleaned = self.__clean_raw_data(data)
        yesterday = datetime.now() - _ONE_DAY
        return cleaned.get(datetime(yesterday.year, yesterday.month, yesterday.day)) is not None

    def price(self, d):
        return self._data.get(datetime(d.year, d.month, d.day))


class JSONDataCache(object):
    """
    A file system cache for data queried via rest.
    """

    def __init__(self, name, queryer, validator):
        """
        :param name: The name of the cache. (Should be unique.)
        :param queryer: A function which accepts no parameters and returns json serializable data.
        :param validator: A function which accepts json-serialized data and returns true if the data are valid.
        """
        self.cache_name = ".{}_cache".format(name)
        self.queryer = queryer
        self.validator = validator

    def get(self):
        """
        Get data from the cache, if it exists, and return the data if they are valid. If the data are invalid or the
        cache is not present, execute a query and store the data.
        """
        data = None
        if os.path.isfile(self.cache_name):
            with open(self.cache_name, 'r') as f:
                data = json.load(f)
            if data and self.validator(data):
                return data
            else:
                data = None  # Data is invalid, get rid of it

        if not data:
            data = self.queryer()
            with open(self.cache_name, 'w') as f:
                json.dump(data, f)
            return data


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
