from dexbot.strategies.config_parts.base_config import BaseConfig, ConfigElement


class FlexibleConfig(BaseConfig):
    @classmethod
    def configure(cls, return_base_config=True):
        # External exchanges used to calculate center price
        EXCHANGES = [
            # ('none', 'None. Use Manual or Bitshares DEX Price (default)'),
            ('gecko', 'Coingecko'),
            ('waves', 'Waves DEX'),
            ('kraken', 'Kraken'),
            ('bitfinex', 'Bitfinex'),
            ('gdax', 'Gdax'),
            ('binance', 'Binance'),
        ]

        config = [
            ConfigElement(
                'buy_distance',
                'float',
                2,
                'Buy distance',
                'The percentage difference between buy order and center price',
                (0, 100, 2, '%'),
            ),
            ConfigElement(
                'sell_distance',
                'float',
                2,
                'Sell distance',
                'The percentage difference between sell order and center price',
                (0, 100, 2, '%'),
            ),
            ConfigElement(
                'buy_orders',
                'string',
                '3-2-1',
                'Buy orders',
                'Buy orders in relative amounts, you can set any number of orders. Orders are from far end towards'
                ' center',
                r'[0-9\.-]+',
            ),
            ConfigElement(
                'sell_orders',
                'string',
                '1-2-3',
                'Sell orders',
                'Sell orders in relative amounts, you can set any number of orders. Orders are from center towards'
                ' far end',
                r'[0-9\.-]+',
            ),
            ConfigElement(
                'buy_increment_step',
                'float',
                2,
                'Buy orders increment step',
                'Increment % between orders on the buy side',
                (0, 100, 2, '%'),
            ),
            ConfigElement(
                'sell_increment_step',
                'float',
                2,
                'Sell orders increment step',
                'Increment % between orders on the sell side',
                (0, 100, 2, '%'),
            ),
            ConfigElement(
                'buy_stop_ratio',
                'float',
                50,
                'Buy stop ratio',
                'Stop placing buy orders if BASE asset value becomes less than this ratio, percentage 0-100',
                (0, 100, 2, '%'),
            ),
            ConfigElement(
                'sell_stop_ratio',
                'float',
                50,
                'Sell stop ratio',
                'Stop placing sell orders if QUOTE asset value becomes less than this ratio, percentage 0-100',
                (0, 100, 2, '%'),
            ),
            ConfigElement(
                'external_feed',
                'bool',
                False,
                'External price feed',
                'Use external reference price instead of center price acquired from the market',
                None,
            ),
            ConfigElement(
                'external_price_source',
                'choice',
                EXCHANGES[0][0],
                'External price source',
                'The bot will try to get price information from this source',
                EXCHANGES,
            ),
            ConfigElement(
                'center_price_depth',
                'float',
                0,
                'Center price depth',
                'Cumulative quote amount from which depth center price will be measured',
                (0.00000000, 1000000000, 8, ''),
            ),
            ConfigElement(
                'center_price_from_last_trade',
                'bool',
                False,
                'Last trade price as new center price',
                'This will make orders move by half the spread at every fill',
                None,
            ),
            ConfigElement(
                'reset_on_partial_fill',
                'bool',
                True,
                'Reset orders on partial fill',
                'Reset orders when buy or sell order is partially filled',
                None,
            ),
            ConfigElement(
                'partial_fill_threshold',
                'float',
                90,
                'Fill threshold',
                'Order fill threshold to reset orders',
                (0, 100, 2, '%'),
            ),
            ConfigElement(
                'reset_on_price_change',
                'bool',
                False,
                'Reset orders on center price change',
                'Reset orders when center price is changed more than threshold',
                None,
            ),
            ConfigElement(
                'price_change_threshold',
                'float',
                0.5,
                'Price change threshold',
                'Define center price threshold to react on, percentage (consider using 1/10 of your spread)',
                (0, 100, 0.5, '%'),
            ),
        ]

        return BaseConfig.configure(return_base_config) + config

    @classmethod
    def configure_details(cls, include_default_tabs=True):
        return BaseConfig.configure_details(include_default_tabs) + []
