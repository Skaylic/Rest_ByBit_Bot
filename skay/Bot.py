import os
from dotenv import load_dotenv
from time import strftime, sleep
from skay.ByBit import ByBit
from skay.DataBase import DataBase
from skay.Models import Orders


load_dotenv()
db = DataBase().set_db()


class Bot(ByBit):
    def __init__(self):
        super(Bot, self).__init__()
        self.min = float(os.getenv("MIN"))
        self.max = float(os.getenv("MAX"))
        self.percent = float(os.getenv("PERCENT"))
        self.grid = []
        self.grid_px = 0.0
        self.position_px = 0.0
        self.to_buy = 0

    def grid_positions(self):
        x = self.min
        while x <= self.max:
            x += (x * self.percent / 100)
            self.grid.append(x)

    def array_grid(self, a, val):
        self.grid_px = round(min([x for x in a if x > val] or [None]), 9)
        return self

    def is_position(self):
        _ord = (db.query(Orders).filter(Orders.side == 'Buy', Orders.profit < self.kline['close'], Orders.is_active == True)
                .order_by(Orders.px).first())
        if _ord:
            return _ord
        _ord = db.query(Orders).filter(Orders.side == 'Buy', Orders.grid_px == self.grid_px,
                                       Orders.is_active == True).first()
        if _ord:
            return None
        else:
            return False

    def save_order(self, order, sz=0, active=True):
        if sz != 0:
            order['qty'] = sz
        _ord = Orders(
            ordId = order.get('orderId'),
            cTime = strftime('%Y%m%d%H%M%S'),
            sz = order.get('qty'),
            px = order.get('avgPrice'),
            profit = order.get('profit'),
            fee = order.get('cumExecFee'),
            grid_px = order.get('grid_px'),
            side = order.get('side'),
            status = order.get('orderStatus'),
            symbol = order.get('symbol'),
            orderType = order.get('orderType'),
            marketUnit = order.get('marketUnit'),
            orderLinkId = order.get('orderLinkId'),
            is_active = active,
        )
        db.add(_ord)
        db.commit()
        self.logger.info(_ord)
        return _ord

    def check(self):
        if not self.instruments:
            self.getInstruments()
        if not self.balance:
            self.getBalance()
        self.grid_positions()

    async def run(self):
        self.logger.info("Bot is running!")
        while True:
            self.check()
            if len(self.kline) > 0:
                self.array_grid(self.grid, float(self.kline['close']))
                pos = self.is_position()
                if float(self.kline['close']) > float(self.kline['open']) and self.to_buy == 0:
                    self.position_px = self.grid_px
                    self.to_buy = 1
                elif float(self.kline['close']) < float(self.kline['open']) and self.to_buy == 1:
                    self.to_buy = 0
                if pos and self.balance[self.baseCoin] > pos.sz and self.order is None:
                    self.sendTicker(round(pos.sz * float(self.kline['close']), 4), 'Sell', strftime('%Y%m%d%H%M%S'))
                    self.getBalance()
                elif pos and self.balance[self.baseCoin] < pos.sz and self.order is None:
                    self.getBalance()
                    if self.balance[self.quoteCoin] > self.qty * float(self.kline['close']):
                        self.sendTicker(self.qty, 'Buy')
                elif (pos is False and self.to_buy == 1 and float(self.kline['close']) > self.position_px
                      and self.order is None):
                    self.getBalance()
                    if self.balance[self.quoteCoin] > self.qty * float(self.kline['close']):
                        self.sendTicker(self.qty, 'Buy', strftime('%Y%m%d%H%M%S'))
                        self.position_px = self.grid_px
                if self.order and self.order['orderId'] == self.orderId:
                    if self.order['orderLinkId'] and self.order['side'] == "Sell":
                        self.save_order(self.order, active=False)
                        pos.cTime = strftime('%Y%m%d%H%M%S')
                        pos.is_active = False
                        db.commit()
                        self.order = None
                    elif self.order['orderLinkId'] and self.order['side'] == "Buy":
                        self.order['qty'] = float(self.order['qty']) - float(self.order['cumExecFee'])
                        self.order['profit'] = float(self.order['avgPrice']) + (
                                    float(self.order['avgPrice']) * self.percent / 100)
                        self.order['grid_px'] = self.grid_px
                        self.save_order(self.order, active=True)
                        self.order = None
                    else:
                        self.save_order(self.order, active=False)
                        self.order = None
            sleep(10)
