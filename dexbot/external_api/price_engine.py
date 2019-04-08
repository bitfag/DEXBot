from .ccxt_engine import CcxtEngine


class PriceQueryEngine(CcxtEngine):
    """ Interface to do read-only queries of external APIs

        :param str exchange: exchange name, bittrex / binance /etc
        :param str market: market to operate on in format of 'QUOTE/BASE'
        :param xxx loop: (optional) asyncio event loop
    """

    def __init__(self, exchange, market, *args, **kwargs):

        if exchange == 'gecko':
            pass
        elif exchange == 'waves':
            pass
        else:
            CcxtEngine.__init__(self, exchange, market, *args, **kwargs)
