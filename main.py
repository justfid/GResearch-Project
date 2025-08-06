from datetime import date
import pandas as pd
import plotly.graph_objects as go

#### SETUP ####
#loads CSV with columns
df = pd.read_csv("META.csv", parse_dates=["Date"])

#turns dates into strings
df["Close/Last"] = df["Close/Last"].str.replace("$", "", regex=False).astype(float)
df.set_index("Date", inplace=True)

#sort DataFrame by index (Date) in asc order
df = df.sort_index(ascending=True)

#calculate exponential moving averages (react faster to market changes)
#also std dev, then Z-score
window = 20
df["EMA20"] = df["Close/Last"].ewm(span=window, adjust=False).mean() 
#adjust=False means doesn't use FULL history / no bias correction - faster 
df["EMA50"] = df["Close/Last"].ewm(span=50, adjust=False).mean() #used for trend filter
df["Rolling_Std"] = df["Close/Last"].rolling(window).std()
df["z_score"] = (df["Close/Last"] - df["EMA20"]) / df["Rolling_Std"]


#bollinger Bands
df["upper_band"] = df["EMA20"] + 2 * df["Rolling_Std"]
df["lower_band"] = df["EMA20"] - 2 * df["Rolling_Std"]

#trend filter - moving average
df['trend_up'] = df['EMA20'] > df['EMA50']

#### PARAMETERS ####

#long entry - price below lower band, extreme Z score, trend is up
df['Long_Entry'] = (df['z_score'] < -1.5) & (df['Close/Last'] < df['lower_band']) & df['trend_up']

# "&"works with pandas

#short entry - price above upper band, extreme Z score, trend is down
df['Short_Entry'] = (df['z_score'] > 1.5) & (df['Close/Last'] > df['upper_band']) & (~df['trend_up'])

# Exit: Z-score has returned close to mean (0)
df['Exit'] = (df['z_score'].abs() < 0.1)



#### TRADING LOGIC ####

initial_balance = 1000
balance = initial_balance
position = 0  # 0 = none, 1 = long, -1 = short
entry_price = 0
shares = 0
portfolio_values = []
positions = []


executed_buys = []
executed_buys_prices = []
executed_sells = []
executed_sells_prices = []

conviction = 0.9  #90% of balance used for trades
fee = 0.0045 #0.4% fee for trades (in line with Kraken taker fees) + 0.05% spread 
#on high end but assumes no slippage, market impact, fees for short/longs, latency)

for i in range(len(df)):
    price = df["Close/Last"].iloc[i]
    #calculate portfolio value (assuming everything liquidated)
    portfolio_values.append(
        balance + shares * price if position == 1 else
        balance - shares * price if position == -1 else
        balance
    )

    #trading logic with trend filter
    if position == 0:
        #long entry with bollenger bands
        if df["Long_Entry"].iloc[i]:
            trade_amount = balance * conviction
            entry_fee = trade_amount * fee
            total_cost = trade_amount + entry_fee #apply fee to trade amount
            if total_cost <= balance: #prevents negative balance
                position = 1
                entry_price = price
                shares = trade_amount / price #assumes fractional shares
                balance -= total_cost
                executed_buys.append(df.index[i])
                executed_buys_prices.append(price)

        #only go short if bear market
        elif df["Short_Entry"].iloc[i]:
            trade_amount = balance * conviction 
            entry_fee = trade_amount * fee
            position = -1 
            entry_price = price 
            shares = trade_amount / price 
            balance += (trade_amount - entry_fee) #shorting gives you cash, applies fee
            executed_sells.append(df.index[i])
            executed_sells_prices.append(price)

    elif position == 1:
        if df["Exit"].iloc[i]:
            exit_price = price
            proceeds = shares * exit_price #sell shares
            exit_fee = proceeds * fee
            balance += (proceeds - exit_fee) #apply fee to exit proceeds
            shares = 0
            position = 0
            executed_sells.append(df.index[i])
            executed_sells_prices.append(price)

    elif position == -1:
        if df["Exit"].iloc[i]:

            exit_price = price
            cost = shares * exit_price #buy back shares
            exit_fee = cost * fee
            balance -= (cost + exit_fee) #apply fee to exit cost
            shares = 0
            position = 0
            executed_buys.append(df.index[i])
            executed_buys_prices.append(price)

    positions.append(position)

#force close any open position at the last price to calculate final portfolio value
last_price = df["Close/Last"].iloc[-1]
if position == 1 and shares > 0:
    balance += shares * last_price
    shares = 0
    position = 0
    #print("Force-closed long at end.") #redundant but useful for debugging
elif position == -1 and shares > 0:
    balance -= shares * last_price
    shares = 0
    position = 0
    #print("Force-closed short at end.") #redundant but useful for debugging

#update final portfolio value
portfolio_values[-1] = balance

df["Portfolio_Value"] = portfolio_values
df["Position"] = positions

print(f"Final balance: {balance:.2f}") 
#print(f"Final shares: {shares:.4f}") #not needed will force close at end
#print(f"Final position: {position}") #not needed will force close at end


#### PLOTLY GRAPHS ####

from plotly.subplots import make_subplots

#subplots
fig = make_subplots(rows=3, cols=1, shared_xaxes=True,
                    vertical_spacing=0.1,
                    subplot_titles=("Price with Moving Average", "Z-Score", "Portfolio Value"))

#candlestick plot for price
fig.add_trace(go.Candlestick(x=df.index,
                             open=df["Open"],
                             high=df["High"],
                             low=df["Low"],
                             close=df["Close/Last"],
                             name="Price"), row=1, col=1)

#rolling mean line
fig.add_trace(go.Scatter(x=df.index, y=df["EMA20"],
                         mode="lines",
                         line=dict(color="orange", width=2),
                         name=f"{window}-Day EMA"), row=1, col=1)

fig.add_trace(go.Scatter(x=df.index, y=df["EMA50"],
                         mode="lines",
                         line=dict(color="blue", width=2),
                         name=f"50-Day EMA"), row=1, col=1)


#executed buys (green triangle)
fig.add_trace(go.Scatter(
    x=executed_buys,
    y=executed_buys_prices,
    mode="markers",
    marker=dict(symbol="triangle-up", color="green", size=14),
    name="Executed Buy"
), row=1, col=1)

#executed sells (red triangle)
fig.add_trace(go.Scatter(
    x=executed_sells,
    y=executed_sells_prices,
    mode="markers",
    marker=dict(symbol="triangle-down", color="red", size=14),
    name="Executed Sell"
), row=1, col=1)

#upper Bollinger Band
fig.add_trace(go.Scatter(
    x=df.index,
    y=df["upper_band"],
    mode="lines",
    line=dict(color="purple", width=1, dash="dot"),
    name="Upper Bollinger Band"
), row=1, col=1)

#lower Bollinger Band
fig.add_trace(go.Scatter(
    x=df.index,
    y=df["lower_band"],
    mode="lines",
    line=dict(color="purple", width=1, dash="dot"),
    name="Lower Bollinger Band"
), row=1, col=1)

#plot Z-score
fig.add_trace(go.Scatter(x=df.index, y=df["z_score"],
                         mode="lines",
                         line=dict(color="green", width=2),
                         name="Z-Score"), row=2, col=1)

#thresholds on Z-score plot
fig.add_hline(y=0, line_dash="dash", line_color="black", row=2, col=1)
fig.add_hline(y=1.5, line_dash="dash", line_color="red", row=2, col=1)
fig.add_hline(y=-1.5, line_dash="dash", line_color="red", row=2, col=1)

fig.add_trace(go.Scatter(
    x=df.index,
    y=df["Portfolio_Value"],
    mode="lines",
    line=dict(color="black", width=2),
    name="Portfolio Value ($)"
), row=3, col=1)

#update layout
fig.update_layout(height=1050, width=1900, title_text="Stock Price & Z-Score Analysis")
fig.update_xaxes(rangeslider_visible=False)

fig.show()
