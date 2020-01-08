import logging

import pytest
from bitshares.amount import Amount
from dexbot.strategies.flexible_orders import Strategy

# Turn on debug for dexbot logger
log = logging.getLogger("dexbot")
log.setLevel(logging.DEBUG)


def test_validate_orders():
    # Correct input
    test_input = '10-20-30'
    expected = [0.1, 0.2, 0.3]
    assert Strategy.validate_orders(test_input) == expected

    # Percent > 100
    test_input = '30-50-40'
    with pytest.raises(ValueError):
        Strategy.validate_orders(test_input)

    # Incorrect values
    test_input = 'a-b-c'
    with pytest.raises(ValueError):
        Strategy.validate_orders(test_input)

    # Incorrect delimiter
    test_input = '10+5+1'
    with pytest.raises(ValueError):
        Strategy.validate_orders(test_input)


def test_check_cp_shift_is_too_big(strategy_worker):
    worker = strategy_worker
    worker.price_change_threshold = 1 / 100

    assert worker.check_cp_shift_is_too_big(1, 2) is True
    assert worker.check_cp_shift_is_too_big(2, 1) is True

    old_cp = 1
    new_cp = old_cp * (1 + worker.price_change_threshold / 2)
    assert worker.check_cp_shift_is_too_big(old_cp, new_cp) is False


def test_calc_ratios(strategy_worker):
    worker = strategy_worker

    a, b = worker.calc_ratios(3)
    assert a + b == 1


def test_calc_center_price_external(strategy_worker, monkeypatch):
    def mocked_cp(*args):
        return 1

    def mocked_cp_bad(*args):
        return None

    worker = strategy_worker
    worker.external_feed = True
    worker.external_price_source = 'binance'

    # Normal case
    monkeypatch.setattr(worker, 'get_external_market_center_price', mocked_cp)
    assert worker.calc_center_price() == 1

    # Fail
    monkeypatch.setattr(worker, 'get_external_market_center_price', mocked_cp_bad)
    with pytest.raises(TypeError):
        worker.calc_center_price()


def test_calc_center_price_last_trade(strategy_worker, monkeypatch):
    def mocked_cp(*args):
        return 1

    def mocked_cp_bad(*args):
        return None

    def mocked_last_trade(*args):
        return {'base': 1, 'quote': 1, 'price': 1}

    # Normal case
    worker = strategy_worker
    worker['bootstrapped'] = True
    worker.cp_from_last_trade = True
    monkeypatch.setattr(worker, 'get_own_last_trade', mocked_last_trade)
    assert worker.calc_center_price() == 1

    # Fallback to market CP
    monkeypatch.setattr(worker, 'get_own_last_trade', mocked_cp_bad)
    monkeypatch.setattr(worker, 'get_market_center_price', mocked_cp)
    assert worker.calc_center_price() == 1

    # Fallback didn't work
    monkeypatch.setattr(worker, 'get_market_center_price', mocked_cp_bad)
    with pytest.raises(TypeError):
        worker.calc_center_price()


def test_calc_center_price_market(strategy_worker, monkeypatch):
    def mocked_cp(*args, **kwargs):
        return 1

    def mocked_cp_bad(*args, **kwargs):
        return None

    worker = strategy_worker
    monkeypatch.setattr(worker, 'get_market_center_price', mocked_cp)
    assert worker.calc_center_price() == 1

    monkeypatch.setattr(worker, 'get_market_center_price', mocked_cp_bad)
    with pytest.raises(TypeError):
        worker.calc_center_price()


def test_filter_closest_orders(strategy_worker):
    worker = strategy_worker
    worker.place_market_buy_order(1, 0.9)
    closesest_buy = worker.place_market_buy_order(1, 0.95)

    worker.place_market_sell_order(1, 1.1)
    closest_sell = worker.place_market_sell_order(1, 1.05)

    closest = worker.filter_closest_orders(worker.own_orders)
    assert closest[0]['id'] == closesest_buy['id']
    assert closest[1]['id'] == closest_sell['id']


def test_filter_closest_orders_missing(strategy_worker):
    worker = strategy_worker
    worker.place_market_buy_order(1, 0.9)
    closesest_buy = worker.place_market_buy_order(1, 0.95)

    closest = worker.filter_closest_orders(worker.own_orders)
    assert closest[0]['id'] == closesest_buy['id']


def test_place_orders(strategy_worker, monkeypatch, bitshares):
    def mocked_cp(*args, **kwargs):
        return 1

    def mocked_cp_bad(*args, **kwargs):
        return None

    def ratio_zero_base(*args):
        return 0, 1

    def ratio_zero_quote(*args):
        return 1, 0

    def zero_balance_base(asset):
        if asset == worker.market['base']:
            return Amount(0, asset, bitshares_instance=bitshares)
        else:
            return Amount(100, asset, bitshares_instance=bitshares)

    def zero_balance_quote(asset):
        if asset == worker.market['quote']:
            return Amount(0, asset, bitshares_instance=bitshares)
        else:
            return Amount(100, asset, bitshares_instance=bitshares)

    worker = strategy_worker
    num_orders_expected = len(worker.buy_orders_percentages) + len(worker.sell_orders_percentages)

    # Good cp
    monkeypatch.setattr(worker, 'get_market_center_price', mocked_cp)
    worker.place_orders()
    assert len(worker.own_orders) == num_orders_expected

    # Bad cp
    monkeypatch.setattr(worker, 'get_market_center_price', mocked_cp_bad)
    worker.place_orders()
    assert len(worker.own_orders) == 0

    # Buy stop
    monkeypatch.setattr(worker, 'get_market_center_price', mocked_cp)
    worker.buy_stop_ratio = 1
    worker.place_orders()
    assert len(worker.get_own_buy_orders()) == 0
    worker.buy_stop_ratio = 0.5

    # Sell stop
    worker.sell_stop_ratio = 1
    worker.place_orders()
    assert len(worker.get_own_sell_orders()) == 0
    worker.sell_stop_ratio = 0.5

    # No buy order if BASE balance == 0
    worker.buy_stop_ratio = 0
    monkeypatch.setattr(worker, 'balance', zero_balance_base)
    worker.place_orders()
    assert len(worker.get_own_buy_orders()) == 0
    worker.buy_stop_ratio = 0.5

    # No sell order if QUOTE balance == 0
    worker.sell_stop_ratio = 0
    monkeypatch.setattr(worker, 'balance', zero_balance_quote)
    worker.place_orders()
    assert len(worker.get_own_sell_orders()) == 0
    worker.sell_stop_ratio = 0.5


def test_maintain_strategy(strategy_worker, other_worker, other_orders):
    worker = strategy_worker
    worker2 = other_worker

    num_orders_expected = len(worker.buy_orders_percentages) + len(worker.sell_orders_percentages)

    # Fresh run no orders
    worker.maintain_strategy()
    assert len(worker.own_orders) == num_orders_expected

    # Simulate order filled
    order = worker.get_own_buy_orders()[0]
    worker.cancel_orders(order)
    worker.maintain_strategy()
    assert len(worker.own_orders) == num_orders_expected

    # Order partially filled
    order = worker.get_own_buy_orders()[0]
    to_sell = order['quote']['amount'] * worker.partial_fill_threshold * 1.02
    sell_price = order['price'] / 1.01
    log.debug('Sell {} @ {}'.format(to_sell, sell_price))
    worker2.place_market_sell_order(to_sell, sell_price)
    worker.maintain_strategy()
    for order in worker.own_orders:
        assert order['base']['amount'] == order['for_sale']['amount']

    # Center price change
    worker.is_reset_on_price_change = True
    orders_before = worker.own_orders
    order = worker.get_own_buy_orders()[0]
    to_sell = order['quote']['amount']
    # We're placing a sell order close to worker buy to shift center price
    sell_price = order['price'] * 1.02
    log.debug('Sell {} @ {}'.format(to_sell, sell_price))
    worker2.place_market_sell_order(to_sell, sell_price)
    worker.maintain_strategy()
    orders_after = worker.own_orders
    assert orders_before != orders_after


def test_maintain_strategy_transition_from_staggered_orders(strategy_worker, other_worker, other_orders, monkeypatch):
    def mocked_orders():
        return {'fdfgf-hghgsfdf-hghg': {'id': 'fdfgf-hghgsfdf-hghg'}}

    def mocked_filter(*args):
        return args[0]

    worker = strategy_worker
    num_orders_expected = len(worker.buy_orders_percentages) + len(worker.sell_orders_percentages)

    monkeypatch.setattr(worker, 'fetch_orders', mocked_orders)
    monkeypatch.setattr(worker, 'filter_closest_orders', mocked_filter)
    worker.maintain_strategy()
    assert len(worker.own_orders) == num_orders_expected
