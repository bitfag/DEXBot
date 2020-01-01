# Python imports
from datetime import datetime, timedelta
from functools import reduce

# Project imports
from dexbot.strategies.base import StrategyBase
from dexbot.strategies.relative_orders import Strategy as RelativeStrategy
from dexbot.strategies.config_parts.flexible_config import FlexibleConfig


STRATEGY_NAME = 'Flexible Orders'


class Strategy(RelativeStrategy):
    """
    """

    @classmethod
    def configure(cls, return_base_config=True):
        return FlexibleConfig.configure(return_base_config)

    @classmethod
    def configure_details(cls, include_default_tabs=True):
        return FlexibleConfig.configure_details(include_default_tabs)

    def __init__(self, *args, **kwargs):
        # Initializes StrategyBase class
        StrategyBase.__init__(self, *args, **kwargs)

        self.log.info("Initializing {}...".format(STRATEGY_NAME))

        # Tick counter
        self.counter = 0

        # Define Callbacks
        self.onMarketUpdate += self.maintain_strategy
        self.ontick += self.tick

        self.error_ontick = self.error
        self.error_onMarketUpdate = self.error
        self.error_onAccount = self.error

        # Get view
        self.view = kwargs.get('view')
        self.worker_name = kwargs.get('name')

        # Worker params
        self.buy_distance = self.worker.get('buy_distance', 3) / 100
        self.sell_distance = self.worker.get('sell_distance', 3) / 100
        self.buy_orders = self.worker.get('buy_orders', '6-4')
        self.sell_orders = self.worker.get('sell_orders', '4-6')
        self.buy_increment_step = self.worker.get('buy_increment_step', 2) / 100
        self.sell_increment_step = self.worker.get('sell_increment_step', 2) / 100
        self.buy_stop_ratio = self.worker.get('buy_stop_ratio', 50) / 100
        self.sell_stop_ratio = self.worker.get('sell_stop_ratio', 50) / 100
        self.external_feed = self.worker.get('external_feed', False)
        self.external_price_source = self.worker.get('external_price_source', 'gecko')
        self.center_price_depth = self.worker.get('center_price_depth', 0)
        self.cp_from_last_trade = self.worker.get('center_price_from_last_trade', False)
        self.is_reset_on_partial_fill = self.worker.get('reset_on_partial_fill', True)
        self.partial_fill_threshold = self.worker.get('partial_fill_threshold', 90) / 100
        self.is_reset_on_price_change = self.worker.get('reset_on_price_change', False)
        self.price_change_threshold = self.worker.get('price_change_threshold', 0.5) / 100
        # Our center price is always dynamic
        self.is_center_price_dynamic = True

        self.buy_orders_percentages = self.validate_orders(self.buy_orders)
        self.sell_orders_percentages = self.validate_orders(self.sell_orders)
        self.num_orders_expected = len(self.buy_orders_percentages) + len(self.sell_orders_percentages)

        # Set last check in the past to get immediate check at startup
        self.last_check = datetime(2000, 1, 1)
        self.min_check_interval = 5

        if self.view:
            self.update_gui_slider()

        self.log.info("{} initialized.".format(STRATEGY_NAME))

    @staticmethod
    def validate_orders(orders):
        """ Check that orders percentages string is valid and return orders percentage list

            :param str orders: orders in format '30-20-10' where each number is a percentage
            :return: list of orders percentages in format [0.30, 0.20, 0.10]
        """
        orders = orders.split('-')
        orders = [float(o) / 100 for o in orders]

        pct_sum = reduce(lambda x, y: x + y, orders)
        if pct_sum > 1:
            raise ValueError('Orders percentages should not exceed 100')

        return orders

    def maintain_strategy(self, *args):
        """ Strategy main logic
        """
        delta = datetime.now() - self.last_check
        # Only allow to run when minimal time passed
        if delta < timedelta(seconds=self.min_check_interval):
            return

        orders = self.fetch_orders()
        # dict -> list
        try:
            orders = [order for id_, order in orders.items()]
        except AttributeError:
            # orders is None
            self.place_orders()
            self['bootstrapped'] = True
            return

        # Is orders number correct?
        if len(orders) < self.num_orders_expected:
            self.place_orders()
            self['bootstrapped'] = True
            return

        # Orders were touched/filled? Replace orders
        if self.is_reset_on_partial_fill:
            # Check only closest orders (optimization)
            orders_to_check = self.filter_closest_orders(orders)
            refreshed_orders = [self.get_order(order['id']) for order in orders_to_check]
            for order in refreshed_orders:
                if not order or self.is_partially_filled(order, threshold=self.partial_fill_threshold):
                    # Order is None or partially filled
                    self['bootstrapped'] = True
                    self.place_orders()
                    return

        # Center price changed too much? Replace orders
        if self.is_reset_on_price_change:
            old_center_price = self['center_price']
            current_center_price = self.calc_center_price()
            need_update = self.check_cp_shift_is_too_big(old_center_price, current_center_price)
            if need_update:
                self.place_orders()
                return

        self.last_check = datetime.now()

    def calc_center_price(self):
        """ Calculate center price using various sources depending on settings
        """
        if self.external_feed:
            try:
                center_price = self.get_external_market_center_price(self.external_price_source)
                self.log.info('Using center price from external source: {:.8f}'.format(center_price))
            except TypeError:
                self.log.warning('Failed to obtain center price from external source')
                raise
        elif self.cp_from_last_trade and self['bootstrapped']:
            try:
                center_price = self.get_own_last_trade()['price']
                self.log.info('Using center price from last trade: {:.8f}'.format(center_price))
            except TypeError:
                try:
                    center_price = self.get_market_center_price()
                    self.log.info(
                        'Using market center price (failed to obtain last trade): {:.8f}'.format(center_price)
                    )
                except TypeError:
                    self.log.warning('Failed to obtain center price from last trade and from market')
                    raise
        else:
            center_price = self.get_market_center_price(quote_amount=self.center_price_depth)
            self.log.info('Using market center price: {:.8f}'.format(center_price))

        return center_price

    def calc_ratios(self, price):
        """ Calculate relative ratio of BASE and QUOTE at given price

            :param float price:
            :return: tuple with base and quote ratio
        """
        base_balance = self.balance(self.market['base'])['amount']
        quote_balance = self.balance(self.market['quote'])['amount']
        quote_value_in_base = quote_balance * price
        sum_value = base_balance + quote_value_in_base
        base_ratio = base_balance / sum_value
        quote_ratio = 1 - base_ratio

        return base_ratio, quote_ratio

    def place_orders(self):
        """ Cancel old orders and place a new ones
        """
        try:
            center_price = self.calc_center_price()
        except TypeError:
            self.log.error('Failed to obtain center price')
            self.cancel_all_orders()
            self.clear_orders()
            return

        # Cancelling all orders AFTER CP calculation, this prevents immediate CP shift after placing orders
        self.cancel_all_orders()
        self.clear_orders()

        # Calc orders prices and amounts
        buy_price = center_price / (1 + self.buy_distance)
        sell_price = center_price * (1 + self.sell_distance)

        buy_prices = [buy_price]
        sell_prices = [sell_price]

        for _ in range(0, len(self.buy_orders_percentages) - 1):
            buy_price /= 1 + self.buy_increment_step
            buy_prices.append(buy_price)

        for _ in range(0, len(self.sell_orders_percentages) - 1):
            sell_price *= 1 + self.sell_increment_step
            sell_prices.append(sell_price)

        self.log.debug('Will place buy orders at prices: %s', buy_prices)
        self.log.debug('Will place sell orders at prices: %s', sell_prices)

        # Check for stop ratio
        base_ratio, quote_ratio = self.calc_ratios(center_price)
        if base_ratio < self.buy_stop_ratio:
            self.log.info(
                'Not placing buy orders, buy ratio limit reached: {:.2%} < {:.2%}'.format(
                    base_ratio, self.buy_stop_ratio
                )
            )
            buy_prices = []
        if quote_ratio < self.sell_stop_ratio:
            self.log.info(
                'Not placing sell orders, sell ratio limit reached: {:.2%} < {:.2%}'.format(
                    quote_ratio, self.sell_stop_ratio
                )
            )
            sell_prices = []

        # Calc orders
        # Arrange prices from far end towards center
        buy_prices = list(reversed(buy_prices))
        for price, percentage in zip(buy_prices, self.buy_orders_percentages):
            base_amount = percentage * self.balance(self.market['base'])['amount']
            quote_amount = base_amount / price
            if quote_amount == 0:
                break
            # TODO: refactor place_market_xxx_order to raise InsufficientFunds exception instead of disabling worker
            order = self.place_market_buy_order(quote_amount, price)
            # TODO: refactor place_market_xxx_order to return orderid even if order immediately filled
            try:
                self.save_order(order)
            except KeyError:
                pass

        for price, percentage in zip(sell_prices, self.sell_orders_percentages):
            quote_amount = percentage * self.balance(self.market['quote'])['amount']
            if quote_amount == 0:
                break
            order = self.place_market_sell_order(quote_amount, price)
            try:
                self.save_order(order)
            except KeyError:
                pass

        # Store CP
        if not self.cp_from_last_trade or not self.external_feed:
            # Refresh CP if using orderbook orders to calculate CP
            center_price = self.calc_center_price()
        self['center_price'] = center_price

    def filter_closest_orders(self, orders):
        """ Take list of orders and return only closest to center orders

            :param list orders: list of bitshares.price.Order objects
            :return: list with closest buy and sell orders
        """
        buy_orders = self.filter_buy_orders(orders, sort='DESC')
        sell_orders = self.filter_sell_orders(orders, sort='DESC', invert=False)
        result = [buy_orders[0], sell_orders[0]]
        return result

    def check_cp_shift_is_too_big(self, old_center_price, current_center_price):
        """ Check that center price change is more than threshold

            :param float old_center_price: previous center price
            :param float current_center_price: new center price
            :return: True = center price changed more than threshold
        """
        diff = (current_center_price - old_center_price) / current_center_price
        if abs(diff) >= self.price_change_threshold:
            self.log.debug('Center price changed, updating orders. Diff: {:.2%}'.format(diff))
            return True

        return False

    def error(self, *args, **kwargs):
        """ Defines what happens when error occurs """
        self.disabled = True

    def tick(self, d):
        """ Ticks come in on every block """
        if self.counter % 4 == 0:
            self.maintain_strategy()
        self.counter += 1
