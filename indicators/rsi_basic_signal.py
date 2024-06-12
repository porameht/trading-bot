import ta

# This function generates a basic RSI signal.
def rsi_basic_signal(session, symbol, timeframe, window):
    kl = session.klines(symbol, timeframe)
    rsi = ta.momentum.RSIIndicator(kl.Close, window=window).rsi()
    
    if rsi.iloc[-2] < 30 and rsi.iloc[-1] > 30:
        return 'up', kl
    if rsi.iloc[-2] > 70 and rsi.iloc[-1] < 70:
        return 'down', kl
    else:
        return 'none', kl
