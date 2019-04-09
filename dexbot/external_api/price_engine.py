from .ccxt_engine import CcxtEngine
from .gecko_engine import GeckoEngine


class PriceQueryEngine(CcxtEngine, GeckoEngine):
    """ Interface to do read-only queries of external APIs

        :param str exchange: exchange name, bittrex / binance /etc
        :param str market: market to operate on in format of 'QUOTE/BASE'
        :param xxx loop: (optional) asyncio event loop
    """

    def __init__(self, exchange, market, *args, **kwargs):

        if exchange == 'gecko':
            GeckoEngine.__init__(self, market, *args, **kwargs)
        elif exchange == 'waves':
            pass
        else:
            CcxtEngine.__init__(self, exchange, market, *args, **kwargs)
