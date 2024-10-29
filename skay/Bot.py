import os
from dotenv import load_dotenv
from time import sleep, strftime
import logging
from skay.ByBit import ByBit
from skay.DataBase import DataBase
from skay.Models import Orders


load_dotenv()

logger = logging.getLogger('SkayBot')
db = DataBase().set_db()


class Bot(ByBit):
    def __init__(self):
        super(Bot, self).__init__()
        self.grid = []
        self.grid_px = 0.0
        self.position_px = 0.0
        self.to_buy = 0
        self.min = float(os.getenv("MIN"))
        self.max = float(os.getenv("MAX"))
        self.percent = float(os.getenv("PERCENT"))

    def check(self):
        if not self.instruments:
            self.getInstruments()
        if not self.balance:
            self.getBalance()
        if self.qty < self.min_qty:
            self.qty = self.min_qty
            logger.debug(f"Qty < MinQty: Qty = {self.qty}")
        self.getKline()
        self.grid_positions()

    def grid_positions(self):
        x = self.min
        while x <= self.max:
            x += (x * self.percent / 100)
            self.grid.append(x)

    def array_grid(self, a, val):
        self.grid_px = round(min([x for x in a if x > val] or [None]), 9)
        return self

    def is_position(self):
        _ord = (db.query(Orders).filter(Orders.side == 'Buy', Orders.px < self.kline['close'], Orders.is_active == True)
                .order_by(Orders.px).first())
        if _ord:
            return _ord
        _ord = db.query(Orders).filter(Orders.side == 'Buy', Orders.grid_px == self.grid_px,
                                       Orders.is_active == True).first()
        if _ord:
            return None
        else:
            return False

    def save_order(self, order, active=True):
        _ord = Orders(
            ordId=order.get('orderId'),
            cTime=strftime('%Y%m%d%H%M%S'),
            sz=order.get('cumExecQty'),
            px=order.get('avgPrice'),
            grid_px=self.grid_px,
            profit=order.get('profit'),
            fee=order.get('cumExecFee'),
            feeCurrency=order.get('marketUnit'),
            side=order.get('side'),
            symbol=order.get('symbol'),
            is_active=active,
            category=order.get('orderType'),
            status=order.get('orderStatus'),
            tag=order.get('orderLinkId')
        )
        db.add(_ord)
        db.commit()
        logger.info(_ord)
        return _ord

    def start(self):
        logger.info("Bot running!")
        while True:
            self.check()
            if len(self.kline) > 0:
                self.array_grid(self.grid, self.kline['close'])
                pos = self.is_position()
                if self.kline['close'] > self.kline['open'] and self.to_buy == 0:
                    self.position_px = self.grid_px
                    self.to_buy = 1
                    logger.info(f"Buy GridPx: {self.grid_px}")
                elif self.kline['close'] < self.kline['open'] and self.to_buy == 1:
                    self.to_buy = 0
                    logger.info(f"Sell GridPx: {self.grid_px}")
                if pos and self.balance[self.baseCoin] > pos.sz and self.order is None:
                    self.sendTicker(side='Sell', qty=round(pos.sz * self.kline['close'], 4), tag=strftime('%Y%m%d%H%M%S'))
                    self.getBalance()
                elif pos and self.balance[self.baseCoin] < pos.sz and self.order is None:
                    self.getBalance()
                    if self.balance[self.quoteCoin] > self.qty * self.kline['close']:
                        self.sendTicker(side='Buy')
                elif (pos is False and self.to_buy == 1 and self.kline['close'] > self.position_px
                      and self.order is None):
                    self.getBalance()
                    if self.balance[self.quoteCoin] > self.qty * self.kline['close']:
                        self.sendTicker(side='Buy', tag=strftime('%Y%m%d%H%M%S'))
                        self.position_px = self.grid_px
                if self.order and self.order['orderId'] == self.orderId:
                    if self.order['orderLinkId'] and self.order['side'] == "Sell":
                        self.save_order(self.order, active=False)
                        self.orderId = None
                        self.order = None
                        pos.cTime = strftime('%Y%m%d%H%M%S')
                        pos.is_active = False
                        db.commit()
                    elif self.order['orderLinkId'] and self.order['side'] == "Buy":
                        self.order['cumExecQty'] = float(self.order['cumExecQty']) - float(self.order['cumExecFee'])
                        self.order['profit'] = float(self.order['avgPrice']) + (float(self.order['avgPrice']) * self.percent / 100)
                        self.save_order(self.order, active=True)
                        self.orderId = None
                        self.order = None
                    else:
                        self.save_order(self.order, active=False)
                        self.orderId = None
                        self.order = None
            sleep(10)