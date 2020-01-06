import pytest
import time
import copy
import logging

from dexbot.strategies.base import StrategyBase
from dexbot.strategies.flexible_orders import Strategy

log = logging.getLogger("dexbot")


@pytest.fixture(scope='session')
def assets(create_asset):
    """ Create some assets with different precision
    """
    create_asset('BASEA', 3)
    create_asset('QUOTEA', 8)


@pytest.fixture(scope='module')
def base_account(assets, prepare_account):
    """ Factory to generate random account with pre-defined balances
    """

    def func():
        account = prepare_account({'BASEA': 100, 'QUOTEA': 100, 'TEST': 1000})
        return account

    return func


@pytest.fixture(scope='module')
def account(base_account):
    """ Prepare worker account with some balance
    """
    return base_account()


@pytest.fixture(scope='session')
def dexbot_worker_name():
    """ Fixture to share worker name
    """
    return 'foo'


@pytest.fixture
def config(bitshares, account, dexbot_worker_name):
    """ Define worker's config

        This fixture should be function-scoped to use new fresh bitshares account for each test
    """
    worker_name = dexbot_worker_name
    config = {
        'node': '{}'.format(bitshares.rpc.url),
        'workers': {
            worker_name: {
                'account': '{}'.format(account),
                'buy_distance': 4.0,
                'sell_distance': 4.0,
                'buy_stop_ratio': 10.0,
                'sell_stop_ratio': 10.0,
                'buy_orders': '30-20-10',
                'sell_orders': '10-20-30',
                'center_price_depth': 0.0,
                'external_feed': False,
                'external_price_source': 'null',
                'fee_asset': 'TEST',
                'market': 'QUOTEA/BASEA',
                'module': 'dexbot.strategies.flexible_orders',
                'reset_on_partial_fill': True,
                'partial_fill_threshold': 90.0,
                'reset_on_price_change': False,
                'price_change_threshold': 0.5,
                'center_price_from_last_trade': False,
            }
        },
    }
    return config


@pytest.fixture
def config_other_account(config, base_account, dexbot_worker_name):
    """ Config for other account which simulates foreign trader
    """
    config = copy.deepcopy(config)
    worker_name = dexbot_worker_name
    config['workers'][worker_name]['account'] = base_account()
    return config


@pytest.fixture
def base_worker(bitshares, dexbot_worker_name):
    """ Fixture to create a worker
    """
    workers = []

    def _base_worker(config, worker_name=dexbot_worker_name):
        worker = Strategy(name=worker_name, config=config, bitshares_instance=bitshares)
        worker.min_check_interval = 0
        workers.append(worker)
        return worker

    yield _base_worker
    for worker in workers:
        worker.cancel_all_orders()
        worker.bitshares.txbuffer.clear()
        worker.bitshares.bundle = False


@pytest.fixture
def strategy_worker(base_worker, config):
    """ A worker of strategy to be tested
    """
    worker = base_worker(config)
    return worker


@pytest.fixture
def other_worker(dexbot_worker_name, config_other_account):
    worker = StrategyBase(name=dexbot_worker_name, config=config_other_account)
    yield worker
    worker.cancel_all_orders()
    time.sleep(1.1)


@pytest.fixture
def other_orders(other_worker):
    """ Place some orders from second account to simulate foreign trader
    """
    worker = other_worker
    worker.place_market_buy_order(10, 0.5)
    worker.place_market_sell_order(10, 1.5)
    if float(worker.market.ticker().get('highestBid')) == 0:
        empty_ticker_workaround(worker)
    return worker


def empty_ticker_workaround(worker):
    bid = worker.get_highest_market_buy_order()
    sell_price = bid['price'] / 1.01
    to_sell = bid['quote']['amount'] / 10
    log.debug('Executing empty ticker workaround')
    worker.place_market_sell_order(to_sell, sell_price)
