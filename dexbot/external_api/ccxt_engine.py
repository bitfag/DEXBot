#import asyncio
#import ccxt.async_support as ccxt
import ccxt

from .base_engine import ExternalEngineBase


class CcxtEngine(ExternalEngineBase):
    """ CEX interface based on ccxt library

        To get info about ccxt and supported exchanges, see https://ccxt.readthedocs.io/en/latest/manual.html
    """
    def __init__(self, exchange, market, *args, **kwargs):

        super().__init__(exchange, market, *args, **kwargs)

        self.exchange = getattr(ccxt, exchange)({'verbose': False})

    async def fetch_ticker_async(self, market):
        """ Fetch ticker in async manner (stub)

            :param str market: market to get ticker for, in format of 'QUOTE/BASE'
        """

        ticker = None
        try:
            ticker = await self.exchange.fetch_ticker(market)
        except ccxt.RequestTimeout:
            self.log.info('Request Timeout (ignoring)')
        except ccxt.ExchangeNotAvailable:
            self.log.info('Exchange Not Available due to downtime or maintenance (ignoring)')
        except Exception:
            # Todo: too broad handling
            self.log.exception('Other Exchange Error (ignoring)')

        # await self.exchange.close()

        return ticker

    def fetch_ticker(self, market):
        """ Fetch ticker

            :param str market: market to get ticker for, in format of 'QUOTE/BASE'
        """
        ticker = None
        try:
            ticker = self.exchange.fetch_ticker(market)
        except ccxt.RequestTimeout:
            self.log.info('Request Timeout (ignoring)')
        except ccxt.ExchangeNotAvailable:
            self.log.info('Exchange Not Available due to downtime or maintenance (ignoring)')
        except Exception:
            self.log.exception('Other Exchange Error (ignoring)')

        return ticker

    def _get_ticker_prices(self, market):
        """ Obtain highest bid and lowest ask prices from ticker data

            :param str market: market to get ticker price for, in format of 'QUOTE/BASE'
            :return: buy_price, sell_price - highest bid and lowest ask prices from ticker data, as floats
            :rtype: tuple
        """
        bid = 0
        ask = 0

        # ticker = self.loop.run_until_complete(self.fetch_ticker(market))
        ticker = self.fetch_ticker(market)

        if ticker:
            bid = ticker.get('bid', 0)
            ask = ticker.get('ask', 0)

        return bid, ask

    def _get_orderbook(self, market, book=None):
        """ Return an orderbook.

            :param str market: market, in format of 'QUOTE/BASE'
            :param str book: (optional) stub, ccxt doesn't support fetching only 'bids' or 'asks' book
            :return: dict with 'bids' and 'asks' lists of list tuples representing orderbook entries where each entry is
                expressed as (price: float, amount: float)
            :rtype: dict
        """

        orderbook = self.exchange.fetchOrderBook(market)

        return orderbook

    def _get_market_fee(self, market, fee_type='taker'):
        """ Get market fee

            FYI: this methods works only if some other query was performed prior.

            :param str market: market, in format of 'QUOTE/BASE'
            :param str fee_type: (optional) ccxt allows to get "taker" or "maker" fee
        """
        return self.exchange.markets[market][fee_type]
