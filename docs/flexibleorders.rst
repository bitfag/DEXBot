***************
Flexible Orders
***************

How it works
============

This is a market-making strategy with relative nature. User can specify order distances (bid, ask) from center price.
Order quantities are always set in a percentage form. Multiple orders with defined price increments are supported. User
is able to control portfolio ratio, for example stop placing buy orders if BASE value becomes less than 80% of the
portfolio value. Strategy can take center price from external source, or from own last trade, or from orderbook
condition.

On start, the strategy calculates current center price and places orders according to settings. If
`reset_on_price_change` is set to `True`, the strategy constantly re-evaluates center price and portfolio ratio and
moves orders accordingly. Otherwise, orders are replaced only after being filled (fully or partially).

Configuration parameters
========================

* `buy_distance`, `sell_distance`: defines closest order distance from center price. Independent configuration gives you
  an ability to set orders asymmetrically
* `buy_orders`: define buy orders number and amounts in following form: `30-20-10`. This notation means 3 orders will be
  placed, using 30%, 20%, and 10% of the BASE asset amount. Orders direction is from far end towards center.
* `sell_orders`: sell orders amounts similarly to `buy_orders`, exept orders direction is from center to far end! This
  makes sense if you'll look at orders like this: `30-20-10 <center> 2-3-4`.
* `buy_increment_step`, `sell_increment_step`: increment % between orders. That is, you can set different increment for
  buy and sell orders
* `buy_stop_ratio`: Stop placing buy orders if BASE asset value becomes less than this ratio, percentage 0-100. You can
  think of this setting as a "kill-switch" to stop buying an asset if position becomes too huge.
* `sell_stop_ratio`: Stop placing sell orders if QUOTE asset value becomes less than this ratio, percentage 0-100. Same
  as buy stop, but for QUOTE asset. With this setting you can prevent "sold out" condition to make sure you have some
  QUOTE if price goes up
* `external_feed`: if True, use external center price
* `external_price_source`: set any ccxt-supported exchange id here, like "binance", "bittrex" and so on
* `external_market`: external market can use different ticker, here you can specify what exact symbols you want to use.
  Example: bitshares market is RUDEX.GOLOS/RUDEX.BTC, external market would be GOL/BTC
* `center_price_depth`: Cumulative quote amount from which depth center price will be measured. This prevents dust
  orders from influencing center price
* `center_price_from_last_trade`: Own last trade price wil be used as new center price
* `reset_on_partial_fill`: Reset orders when buy or sell order is partially filled
* `reset_on_price_change`: Reset orders when center price is changed more than threshold
* `price_change_threshold`: Define center price threshold to react on, percentage (consider using 1/10 of your spread)

Configuration examples
======================

Trading on a downtrend
----------------------

When market is in a downtrend, you may wish to set buy orders deep, and sell orders close. Also, you can limit your
position by keeping BASE ratio high. Further, you want to sell QUOTE as soon as possible:

.. code-block:: yaml

    buy_distance: 4
    sell_distance: 1
    buy_orders: 3-2-1
    sell_orders: 40-30-30
    buy_stop_ratio: 90
    sell_stop_ratio: 0


Trading Bitcoin and waiting for "to the moon"
---------------------------------------------

Say, your expectation is BTC going moon. So your goal is to keep most of your BTC, doing partial sells on highs and
re-bying on price drops. So, you're set high sell stop ratio and low buy stop ratio. Order sizes are also set
accordingly: sell small amounts and try to re-buy more agressively.

.. code-block:: yaml

    buy_distance: 2
    sell_distance: 2
    buy_orders: 30-20-15
    sell_orders: 2-4-6
    buy_stop_ratio: 3
    sell_stop_ratio: 80
