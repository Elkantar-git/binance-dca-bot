from system.logger import logger
import pandas as pd

from auth.binance_auth import *
from binance.enums import *

client = load_binance_creds('auth/auth.yml')

def get_price(coin, pairing):
     return client.get_ticker(symbol=coin+pairing)['lastPrice']

def get_history_ath(coin, pairing):
    pairName = coin + pairing
    startDate = "01 january 2017"
    timeInterval = Client.KLINE_INTERVAL_1WEEK

    # -- Load all price data from binance API --
    klinesT = client.get_historical_klines(pairName, timeInterval, startDate)

    # -- Define your dataset --
    df = pd.DataFrame(klinesT, columns = ['timestamp', 'open', 'high', 'low', 'close', 'volume', 'close_time', 'quote_av', 'trades', 'tb_base_av', 'tb_quote_av', 'ignore' ])
    df['close'] = pd.to_numeric(df['close'])
    df['high'] = pd.to_numeric(df['high'])
    df['low'] = pd.to_numeric(df['low'])
    df['open'] = pd.to_numeric(df['open'])

    # -- Set the date to index --
    df = df.set_index(df['timestamp'])
    df.index = pd.to_datetime(df.index, unit='ms')
    del df['timestamp']

    print("Data loaded 100%")

    # -- Drop all columns we do not need --
    df.drop(columns=df.columns.difference(['open','high','low','close','volume']), inplace=True)

    # -- Indicators, you can edit every value --
    df['LAST_ATH'] = df['close'].cummax()
    ath = df['LAST_ATH'].iloc[-1]
    return ath


def convert_volume(coin, quantity):
    """Converts the volume given in QUANTITY from USDT to the each coin's volume"""

    try:
        info = client.get_symbol_info(coin)
        step_size = info['filters'][2]['stepSize']
        lot_size = {coin:step_size.index('1') - 1}

        if lot_size[coin] < 0:
            lot_size[coin] = 0

    except Exception as e:
        logger.debug(f'Converted {quantity} {coin} by setting lot size to 0')
        lot_size = {coin:0}

    # calculate the volume in coin from QUANTITY in USDT (default)
    # volume = float(quantity / float(last_price))
    volume = quantity

    # define the volume with the correct step size
    if coin not in lot_size:
        volume = float('{:.1f}'.format(volume))

    else:
        # if lot size has 0 decimal points, make the volume an integer
        if lot_size[coin] == 0:
            volume = int(volume)
        else:
            # volume = float('{:.{}f}'.format(volume, lot_size[coin]))
            volume = float('{:.{}f}'.format(volume, lot_size[coin]))

    logger.debug(f'Sucessfully converted {quantity} {coin} to {volume} in trading coin')
    return volume

def strategy(ath, last_price, volume, average_dca):

    deltaPrice = last_price / average_dca

    # BUY
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

def create_order(coin, amount):
    """
    Creates simple buy order and returns the order
    """
    # return client.order_limit_buy(
    #     symbol=coin,
    #     quantity=amount,
    #     price=price)

    return client.order_market_buy(
        symbol=coin,
        quantity=amount)

def create_test_order(coin, amount):
    """
    Creates simple buy order and returns the order
    """
    
    return client.create_test_order(
        symbol=coin,
        side=SIDE_BUY,
        type=ORDER_TYPE_MARKET,
        quantity=amount)
