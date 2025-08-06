from datetime import date
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.figure_factory as ff

#### PARAMETERS ####
window = 20 #best results with 20 so variable name is EMA20
bollinger_threshold = 1.5  #num standard deviations away from EMA20
neutral_zone = 0.05  #neutral zone
z_score_threshold = 1.25  #threshold for Z-score
z_score_exit_threshold = 0.1  #threshold for exiting trades
conviction = 0.9  #90% of balance used for trades
fee = 0.00001 #0.001% fee per trade (GIVEN)
risk_free_rate = 0.025 #assumed annualised risk-free rate
initial_balance = 100000 #initial balance in USD (GIVEN)
short_daily_fee = 0.0001 #0.01% daily fee for shorting (GIVEN)

#### SETUP ####
#loads CSV with columns
df = pd.read_csv("AMD.csv", parse_dates=["Date"])

#turns dates into strings
df["Close/Last"] = df["Close/Last"].str.replace("$", "", regex=False).astype(float)
df.set_index("Date", inplace=True)

#sort DataFrame by index (Date) in asc order
df = df.sort_index(ascending=True)

#calculate exponential moving averages (react faster to market changes)
#also std dev, then Z-score

df["EMA20"] = df["Close/Last"].ewm(span=window, adjust=False).mean() 
#adjust=False means doesn't use FULL history / no bias correction - faster 
df["EMA50"] = df["Close/Last"].ewm(span=50, adjust=False).mean() #used for trend filter
df["Rolling_Std"] = df["Close/Last"].rolling(window).std()
df["z_score"] = (df["Close/Last"] - df["EMA20"]) / df["Rolling_Std"]


#bollinger Bands
df["upper_band"] = df["EMA20"] + (bollinger_threshold * df["Rolling_Std"])
df["lower_band"] = df["EMA20"] - (bollinger_threshold * df["Rolling_Std"])

#trend filter - moving average (with neutral zone)
df['trend_up'] = df['EMA20'] > df['EMA50'] * (1 - neutral_zone)
df['trend_down'] = df['EMA20'] < df['EMA50'] * (1 + neutral_zone)


#### THEORY ####

#long entry - price below lower band, extreme Z score, trend is up
df['Long_Entry'] = (df['z_score'] < -z_score_threshold) & (df['Close/Last'] < df['lower_band']) & (df['trend_up'])

# "&"works with pandas - and

#short entry - price above upper band, extreme Z score, trend is down
df['Short_Entry'] = (df['z_score'] > z_score_threshold) & (df['Close/Last'] > df['upper_band']) & (~df['trend_up'])

# "~" is NOT operator in pandas

#exit: Z-score has returned close to mean (0)
df['Exit'] = (df['z_score'].abs() < z_score_exit_threshold)



#### TRADING LOGIC ####
balance = initial_balance
position = 0  # 0 = none, 1 = long, -1 = short
entry_price = 0
shares = 0
portfolio_values = []
positions = []
short_entry_index = None

executed_buys = []
executed_buys_prices = []
executed_sells = []
executed_sells_prices = []
executed_exit = []
executed_exit_prices = []


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
            entry_fee = (trade_amount * fee) + 1 #add 1 to fee as fixed fee on top
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
            entry_fee = (trade_amount * fee) + 1 #add 1 to fee as fixed fee on top
            position = -1 
            entry_price = price 
            shares = trade_amount / price 
            balance += (trade_amount - entry_fee) #shorting gives you cash, applies fee
            short_entry_index = i  #track when the short started
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
            executed_exit.append(df.index[i])
            executed_exit_prices.append(price)

    elif position == -1:
        if df["Exit"].iloc[i]:

            exit_price = price
            cost = shares * exit_price #buy back shares
            exit_fee = cost * fee

            #calculate days held and apply daily short fee
            if short_entry_index is not None:
                days_held = i - short_entry_index
                short_fee_total = shares * entry_price * short_daily_fee * days_held
            else:
                short_fee_total = 0

            balance -= (cost + exit_fee + short_fee_total) #apply exit fees and overall short fee
            shares = 0
            position = 0
            executed_buys.append(df.index[i])
            executed_buys_prices.append(price)
            short_entry_index = None  #resets
            executed_exit
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

elif position == -1 and shares > 0:
    if short_entry_index is not None:
        days_held = len(df) - 1 - short_entry_index
        short_fee_total = shares * entry_price * short_daily_fee * days_held
    else:
        short_fee_total = 0
    balance -= (shares * last_price + short_fee_total)
    shares = 0
    position = 0

#update final portfolio value
portfolio_values[-1] = balance

df["Portfolio_Value"] = portfolio_values
df["Position"] = positions

#### SHARPE RATIO ####
#calculate daily returns of strategy
df['Strategy_Return'] = df['Portfolio_Value'].pct_change()

#calculate mean and std deviation of trade returns
mean_strategy_return = df['Strategy_Return'].mean() #daily
std_strategy_return = df['Strategy_Return'].std() #daily

#annualised return and Sharpe Ratio
annual_return = mean_strategy_return * 252
annual_std = std_strategy_return * (252 ** 0.5) #square root of 252 trading days
annual_sharpe = (annual_return - risk_free_rate) / annual_std 

print(f"Annual (avg) Return (Percentage): {(annual_return * 100).round(4)}%")
print(f"Annual Sharpe Ratio: {annual_sharpe:.4f}")
print(f"Final profit /loss: {balance - initial_balance:.2f} USD")
print(f"Final balance: {balance:.2f}") 
#print(f"Final shares: {shares:.4f}") #not needed will force close at end
#print(f"Final position: {position}") #not needed will force close at end


#### PLOTLY GRAPHS ####

#subplots
fig = make_subplots(rows=3, cols=1, shared_xaxes=True,
                    vertical_spacing=0.1,
                    subplot_titles=("Price with EMA & Bollinger Bands", "Portfolio Value", "Z-Score",))

#candlestick plot for price (row 1)
fig.add_trace(go.Candlestick(x=df.index,
                             open=df["Open"],
                             high=df["High"],
                             low=df["Low"],
                             close=df["Close/Last"],
                             name="Price"), row=1, col=1)

#EMA lines
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

#executed exits (red triangle)
fig.add_trace(go.Scatter(
    x=executed_exit,
    y=executed_exit_prices,
    mode="markers",
    marker=dict(symbol="diamond", color="purple", size=14),
    name="Executed Exit"
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

#portfolio value plot
fig.add_trace(go.Scatter(
    x=df.index,
    y=df["Portfolio_Value"],
    mode="lines",
    line=dict(color="black", width=2),
    name="Portfolio Value ($)"
), row=2, col=1)

#add baseline at initial balance
fig.add_hline(
    y=initial_balance,
    line_dash="dot",
    line_color="gray",
    annotation_text="Initial Balance",
    annotation_position="top left",
    row=2,
    col=1
)

#plot Z-score
fig.add_trace(go.Scatter(x=df.index, y=df["z_score"],
                         mode="lines",
                         line=dict(color="green", width=2),
                         name="Z-Score"), row=3, col=1)

#thresholds on Z-score plot
fig.add_hline(y=0, line_dash="dash", line_color="black", row=3, col=1)
fig.add_hline(y=z_score_threshold, line_dash="dash", line_color="red", row=3, col=1)
fig.add_hline(y=-z_score_threshold, line_dash="dash", line_color="red", row=3, col=1)

#update layout
fig.update_layout(height=1050, width=1900, title_text="Stock Price & Z-Score Analysis")

#add button to toggle between linear/log scale (not to z score plot)
fig.update_layout(
    updatemenus=[
        dict(
            type="buttons",
            direction="right",
            x=0.7,
            y=1.15,
            buttons=list([
                dict(
                    args=[
                        {"yaxis.type": "linear", "yaxis2.type": "linear"}
                    ],
                    label="Linear",
                    method="relayout"
                ),
                dict(
                    args=[
                        {"yaxis.type": "log", "yaxis2.type": "log"}
                    ],
                    label="Log",
                    method="relayout"
                )
            ]),
            showactive=True
        )
    ]
)

fig.update_xaxes(rangeslider_visible=False)

#### TABLES ####
#create year column from the index
df['Year'] = df.index.year

#calculate yearly profit
yearly_profit = df.groupby('Year')['Portfolio_Value'].agg(['first', 'last'])
yearly_profit['Profit'] = yearly_profit['last'] - yearly_profit['first']

#calculate yearly Sharpe ratio
def yearly_sharpe(group):
    returns = group['Portfolio_Value'].pct_change() #daily returns
    mean_return = returns.mean() * 252  # annualised
    std_return = returns.std() * (252 ** 0.5)  # annualised
    sharpe = (mean_return - risk_free_rate) / std_return
    return sharpe

yearly_sharpe_ratios = df.groupby('Year').apply(yearly_sharpe) #apply function to each group
#code will be deprecated in future versions - doesn't affect functionality NOW
yearly_profit['Sharpe Ratio'] = yearly_sharpe_ratios

#plotly table
table_data = yearly_profit.reset_index()[['Year', 'Profit', 'Sharpe Ratio']]
table_data['Profit'] = table_data['Profit'].map('{:.2f}'.format) 
table_data['Sharpe Ratio'] = table_data['Sharpe Ratio'].map('{:.2f}'.format)

fig_table = ff.create_table(table_data) 
fig_table.update_layout(width=500, height=400, title="Yearly Profit & Sharpe Ratio")


#summary table for overall results
summary_data = pd.DataFrame({
    "Metric": ["Final Profit (USD)", "Final Portfolio Value (USD)", "Overall Sharpe Ratio"],
    "Value": [
        f"{(balance - initial_balance):.2f}",
        f"{balance:.2f}",
        f"{annual_sharpe:.2f}"
    ]
})

fig_summary = ff.create_table(summary_data) 
fig_summary.update_layout(width=500, height=200, title="Overall Performance Summary")

#show tables and plots
fig.show()
fig_table.show()
fig_summary.show()
