from datetime import date
import pandas as pd
import plotly.graph_objects as go

#### SETUP ####
#loads CSV with columns
df = pd.read_csv("AMD.csv", parse_dates=["Date"])

#turns dates into strings
df['Close/Last'] = df['Close/Last'].str.replace('$', '', regex=False).astype(float)
df.set_index("Date", inplace=True)

#sort DataFrame by index (Date) in asc order
df = df.sort_index(ascending=True)

#calculate rolling mean and std dev, then Z-score
window = 5
df["Rolling_Mean"] = df["Close/Last"].rolling(window).mean()
df["Rolling_Std"] = df["Close/Last"].rolling(window).std()
df["Z_Score"] = (df["Close/Last"] - df["Rolling_Mean"]) / df["Rolling_Std"]

#calculate 200 day moving average
df["MA200"] = df["Close/Last"].rolling(window=200).mean()
df["Bull_Market"] = df["Close/Last"] > df["MA200"]

#### PARAMETERS ####

#buy when price is far below mean (with a bit of give)
df["Long_Entry"] = df["Z_Score"] < -1.5
#exit long when price returns to mean (with a bit of give)
df["Long_Exit"] = df["Z_Score"] > 0.5 #better results with 0.5 instead of 0

#short when price is far above mean (with a bit of give)
df["Short_Entry"] = df["Z_Score"] > 1.5
#exit short when price returns to mean (with a bit of give)
df["Short_Exit"] = df["Z_Score"] < -0.5 #better results with 0.5 instead of 0


#### TRADING LOGIC ####
#simulate trading - half per trade - no fees or slippage

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
        #only go long if bull market
        if df["Long_Entry"].iloc[i] and df["Bull_Market"].iloc[i]:
            position = 1
            entry_price = price
            trade_amount = balance * conviction
            shares = trade_amount / price
            entry_fee = trade_amount * fee
            balance -= (trade_amount + entry_fee) #apply fee to trade amount

            executed_buys.append(df.index[i])
            executed_buys_prices.append(price)
        #only go short if bear market
        elif df["Short_Entry"].iloc[i] and not df["Bull_Market"].iloc[i]:
            position = -1
            entry_price = price
            trade_amount = balance * conviction * (1 - fee) #apply fee to trade amount
            shares = trade_amount / price
            entry_fee = trade_amount * fee
            balance += (trade_amount - entry_fee) #receive cash from short sale, apply fee

            executed_sells.append(df.index[i])
            executed_sells_prices.append(price)

    elif position == 1:
        if df["Long_Exit"].iloc[i]:
            position = 0
            exit_price = price
            proceeds = shares * exit_price #sell shares
            exit_fee = proceeds * fee #apply fee to proceeds
            balance += (proceeds - exit_fee) #apply fee to exit proceeds
            shares = 0

            executed_sells.append(df.index[i])
            executed_sells_prices.append(price)

    elif position == -1:
        if df["Short_Exit"].iloc[i]:
            position = 0
            exit_price = price
            cost = shares * exit_price #buy back shares
            exit_fee = cost * fee #apply fee to cost
            balance -= (cost + exit_fee) #apply fee to exit cost
            shares = 0

            executed_buys.append(df.index[i])
            executed_buys_prices.append(price)

    positions.append(position)

#force close any open position at the last price to calculate final portfolio value
last_price = df["Close/Last"].iloc[-1]
if position == 1 and shares > 0:
    balance += shares * last_price
    shares = 0
    position = 0
    print("Force-closed long at end.")
elif position == -1 and shares > 0:
    balance -= shares * last_price
    shares = 0
    position = 0
    print("Force-closed short at end.")

#update final portfolio value
portfolio_values[-1] = balance

df["Portfolio_Value"] = portfolio_values
df["Position"] = positions

print(f"Final balance: {balance:.2f}")
print(f"Final shares: {shares:.4f}")
print(f"Final position: {position}")

from plotly.subplots import make_subplots


#### PLOTLY GRAPHS ####
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
fig.add_trace(go.Scatter(x=df.index, y=df["Rolling_Mean"],
                         mode="lines",
                         line=dict(color="orange", width=2),
                         name=f"{window}-Day MA"), row=1, col=1)

fig.add_trace(go.Scatter(x=df.index, y=df["MA200"],
                         mode="lines",
                         line=dict(color="blue", width=2),
                         name=f"200-Day MA"), row=1, col=1)


# Find min/max Z-score points
min_z_idx = df["Z_Score"].idxmin()
max_z_idx = df["Z_Score"].idxmax()
min_z_price = df.loc[min_z_idx, "Close/Last"]
max_z_price = df.loc[max_z_idx, "Close/Last"]


# Actual executed buys (green triangle-up)
fig.add_trace(go.Scatter(
    x=executed_buys,
    y=executed_buys_prices,
    mode="markers",
    marker=dict(symbol="triangle-up", color="green", size=14),
    name="Executed Buy"
), row=1, col=1)

# Actual executed sells (red triangle-down)
fig.add_trace(go.Scatter(
    x=executed_sells,
    y=executed_sells_prices,
    mode="markers",
    marker=dict(symbol="triangle-down", color="red", size=14),
    name="Executed Sell"
), row=1, col=1)

#plot Z-score
fig.add_trace(go.Scatter(x=df.index, y=df["Z_Score"],
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
