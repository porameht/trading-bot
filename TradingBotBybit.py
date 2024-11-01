from time import sleep
from rich import print
from Bybit import Bybit
from datetime import datetime, time
import pytz
from common.enums import OrderSide, OrderType, MarginMode, TimeFrame, Signal
from TelegramBot import TelegramBot

class TradingBotBybit:
    def __init__(self, session_config):
        self.session = Bybit(session_config['api'], session_config['secret'], session_config['accountType'])
        self.symbols = self.session.get_tickers()
        self.mode = session_config['mode']
        self.leverage = session_config['leverage']
        self.timeframe = session_config['timeframe']
        self.qty = session_config['qty']
        self.max_positions = session_config['max_positions']
        self.signal_funcs = session_config['signal_funcs']
        self.last_order_times = {}
        self.thai_tz = pytz.timezone('Asia/Bangkok')
        self.telegram = TelegramBot(session_config)
        self.current_time = datetime.now(self.thai_tz).time()

    def is_trading_time(self):
        current_time = datetime.now(self.thai_tz).time()
        start_time = time(20, 0)  # 20:00
        end_time = time(6, 0)    # 06:00

        if start_time < end_time:
            return start_time <= current_time <= end_time
        else:  # Crosses midnight
            return current_time >= start_time or current_time <= end_time
    def execute_trades(self, positions):
        for elem in self.symbols:
            if len(positions) >= self.max_positions:
                break

            last_order_time = self.last_order_times.get(elem)
            
            if last_order_time:
                continue
            
            try:
                signal_funcs = [
                    (func, *func(self.session, elem, self.timeframe))
                    for func in self.signal_funcs
                ]

                for func, signal, take_profit, stop_loss in signal_funcs:
                    if signal == Signal.UP.value and elem not in positions:
                        result = self.session.place_order_market(elem, OrderSide.BUY.value, self.mode, self.leverage, self.qty, take_profit, stop_loss)
                        
                        if result:
                            positions.append(elem)
                            self.telegram.send_trade_message(elem, OrderSide.BUY.value, self.session.get_last_price(elem), take_profit, stop_loss, func.__name__)
                            sleep(1)
                            break
                    elif signal == Signal.DOWN.value and elem not in positions:
                        result = self.session.place_order_market(elem, OrderSide.SELL.value, self.mode, self.leverage, self.qty, take_profit, stop_loss)
                        
                        if result:
                            positions.append(elem)
                            self.telegram.send_trade_message(elem, OrderSide.SELL.value, self.session.get_last_price(elem), take_profit, stop_loss, func.__name__)
                            sleep(1)
                            break

            except Exception as err:
                self.telegram.send_message(f"❌ Error executing trade for {elem}: {err}")
                print(f"Error executing trade for {elem}: {err}")

    def run(self):
        while True:
            # if not self.is_trading_time():
            #     print("Outside trading hours. Waiting...")
            #     sleep(300)  # Sleep for 5 minutes before checking again
            #     continue

            balance = self.session.get_balance()
            self.last_order_times = self.session.get_last_order_time(last_hours=1)
            net_profit = self.session.get_net_profit(last_hours=12)

            if balance is None or self.symbols is None:
                print('❌ Cannot connect to Bybit')
                sleep(120)
                continue
            
            if net_profit > 0.5:
                message = f'🎉 Net profit in the last 12 hours: {net_profit} USDT'
                print(message)
                # Only send Telegram message at midnight and noon
                if self.current_time.hour in [0, 12] and self.current_time.minute == 0:
                    self.telegram.send_message(message)
                    # Sleep for 1 minute to avoid multiple messages
                sleep(30)
                continue

            try:
                positions = self.session.get_positions(200)
                self.execute_trades(positions)
            except Exception as err:
                self.telegram.send_message(f"❌ Error in main loop: {err}")
                print(f"Error in main loop: {err}")
                sleep(60)

            print(f'🔎 Process Scanning... {len(self.symbols)} Charts => 🧠 {", ".join(f.__name__ for f in self.signal_funcs)} signals')
            sleep(20)
