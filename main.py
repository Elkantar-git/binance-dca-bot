from ast import While
from multiprocessing.connection import wait
from service.binance_service import *
from system.store_order import *
from system.load_data import *
from service.email_service import *
from trades.metrics import *

from collections import defaultdict
from datetime import datetime, time, timedelta
import time
from system.logger import logger
import json
import os.path


# load coins to DCA
coins_to_DCA = load_data('config/coins.yml')['COINS']
# loads local configuration
config = load_data('config/config.yml')

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
        print(coin, last_price)

        sl = min(listPrice) + min(listPrice) * trailing_delta
        print(f"Stop loss price: {sl}")

        if float(last_price) >= sl:
            reset = end_time - now_time
            print(f"Reset time: {reset.total_seconds()}")
            logger.info(f'Last price of {coin} is {last_price} which is greater than {sl}')
            break
        elif now_time >= end_time:
            reset = now_time - now_time
            logger.info(f'Last price of {coin} is {last_price} which is less than {sl}')
            break
    return last_price, reset


def main():
    """
    DCA every x number of days.
    """
    while True:

        # load the order file if it exists
        if os.path.isfile('trades/order.json'):
            order = load_order('trades/order.json')
        else:
            logger.info("No order file found, creating new file")
            order = {}

        pairing = config['TRADE_OPTIONS']['PAIRING']
        qty = config['TRADE_OPTIONS']['QUANTITY']
        frequency = config['TRADE_OPTIONS']['DCA_EVERY']
        test_mode = config['TRADE_OPTIONS']['TEST']
        trailingDelta = config['TRADE_OPTIONS']['TRAILING_DELTA']
        send_notification_flag = config['SEND_NOTIFICATIONS']

        # if not test_mode:
        #     logger.warning("RUNNING IN LIVE MODE! PAUSING FOR 1 MINUTE")
        #     time.sleep(5)

        # DCA each coin
        for coin in coins_to_DCA:
            ath = get_history_ath(coin, pairing)
            all_prices = get_all_order_prices(order)
            avg_dca = calculate_avg_dca(all_prices)
            last_price, reset = trailing_stop(coin, pairing, frequency, trailingDelta)

            # volume = convert_volume(coin+pairing, qty, last_price)

            if avg_dca == {}:
                volume = strategy(ath, float(last_price), qty, float(last_price))
                fvolume = convert_volume(coin+pairing, volume)

            elif avg_dca != {}:
                volume = strategy(ath, float(last_price), qty, float(avg_dca[coin]))
                fvolume = convert_volume(coin+pairing, volume)

            # Tranform volume with strategy
            print(f"last price: {last_price}")
            print(f"avg dca: {avg_dca}")
            print(f"Volume: {volume}")

            try:
                # Run a test trade if true
                if config['TRADE_OPTIONS']['TEST']:
                    if coin not in order:
                        order[coin] = {}
                        order[coin]["orders"] = []

                    # create_test_order(coin+pairing, fvolume)

                    order[coin]["orders"].append({
                                'symbol':coin+pairing,
                                'price':last_price,
                                'volume':fvolume,
                                'time':datetime.timestamp(datetime.now())
                                })
                    logger.info('PLACING TEST ORDER')
                # place a live order if False
                else:
                    if coin not in order:
                        order[coin] = {}
                        order[coin]["orders"] = []

                    order[coin]["orders"].append(create_order(coin+pairing, fvolume))
                    logger.info('PLACING LIVE ORDER')

            except Exception as e:
                logger.info(e)

            else:
                logger.info(f"Order created with {fvolume} on {coin} at {datetime.now()}")
                store_order('trades/order.json', order)

        message = f'DCA complete, bought {coins_to_DCA}. Waiting {reset}.'
        logger.info(message)

        # sends an e-mail if enabled.
        if send_notification_flag:
            send_notification(message)

        # report on DCA performance. Files saved in trades/dca-tracker
        all_prices = get_all_order_prices(order)
        avg_dca = calculate_avg_dca(all_prices)
        dca_history = plot_dca_history(all_prices, avg_dca)

        time.sleep(reset.total_seconds())
        # time.sleep(frequency*86400)


if __name__ == '__main__':
    logger.info('working...')
    main()
