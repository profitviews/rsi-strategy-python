import os
import socketio

sio = socketio.Client()

class Strategy(socketio.ClientNamespace):

    def __init__(self):
        super().__init__()

    def on_connected(self, data):
        sio.emit('subscribe', ['trade:bitmex:XBTUSD'])

    def on_trade(self, data):
        print(data)

sio.register_namespace(Strategy())
sio.connect(f'https://markets.profitview.net?api_key={os.environ["PV_KEY"]}', transports=['websocket'])