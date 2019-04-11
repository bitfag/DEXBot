import asyncio
import math
import logging

from dexbot.exceptions import NotImplementedException
from .helper import strip_prefix, split_pair, get_derived_markets

log = logging.getLogger(__name__)


class ExternalEngineBase:
    """ Base class for interacting with external exchanges. All exchange-specific classes should inherit this class.

        :param str exchange: exchange name, bittrex / binance /etc
        :param str market: market to operate on in format of 'QUOTE/BASE'
        :param xxx loop: (optional) asyncio event loop
        :param logging.Logger logger: (optional) logger instance. Each worker can pass own per-worker logger into this
            class, so log messages will be worker-specific.

        Note: This class does not have a logic to substite USD assets, like USD -> USDT. The class users are responsible
        for passing correct asset symbols. The exception is to strip gateway prefixes, like OPEN.LTC -> LTC, RUDEX.BTC
        -> BTC and so on
    """

    def __init__(self, exchange, market, loop=None, logger=None):

        self.quote_currency, self.base_currency = split_pair(market)

        # Strip gateway prefixes here
        self.quote_currency = strip_prefix(self.quote_currency)
        self.base_currency = strip_prefix(self.base_currency)
        self.market = '{}/{}'.format(self.quote_currency, self.base_currency)

        # self.local_eventloop = False

        if not loop:
            loop = asyncio.get_event_loop()
            # self.local_eventloop = True
        self.loop = loop

        # Use local logger if external wasn't passed
        self.log = log
        if logger:
            self.log = logger

    def get_derived_center_price(
        self, quote_amount=0, base_amount=0, suppress_errors=False, market=None, intermediate_asset='BTC'
    ):
        """ Returns the center price of indirect market by calculating the price by using intermediate asset, e.g.
            LTC/BTS price is obtained from LTC/BTC and BTS/BTC markets.

            :param float quote_amount: amount of QUOTE asset to use in depth measurement
            :param float base_amount: amount of BASE asset to use in depth measurement
            :param bool suppress_errors: (optional) False = if error will occur, emit an error message and return None
            :param str market: (optional) override market
            :param str intermediate_asset: (optional) specify intermediate asset to use for price conversion, usually
                BTC or USD
            :return: Market center price as float
            :rtype: float
        """
        if not market:
            market = self.market

        intermediate_asset = intermediate_asset.upper()

        # Return direct center price if intermediate asset is BASE or QUOTE
        if self.quote_currency == intermediate_asset or self.base_currency == intermediate_asset:
            return self.get_market_center_price(
                base_amount=base_amount, quote_amount=quote_amount, suppress_errors=suppress_errors
            )

        center_price = 0.0

        # Get markets over intermediate asset, use inverted market for 2nd step because most exchanges have only BTC or
        # USD markets
        market1, market2 = get_derived_markets(self.market, intermediate_asset, invert=True)
        price1 = self.get_market_center_price(quote_amount=quote_amount, suppress_errors=True, market=market1)
        price2 = self.get_market_center_price(base_amount=base_amount, suppress_errors=True, market=market2)

        if price1 and price2:
            # Use division as 2nd price is inverted
            center_price = price1 / price2
        elif not suppress_errors:
            self.log.error(
                "Cannot estimate center price across markets, price1: {:.8f}, price2: {:.8f}".format(price1, price2)
            )
            return None

        self.log.debug('Derived center price is: {:.8f}'.format(center_price))

        return center_price

    def get_market_center_price(self, quote_amount=0, base_amount=0, suppress_errors=False, market=None):
        """ Returns the center price of market including own orders.

            :param float quote_amount: amount of QUOTE asset to use in depth measurement
            :param float base_amount: amount of BASE asset to use in depth measurement
            :param bool suppress_errors: (optional) False = if error will occur, emit an error message and return None
            :param str market: (optional) override market
            :return: Market center price as float, or None on error
            :rtype: float
        """
        center_price = 0.0
        buy_price = 0
        sell_price = 0

        if not market:
            market = self.market

        # If amounts are not given, use ticker data
        if not base_amount and not quote_amount:
            buy_price, sell_price = self.get_ticker_prices(market=market)
        else:
            # Fetch orderbook once, and pass it to the methods to avoid excess queries
            orderbook = self.get_orderbook(market=market)
            buy_price = self.get_market_buy_price(
                quote_amount=quote_amount,
                base_amount=base_amount,
                exclude_own_orders=False,
                market=market,
                cached_orderbook=orderbook,
            )
            sell_price = self.get_market_sell_price(
                quote_amount=quote_amount,
                base_amount=base_amount,
                exclude_own_orders=False,
                market=market,
                cached_orderbook=orderbook,
            )
        if buy_price is None or buy_price == 0.0:
            if not suppress_errors:
                self.log.critical("Cannot estimate center price, there is no highest bid.")
                return None

        if sell_price is None or sell_price == 0.0:
            if not suppress_errors:
                self.log.critical("Cannot estimate center price, there is no lowest ask.")
                return None

        if buy_price:
            center_price = buy_price * math.sqrt(sell_price / buy_price)
            self.log.debug('Center price in PriceQueryEngine.get_market_center_price: {:.8f} '.format(center_price))

        return center_price

    def get_market_spread(self, quote_amount=0, base_amount=0, market=None):
        """ Returns the market spread %, including own orders, from specified depth.

            :param float quote_amount: amount of QUOTE asset to use in depth measurement
            :param float base_amount: amount of BASE asset to use in depth measurement
            :param str market: (optional) override market
            :return: Market spread as float or None
            :rtype: float or None
        """
        if not market:
            market = self.market

        # Fetch orderbook once, and pass it to the methods to avoid excess queries
        orderbook = None
        if quote_amount > 0 or base_amount > 0:
            # We need to preload orderbook because with 0 amounts ticker data will be used
            orderbook = self.get_orderbook(market=market)
        ask = self.get_market_sell_price(
            quote_amount=quote_amount,
            base_amount=base_amount,
            exclude_own_orders=False,
            market=market,
            cached_orderbook=orderbook,
        )
        bid = self.get_market_buy_price(
            quote_amount=quote_amount,
            base_amount=base_amount,
            exclude_own_orders=False,
            market=market,
            cached_orderbook=orderbook,
        )

        if ask == 0 or bid == 0:
            return None

        return ask / bid - 1

    def get_ticker_prices(self, market=None):
        """ Obtain highest bid and lowest ask prices from ticker data

            :param str market: (optional) override market to get ticker for
            :return: buy_price, sell_price - highest bid and lowest ask prices from ticker data, as floats
            :rtype: tuple
        """
        if not market:
            market = self.market

        return self._get_ticker_prices(market)

    def _get_ticker_prices(self, market):
        """ Stub for exchange-specific method

            :param str market: market to get ticker price for, in format of 'QUOTE/BASE'
            :return: buy_price, sell_price - highest bid and lowest ask prices from ticker data, as floats
            :rtype: tuple
        """
        raise NotImplementedException('This method is supposed to be overriden in a subclass')

    def get_market_buy_price(
        self, quote_amount=0, base_amount=0, exclude_own_orders=True, market=None, cached_orderbook=None
    ):
        """ Returns the BASE/QUOTE price for which [depth] worth of QUOTE could be bought, enhanced with
            moving average or weighted moving average.

            [quote/base]_amount = 0 means lowest regardless of size

            :param float quote_amount: amount of QUOTE asset to use in depth measurement
            :param float base_amount: amount of BASE asset to use in depth measurement
            :param bool exclude_own_orders: Exclude own orders when calculating a price
            :param str market: (optional) override market
            :param dict cached_orderbook: (optional) pass pre-loaded orderbok, format is similar to get_orderbook()
            :return: price
            :rtype: float
        """
        if not market:
            market = self.market

        buy_price = 0

        # If amounts are not given, use ticker data
        if not base_amount and not quote_amount:
            buy_price, sell_price = self.get_ticker_prices(market=market)
            return buy_price

        # When amounts are not given, call exchange-specific method.
        # Expect to get a list of tuples representing orderbook entries similar to ccxt format
        # {'bids': [(price, amount)]}
        orderbook = cached_orderbook if cached_orderbook else self.get_orderbook(market=market, book='bids')

        # Prefer base_amount over quote_amount
        asset_amount = base_amount
        if base_amount > quote_amount:
            base = True
        else:
            asset_amount = quote_amount
            base = False

        # To obtain exactly specified amount, we need to multiply it by market fee
        target_amount = asset_amount * (1 + self.get_market_fee(market=market))
        base_amount, quote_amount = self._get_sum_amounts(target_amount, orderbook['bids'], base=base)

        # Prevent division by zero
        if not quote_amount:
            return 0.0

        return base_amount / quote_amount

    def get_market_sell_price(
        self, quote_amount=0, base_amount=0, exclude_own_orders=True, market=None, cached_orderbook=None
    ):
        """ Returns the BASE/QUOTE price for which [quote_amount] worth of QUOTE could be bought,
            enhanced with moving average or weighted moving average.

            [quote/base]_amount = 0 means lowest regardless of size

            :param float quote_amount: amount of QUOTE asset to use in depth measurement
            :param float base_amount: amount of BASE asset to use in depth measurement
            :param bool exclude_own_orders: Exclude own orders when calculating a price
            :param str market: (optional) override market
            :param dict cached_orderbook: (optional) pass pre-loaded orderbok, format is similar to get_orderbook()
            :return: price
            :rtype: float
        """
        if not market:
            market = self.market

        buy_price = 0

        # If amounts are not given, use ticker data
        if not base_amount and not quote_amount:
            buy_price, sell_price = self.get_ticker_prices(market=market)
            return sell_price

        # When amounts are not given, call exchange-specific method.
        # Expect to get a list of tuples representing orderbook entries similar to ccxt format
        # {'bids': [(price, amount)]}
        orderbook = cached_orderbook if cached_orderbook else self.get_orderbook(market=market, book='asks')

        # Prefer quote_amount over base_amount
        asset_amount = quote_amount
        if base_amount > quote_amount:
            base = True
            asset_amount = base_amount
        else:
            base = False

        # To obtain exactly specified amount, we need to multiply it by market fee
        target_amount = asset_amount * (1 + self.get_market_fee(market=market))
        base_amount, quote_amount = self._get_sum_amounts(target_amount, orderbook['asks'], base=base)

        # Prevent division by zero
        if not quote_amount:
            return 0.0

        return base_amount / quote_amount

    @staticmethod
    def _get_sum_amounts(target_amount, orders, base=True):
        """ Returns amounts of BASE and QUOTE for target_amount orderbook depth

            :param float target_amount: measure orderbook for this amount
            :param list orders: bids or asks orders
            :param bool base: (optional) True = measure BASE amount, False = QUOTE
            :return: sum amount of BASE and QUOTE
            :rtype: tuple
        """
        sum_quote = 0
        sum_base = 0
        missing_amount = target_amount

        for order in orders:
            price, order_quote = order
            order_base = order_quote * price
            if base:
                if order_base <= missing_amount:
                    sum_quote += order_quote
                    sum_base += order_base
                    missing_amount -= order_base
                else:
                    sum_quote += missing_amount / price
                    sum_base += missing_amount
                    break
            else:
                if order_quote <= missing_amount:
                    sum_quote += order_quote
                    sum_base += order_base
                    missing_amount -= order_quote
                else:
                    sum_quote += missing_amount
                    sum_base += missing_amount * price
                    break

        return sum_base, sum_quote

    def get_orderbook(self, market=None, book=None):
        """ Return orderbook in an unified, exchange-independent format

            :param str market: (optional) override market
            :param str book: (optional) specify 'bids' or 'asks' to get only desired book
            :return: dict with 'bids' and 'asks' lists of list tuples representing orderbook entries where each entry is
                expressed as (price: float, amount: float)
            :rtype: dict

            Return format is a dict with the following structure:

            .. code-block:: python

                {
                    'bids': [
                        [price, amount],  # [ float, float ]
                        [price, amount],
                        ...
                    ],
                    'asks': [
                        [price, amount],
                        [price, amount],
                        ...
                    ],
                }
        """
        if not market:
            market = self.market

        return self._get_orderbook(market, book=book)

    def _get_orderbook(self, market, book=None):
        """ Stub for exchange-specific method. Supposed to return an orderbook.

            :param str market: market, in format of 'QUOTE/BASE'
            :param str book: (optional) specify 'bids' or 'asks' to get only desired book
            :return: dict with 'bids' and 'asks' lists of list tuples representing orderbook entries where each entry is
                expressed as (price: float, amount: float)
            :rtype: dict
        """
        raise NotImplementedException('This method is supposed to be overriden in a subclass')

    def get_market_buy_orders(self, market=None):
        """ Return buy side of the orderbook, format is similar to get_orderbook()

            :param str market: (optional) override market
        """
        return self.get_orderbook(market=market, book='bids')['bids']

    def get_market_sell_orders(self, market=None):
        """ Return sell side of the orderbook, format is similar to get_orderbook()

            :param str market: (optional) override market
        """
        return self.get_orderbook(market=market, book='asks')['asks']

    def get_market_fee(self, market=None):
        """ Return market fee

            :param str market: (optional) override market
            :return: market fee as fraction of 1
            :rtype: float
        """
        if not market:
            market = self.market

        # Todo: implement caching if this data is dynamically loaded
        # Todo: add handling for maker/taker fee separation

        return self._get_market_fee(market)

    def _get_market_fee(self, market):
        """ Stub for exchange-specific method. Supposed to return market fee.

            :param str market: market, in format of 'QUOTE/BASE'
            :return: market fee as fraction of 1
            :rtype: float
        """
        raise NotImplementedException('This method is supposed to be overriden in a subclass')
