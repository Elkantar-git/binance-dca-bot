from ast import While
from multiprocessing.connection import wait
from service.binance_service import *
from system.strategy import *
from system.store_order import *
from system.load_data import *
from service.email_service import *
from trades.metrics import *

from collections import defaultdict
from datetime import datetime, time
import time
from system.logger import logger
import json
import os.path


# load coins to DCA
coins_to_DCA = load_data('config/coins.yml')['COINS']
# loads local configuration
config = load_data('config/config.yml')

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

        # load the config file
        pairing = config['TRADE_OPTIONS']['PAIRING']
        qty = config['TRADE_OPTIONS']['QUANTITY']
        frequency = config['TRADE_OPTIONS']['DCA_EVERY']
        test_mode = config['TRADE_OPTIONS']['TEST']
        trailingDelta = config['TRADE_OPTIONS']['TRAILING_DELTA']
        send_notification_flag = config['SEND_NOTIFICATIONS']

        if not test_mode:
            logger.warning("RUNNING IN LIVE MODE!")

        # DCA each coin
        for coin in coins_to_DCA:
            ath = get_history_ath(coin, pairing)
            all_prices = get_all_order_prices(order)
            avg_dca = calculate_avg_dca(all_prices)

            last_price, reset = trailing_stop(coin, pairing, frequency, trailingDelta)

            if avg_dca == {}:
                volume = strategy(ath, float(last_price), qty, float(last_price))
                fvolume = convert_volume(coin+pairing, volume)

            elif avg_dca != {}:
                volume = strategy(ath, float(last_price), qty, float(avg_dca[coin]))
                fvolume = convert_volume(coin+pairing, volume)

            try:
                # run a test trade if true
                if config['TRADE_OPTIONS']['TEST']:
                    if coin not in order:
                        order[coin] = {}
                        order[coin]["orders"] = []

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

            # save the order file
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

        # wait for the next DCA
        time.sleep(reset.total_seconds())


if __name__ == '__main__':
    logger.info('working...')
    main()
