import os
import logging
from pybit.unified_trading import HTTP




class ByBit:

    def __init__(self):
        self.logger = logging.getLogger(os.getenv("BOT_NAME"))
        self.logger.info("Bot is started!")
        self.api_key = os.getenv('API_KEY')
        self.api_secret = os.getenv('API_SECRET')
        self.session = None
        self.symbol = os.getenv('SYMBOL')
        self.interval = os.getenv('INTERVAL')
        self.qty = float(os.getenv('QTY'))
        self.min_qty = 0.0
        self.instruments = {}
        self.quoteCoin = None
        self.baseCoin = None
        self.status = None
        self.balance = {}
        self.kline = {}
        self.orderId = None
        self.order = None

    def setSession(self):
        self.session = HTTP(
            testnet=False,
            api_key=self.api_key,
            api_secret=self.api_secret,
        )
        return self

    def getInstruments(self):
        r = self.session.get_instruments_info(
            category="spot",
            symbol=self.symbol,
        )
        data = r['result']['list'][0]
        self.instruments = data
        self.min_qty = float(data['lotSizeFilter']['minOrderQty'])
        self.baseCoin = data['baseCoin']
        self.quoteCoin = data['quoteCoin']
        self.status = data['status']
        return self

    def getBalance(self):
        r = self.session.get_wallet_balance(
            accountType="UNIFIED",
        )
        for i in r['result']['list'][0]['coin']:
            if i['coin'] == self.quoteCoin:
                self.balance[self.quoteCoin] = float(i['walletBalance'])
            elif i['coin'] == self.baseCoin:
                self.balance[self.baseCoin] = float(i['walletBalance'])

    def getKline(self):
        r = self.session.get_kline(
            category="spot",
            symbol=self.symbol,
            interval=self.interval,
            limit=1
        )
        data = r['result']['list'][0]
        self.kline = {"open": float(data[1]), 'close': float(data[4])}
        return self

    def sendTicker(self, qty='', side="Buy", tag=''):
        marketUnit = "quoteCoin"
        if not qty:
            qty = self.qty
        if side == "Sell":
            marketUnit = "baseCoin"
        r = self.session.place_order(
            category="spot",
            symbol=self.symbol,
            side=side,
            orderType="Market",
            qty=qty,
            price=self.kline['close'],
            marketUnit=marketUnit,
            orderLinkId=tag
        )
        self.orderId = r['result']['orderId']
        self.getOrderHistory(r['result']['orderId'])
        return self

    def getOrderHistory(self, ordId=''):
        if not ordId:
            r = self.session.get_order_history(
                category="spot",
                simbol=self.symbol,
                orderId=ordId,
            )
        else:
            r = self.session.get_order_history(
                category="spot",
                simbol=self.symbol,
                limit=50
            )
        data = r['result']['list']
        return data
