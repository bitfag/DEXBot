from dexbot.external_api.helper import strip_prefix, split_pair, get_derived_markets


def test_strip_prefix():
    assert strip_prefix('RUDEX.BTC') == 'BTC'


def test_split_pair():
    assert split_pair('BTC/USD') == ['BTC', 'USD']
    assert split_pair('BTC:USD') == ['BTC', 'USD']
    assert split_pair('BTC-USD') == ['BTC', 'USD']


def test_derived_markets():
    assert get_derived_markets('LTC/BTS', 'BTC') == ('LTC/BTC', 'BTC/BTS')
    assert get_derived_markets('LTC/BTS', 'BTC', invert=True) == ('LTC/BTC', 'BTS/BTC')
