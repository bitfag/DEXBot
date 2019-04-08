import pytest

from dexbot.external_api.price_engine import PriceQueryEngine


@pytest.fixture(scope='module', params=[('bittrex', 'BTC/USD')])
def price_engine(request):
    engine = PriceQueryEngine(request.param[0], request.param[1])
    return engine


@pytest.fixture(scope='module', params=[('bittrex', 'LTC/BTS')])
def price_engine_derived_market(request):
    engine = PriceQueryEngine(request.param[0], request.param[1])
    return engine


def test_derived_center_price(price_engine_derived_market):
    """ Test center price for indirect markets
    """
    assert price_engine_derived_market.get_derived_center_price() > 0


def test_orderbook(price_engine):
    orderbook = price_engine.get_orderbook()
    assert orderbook['bids'][0] is not None
    assert orderbook['asks'][0] is not None


def test_market_fee(price_engine):
    """ FYI: for ccxt, this test works only when at least one query was performed prior
    """
    assert price_engine.get_market_fee() > 0


def test_center_price(price_engine):
    assert price_engine.get_market_center_price() > 0
    assert price_engine.get_market_center_price(base_amount=1000) > 0


def test_buy_price(price_engine):
    assert price_engine.get_market_buy_price() is not None
    assert price_engine.get_market_buy_price(base_amount=100) is not None
    assert price_engine.get_market_buy_price(quote_amount=1) is not None
    assert price_engine.get_market_buy_price(base_amount=100, quote_amount=1) is not None


def test_sell_price(price_engine):
    assert price_engine.get_market_sell_price() is not None
    assert price_engine.get_market_sell_price(base_amount=100) is not None
    assert price_engine.get_market_sell_price(quote_amount=1) is not None
    assert price_engine.get_market_sell_price(base_amount=100, quote_amount=1) is not None


def test_market_spread(price_engine):
    assert price_engine.get_market_spread() > 0
    assert price_engine.get_market_spread(base_amount=10000) > 0
    assert price_engine.get_market_spread(quote_amount=0.5) > 0


def test_market_buy_orders(price_engine):
    orders = price_engine.get_market_buy_orders()
    assert isinstance(orders, list)
    assert len(orders) > 0


def test_market_sell_orders(price_engine):
    orders = price_engine.get_market_sell_orders()
    assert isinstance(orders, list)
    assert len(orders) > 0
