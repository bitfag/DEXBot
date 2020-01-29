import logging

log = logging.getLogger("dexbot")


def empty_ticker_workaround(worker):
    bid = worker.get_highest_market_buy_order()
    sell_price = bid['price'] / 1.01
    to_sell = bid['quote']['amount'] / 10
    log.debug('Executing empty ticker workaround')
    worker.place_market_sell_order(to_sell, sell_price)
