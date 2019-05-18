from pycoingecko import CoinGeckoAPI

from .base_engine import ExternalEngineBase
from .helper import strip_prefix, split_pair


class GeckoEngine(ExternalEngineBase):
    def __init__(self, market, *args, **kwargs):

        super().__init__('gecko', market, *args, **kwargs)

        # Initialize gecko API
        self.api = CoinGeckoAPI()

        # All supported coins id, name and symbol, format is [{'id': xxx, 'symbol': yyy, 'name': zzz}]
        self.coins_list = self.api.get_coins_list()
        # All supported base currencies, format is [str]
        self.vs_currencies = self.api.get_supported_vs_currencies()

        self.market = self._convert_market(self.market)

    def _convert_market(self, market, _stop=False):
        """ Coingecko do not operate using short symbols, thus we need to convert "QUOTE/BASE" market into gecko ids

            :param str market: market format of 'QUOTE/BASE'
            :param bool _stop: (optional) recusion stop flag, for internal use only
            :return: dict with gecko ids {'base': xxx, 'quote': yyy, 'invertred': bool}
            :rtype: dict
        """
        # Split market
        quote_currency, base_currency = split_pair(market)

        # Strip gateway prefixes
        quote_currency = strip_prefix(quote_currency)
        base_currency = strip_prefix(base_currency)

        market = {}
        # On recursive call invert flag is on
        market['inverted'] = _stop
        market['quote'] = self._get_coin_id(quote_currency)
        market['base'] = self._get_vs_currency(base_currency)

        if not market['quote'] or not market['base']:
            if _stop:
                return None
            else:
                market = '{}/{}'.format(base_currency, quote_currency)
                market = self._convert_market(market, _stop=True)

        return market

    def _get_coin_id(self, symbol):
        """ Obtain gecko coin id from symbol

            :param str symbol: currency symbol like BTC, BTS
            :return: gecko coin id like 'bitcoin' or None if not supported
            :rtype: str or None
        """
        for entry in self.coins_list:
            if entry['symbol'].upper() == symbol:
                return entry['id']
        return None

    def _get_vs_currency(self, symbol):
        """ Check that given currency symbol is supported as BASE currency

            :param str symbol: currency symbol like USD, CNY
            :return: gecko vs_currency like usd, cny, or None if not supported
            :rtype: str or None
        """
        symbol = symbol.lower()
        if symbol in self.vs_currencies:
            return symbol
        else:
            return None

    def _get_price(self, market):
        """ Obtain price on gecko market

            :param dict market: dict with keys 'base' and 'quote' where 'base' should be a vs_currency, and quote should
                be coin id
            :return: current price or None
            :rtype: float or None
        """
        coin_data = self.api.get_coins_markets(market['base'], ids=market['quote'])

        if isinstance(coin_data, list) and len(coin_data) > 0:
            return coin_data[0].get('current_price', None)

        return None

    def get_market_center_price(self, suppress_errors=False, market=None, **kwargs):
        """ Obtain price from gecko data

            :param bool suppress_errors: (optional) False = if error will occur, emit an error message and return None
            :param str,dict market: (optional): market to get price for, can be a 'QUOTE/BASE' string or dict of
                internal format
            :return: price
            :rtype: float or None
        """
        original_market = market
        price = 0.0

        if not market:
            market = self.market
        elif isinstance(market, str):
            market = self._convert_market(market)

        # No such market
        if market is None:
            if not suppress_errors:
                self.log.error('No such market: {}'.format(original_market))
                return None
        else:
            price = self._get_price(market)
            if price and market['inverted']:
                return 1 / price

        return price

    def get_derived_center_price(
        self, suppress_errors=False, market=None, intermediate_asset='BTC', **kwargs
    ):
        """ Returns the center price of indirect market by calculating the price by using intermediate asset, e.g.
            LTC/BTS price is obtained from LTC/BTC and BTS/BTC markets.

            :param bool suppress_errors: (optional) False = if error will occur, emit an error message and return None
            :param str,dict market: (optional): market to get price for, can be a 'QUOTE/BASE' string or dict of
                internal format
            :param str intermediate_asset: (optional) specify intermediate asset to use for price conversion, usually
                BTC or USD
            :return: Market center price as float
            :rtype: float
        """
        original_market = market

        if not market:
            # Market was not passed
            market = self.market
        elif isinstance(market, str):
            # Market passed as 'QUOTE/BASE', get internal format
            market = self._convert_market(market)

        # Return direct center price if direct market exists
        if market:
            return self.get_market_center_price(market=market)

        intermediate_asset = intermediate_asset.upper()
        price = 0.0


    # Comments:
    # Market is mandatory when instantiating a class
    # External methods doesn't have a market
    # Internal methods do have market
