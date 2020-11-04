import ccxt
import datetime
import dateutil.parser
import numpy as np
import os
import pytz
import socketio
import threading

from bisect import bisect_left
from scipy.optimize import newton
from scipy.interpolate import interp1d

from talib import RSI

sio = socketio.Client()

API = ccxt.bitmex({
    'apiKey': os.environ['BX_KEY'],
    'secret': os.environ['BX_SECRET']
})


class Strategy(socketio.ClientNamespace):

    def __init__(self):
        super().__init__()
        self.step = 60000
        self.failures = 0
        self.connected = False
        self.trade = {}
        self.syms = {'XBTUSD': (500, .5)}
        self.candle = {sym: {} for sym in self.syms}
        self.quotes = {sym: {'B': np.nan, 'S': np.nan} for sym in self.syms}
        self.fetch_candles()
        self.update_signal()

    @property
    def now(self):
        return datetime.datetime.utcnow().replace(tzinfo=pytz.utc)

    def minute_bin(self, value):
        return value + self.step - (value % self.step)

    def iso_to_unix(self, ts):
        return round(1000 * dateutil.parser.parse(ts).timestamp())

    def on_connected(self, data):
        sio.emit('subscribe', [f'trade:bitmex:{sym}' for sym in self.syms])

    def on_snap(self, data):
        for t in data.get('trade', []):
            sym, time, price = t['sym'], t['time'], t['price']
            self.candle[sym][time] = price
            self.trade[sym] = price

        self.connected = True

    def on_trade(self, data):
        sym, time, price = data['sym'], data['time'], data['price']
        self.candle[sym][time] = price
        self.trade[sym] = price

    def fetch_candles(self):
        for sym in self.syms:
            candles = API.publicGetTradeBucketed(params={
                'binSize': '1m',
                'symbol': sym,
                'count': 500,
                'reverse': True,
                'partial': True
            })
            self.candle[sym] = {self.iso_to_unix(c['timestamp']): c['close'] for c in candles}

    def update_orders(self):
        API.privateDeleteOrderAll()
        open_risk = {x['symbol']: x['currentQty'] for x in API.privateGetPosition()}

        for sym, (max_risk, tick_size) in self.syms.items():
            orders = []
            risk = open_risk.get(sym, 0)
            last = self.trade[sym]
            quotes = self.quotes[sym]

            if risk > 0:
                bsize = max_risk - risk
                asize = -max_risk
            elif risk < 0:
                bsize = max_risk
                asize = -(max_risk - abs(risk))
            else:
                bsize = max_risk
                asize = -max_risk

            if bsize != 0:
                orders.append((min(last - tick_size, quotes['B']), bsize))

            if asize != 0:
                orders.append((max(last + tick_size, quotes['S']), asize))

            print(sym, orders)
            API.privatePostOrderBulk({
                'orders': [{
                    'symbol': sym,
                    'price': price,
                    'orderQty': size,
                    'ordType': 'Limit',
                    'execInst': 'ParticipateDoNotInitiate'
                } for price, size in orders]
            })

    def update_signal(self):
        if self.failures > 5:
            print('too many failures, stopping algo')
            return

        minute = self.minute_bin(round(self.now.timestamp() * 1000))

        for sym, (max_risk, tick_size) in self.syms.items():
            if minute - self.step not in self.candle[sym]:
                self.candle[sym][minute - self.step] = self.candle[sym][minute - 2 * self.step]

            returns = np.linspace(-.02, .02, 100)
            times, closes = zip(*sorted(self.candle[sym].items()))
            rsi_data = [self.hypo_rsi(closes, r) for r in returns]

            func = interp1d(rsi_data, returns, kind='cubic')

            try:
                bid_return = float(func(30))
                ask_return = float(func(70))
                bid = tick_size * round(closes[-1] * (1 + bid_return) / tick_size)
                ask = tick_size * round(closes[-1] * (1 + ask_return) / tick_size)
                self.quotes[sym]['B'] = bid
                self.quotes[sym]['S'] = ask

            except Exception as e:
                print(f'failure to calculate ladder for {sym}: {e}')

        if self.connected:
            try:
                self.update_orders()

            except Exception as e:
                self.failures += 1
                print(f'order update failed: {e}')
                threading.Timer(5, self.update_signal).start()
                return

        threading.Timer(61 - self.now.second, self.update_signal).start()

    def hypo_rsi(self, closes, ret):
        return RSI(np.append(closes, [closes[-1] * (1 + ret)]))[-1]


sio.register_namespace(Strategy())
sio.connect(f'https://markets.profitview.net?api_key={os.environ["PV_KEY"]}', transports=['websocket'])