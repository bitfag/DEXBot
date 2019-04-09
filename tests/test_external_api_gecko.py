import pytest

from dexbot.external_api.price_engine import PriceQueryEngine


@pytest.fixture(scope='module', params=[('gecko', 'BTC/USD'), ('gecko', 'USD/BTC')])
def price_engine(request):
    engine = PriceQueryEngine(request.param[0], request.param[1])
    return engine


def test_center_price(price_engine):
    assert price_engine.get_market_center_price() > 0
