import re


def strip_prefix(symbol):
    """ Strip gateway prefixes from asset names, like BRIDGE.BTC -> BTC

        :param str symbol: currency symbol like BTC, BRIDGE.BTC, OPEN.LTC etc
        :return: symbol without prefix
        :rtype: str
    """
    if '.' in symbol:
        return symbol.split('.')[-1]
    else:
        return symbol


def split_pair(market):
    """ Split market pair into QUOTE, BASE symbols

        :param str market: market pair in format 'QUOTE/BASE'. Supported separators are: "/", ":", "-".
        :return: list with QUOTE and BASE as separate symbols
        :rtype: list
    """
    return re.split('/|:|-', market.upper())


def get_derived_markets(market, intermediate_asset, invert=False):
    """ Return two markets derived from QUOTE/BASE into QUOTE/XXX, XXX/BASE

        :param str market: market pair
        :param str intermediate_asset: intermediate asset
        :param bool invert: True = return second market in inverted format, may be useful for CEXs where you can use
            only fixed BASEs
        :return: two market strings
        :rtype: tuple
    """
    quote, base = split_pair(market)
    market1 = '{}/{}'.format(quote, intermediate_asset)
    if invert:
        market2 = '{}/{}'.format(base, intermediate_asset)
    else:
        market2 = '{}/{}'.format(intermediate_asset, base)

    return market1, market2
