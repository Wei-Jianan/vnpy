from vnpy.app.cta_strategy import (
    CtaTemplate,
    StopOrder,
    TickData,
    BarData,
    TradeData,
    OrderData,
    BarGenerator,
    ArrayManager,
)
import time, datetime
import math

class AsStrategy(CtaTemplate):

    k = 0.1
    sigma = 1
    gamma = 0.5
    fixed_size = 1000

    delta_t = 0
    r = 0
    spread = 0
    bid_price = 0
    ask_price = 0
    last_bid_price = 0
    last_ask_price = 0

    milli_second_per_day = 86400000
    cover_only_milli = 1000 * 60 * 15
    cover_only_request = 400
    vt_orderids = []
    last_tick = None

    parameters = [
        "k",
        "sigma",
        "gamma",
        "fixed_size",
        "cover_only_milli",
        "cover_only_request",
    ]

    variables = [
        "delta_t",
        "r",
        "spread",
        "bid_price",
        "ask_price"
    ]

    def __init__(self, cta_engine, strategy_name, vt_symbol, setting):
        """"""
        super().__init__(cta_engine, strategy_name, vt_symbol, setting)
        self.request_counter = 0
        self.last_now = datetime.datetime.now()
        
    
    def on_init(self):
        """
        Callback when strategy is inited.
        """
        self.write_log("策略初始化")
        self.load_tick(0)
        print("k: "+str(self.k))
        print("gamma: "+ str(self.gamma))
        print("sigma: "+ str(self.sigma))
        print("request limit: "+ str(self.cover_only_request))

    def on_start(self):
        """
        Callback when strategy is started.
        """
        self.write_log("策略start")



    def on_stop(self):
        """
        Callback when strategy is stopped.
        """
        self.write_log("策略停止")

    @classmethod
    def remain_milli_today(cls, now):
        milli_sec_now = int(round(now.timestamp() * 1000))
        zeroToday = now - datetime.timedelta(hours=now.hour, minutes=now.minute, seconds=now.second, microseconds=now.microsecond)
        milli_sec_endtime = int(round(zeroToday.timestamp()*1000)) + cls.milli_second_per_day
        remain_time = milli_sec_endtime - milli_sec_now
        return remain_time
   
    def new_minute(self, now):
        
        if now.minute != self.last_now.minute:
            return True
        return False


    def force_cover(self):
        pass

    def out_of_request_limit(self):
        if self.request_counter > self.cover_only_request:

            # print("out of request!! called: {}, limit: {}".format(self.request_counter, self.cover_only_request))
            return True
        return False
    
    def end_of_day(self, remain_time):
        if remain_time < self.cover_only_milli:
            return True
        return False
        


    def on_tick(self,tick: TickData):
        """
        Callback of new tick data update.
        """
        #get position: self.pos
        #calculate time left (T-t) delta_t 
        now = tick.datetime
        if self.new_minute(now):
            self.request_counter = 0
        

        self.last_now = now
        
        remain_time = self.remain_milli_today(now)

        if self.end_of_day(remain_time) or self.out_of_request_limit():
            cover_only = True
        else:
            cover_only = False

        self.delta_t = remain_time / self.milli_second_per_day

        #calculate indifferent price r(s,t) = s - q * gamma * sigma^2 * delta_t
        self.r = (tick.ask_price_1 + tick.bid_price_1)/2 - self.pos * self.gamma * self.sigma**2 * self.delta_t
        #calculate spread, spread = 2 / gamma * ln(1 + gamma/k)
        self.spread = self.gamma * self.sigma**2 * self.delta_t + 2 / self.gamma * math.log(1 + self.gamma / self.k)
        #calculate ask, ask_price = r + spread/2
        #calculate bid, bid_price = r - spread/2
        self.ask_price = self.round_up(self.r + self.spread/2, self.get_pricetick)
        self.bid_price = self.round_down(self.r - self.spread/2, self.get_pricetick)

        #如果上个tick提交的委托没成交
        if self.vt_orderids:
            #新tick的bid ask和上个tick不变，返回
            if(self.bid_price == self.last_bid_price and self.ask_price == self.last_ask_price):
                return
            #新tick的bid ask发生变化，撤旧单，发新单
            else:
                for orderid in self.vt_orderids:
                    self.cancel_remove_order(orderid)
                self.send_new_order(cover_only=cover_only)
        else:
            self.send_new_order(cover_only=cover_only)

        self.last_ask_price = self.ask_price
        self.last_bid_price = self.bid_price
        self.write_log("{}\n delta_t: {}, spread: {}, r: {}, request counter: {}".format(tick, 
                          self.delta_t, self.spread, self.r, self.request_counter))
            # self.last_tick = tick
    @staticmethod
    def round_up(price, price_tick):
        reminder = price % price_tick 
        rounded = x + price_tick - reminder
        return rounded

    @staticmethod
    def round_down(price, price_tick):
        rounded = price //  price_tick  * price_tick
        return rounded




    def on_order(self, order: OrderData):
        """
        Callback of new order data update.
        """
        pass

    def on_trade(self, trade: TradeData):
        """
        Callback of new trade data update.
        """
        if trade.vt_orderid in self.vt_orderids:
            self.vt_orderids.remove(trade.vt_orderid)
        self.write_log(" order filled {}".format(trade))
    
    def cancel_remove_order(self, orderid):
            self.cancel_order(orderid)
            self.vt_orderids.remove(orderid)
            self.request_counter += 1
    # def force_cover(self):
    #     if self.pos = 0:
    #         return
    #     elif self.pos > 0:
    #         self.sell(self.pos)
    

            
    def send_new_order(self, cover_only=False):
        if self.pos == 0 and not cover_only:
            vt_orderids = self.buy(self.bid_price, self.fixed_size)
            self.vt_orderids.extend(vt_orderids)
            vt_orderids = self.short(self.ask_price, self.fixed_size)
            self.vt_orderids.extend(vt_orderids)
            self.request_counter += 2
        elif self.pos > 0:
            if not cover_only:
                vt_orderids = self.buy(self.bid_price, self.fixed_size)
                self.vt_orderids.extend(vt_orderids)
                self.request_counter += 1
            vt_orderids = self.sell(self.ask_price, self.fixed_size)
            self.vt_orderids.extend(vt_orderids)
            self.request_counter += 1
        elif self.pos < 0:
            if not cover_only:
                vt_orderids =self.short(self.ask_price, self.fixed_size)
                self.vt_orderids.extend(vt_orderids)
                self.request_counter += 1
            vt_orderids = self.cover(self.bid_price, self.fixed_size)
            self.vt_orderids.extend(vt_orderids)
            self.request_counter += 1
        


