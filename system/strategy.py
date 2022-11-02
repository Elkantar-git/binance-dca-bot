from service.binance_service import *
from datetime import datetime, timedelta


def trailing_stop(coin, pairing, maxDuration, trailingDelta):
    listPrice  = []
    start_time = datetime.now()
    end_time = start_time + timedelta(hours=maxDuration)
    trailing_delta = trailingDelta * 0.0001
    while True:
        # Define the end time to break the loop
        now_time = datetime.now()

        last_price = get_price(coin, pairing)
        listPrice.append(int(float(last_price)))

        sl = min(listPrice) + min(listPrice) * trailing_delta

        if float(last_price) >= sl:
            reset = end_time - now_time
            logger.info(f'Last price of {coin} is {last_price} which is greater than {sl}')
            break
        elif now_time >= end_time:
            reset = now_time - now_time
            logger.info(f'Last price of {coin} is {last_price} which is less than {sl}')
            break
    return last_price, reset

def strategy(ath, last_price, volume, average_dca):

    deltaPrice = last_price / average_dca

    if last_price <= 0.5 * ath:
        if deltaPrice > 1.9:
            deltaPrice = 1.9
        buyAmount = (2 * volume) / deltaPrice
    elif last_price > 0.5 * ath:
        if deltaPrice > 1:
            deltaPrice = 1
        buyAmount = (1 * volume) / deltaPrice
    buyAmount = buyAmount / float(last_price)
    return buyAmount
