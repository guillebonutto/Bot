import pandas as pd
import glob

# Load all trades
files = glob.glob('logs/trades/*.csv')
df = pd.concat([pd.read_csv(f) for f in files])

# Filter EMA Pullback
ema = df[df['pattern_detected'] == 'EMA Pullback']
ema = ema[ema['result'].isin(['WIN', 'LOSS'])]

# AUDCAD analysis
audcad = ema[ema['pair'] == 'AUDCAD_otc']

print(f'AUDCAD_otc (EMA Pullback):')
print(f'Total trades: {len(audcad)}')
print(f'Wins: {audcad["result"].value_counts().get("WIN", 0)}')
print(f'Losses: {audcad["result"].value_counts().get("LOSS", 0)}')
print(f'Winrate: {(audcad["result"] == "WIN").mean() * 100:.1f}%')

print(f'\nÚltimos 20 trades:')
print(audcad[['timestamp', 'result']].tail(20).to_string(index=False))

# Por hora
print(f'\nWinrate por hora:')
audcad['hour'] = pd.to_datetime(audcad['timestamp']).dt.hour
hourly = audcad.groupby('hour').agg({
    'result': lambda x: (x == 'WIN').sum(),
    'timestamp': 'count'
})
hourly.columns = ['Wins', 'Total']
hourly['Winrate'] = (hourly['Wins'] / hourly['Total'] * 100).round(1)
print(hourly.sort_values('Winrate', ascending=False))
