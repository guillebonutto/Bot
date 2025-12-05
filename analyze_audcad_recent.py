import pandas as pd
import glob
from datetime import datetime, timedelta

# Load all trades
files = glob.glob('logs/trades/*.csv')
dfs = []
for f in files:
    try:
        df = pd.read_csv(f)
        dfs.append(df)
    except:
        pass

df = pd.concat(dfs, ignore_index=True)

# Filter AUDCAD
audcad = df[df['pair'] == 'AUDCAD_otc'].copy()
audcad = audcad[audcad['result'].isin(['WIN', 'LOSS'])]
audcad['timestamp'] = pd.to_datetime(audcad['timestamp'])

# Sort by timestamp
audcad = audcad.sort_values('timestamp', ascending=False)

print("="*60)
print("ANÁLISIS DE AUDCAD_otc - TRADES RECIENTES")
print("="*60)

# Overall stats
total = len(audcad)
wins = (audcad['result'] == 'WIN').sum()
winrate = wins / total * 100 if total > 0 else 0

print(f"\n📊 ESTADÍSTICAS GENERALES:")
print(f"Total trades: {total}")
print(f"Wins: {wins}")
print(f"Losses: {total - wins}")
print(f"Winrate: {winrate:.1f}%")

# Last 30 days
thirty_days_ago = datetime.now() - timedelta(days=30)
recent = audcad[audcad['timestamp'] >= thirty_days_ago]

if len(recent) > 0:
    recent_wins = (recent['result'] == 'WIN').sum()
    recent_total = len(recent)
    recent_wr = recent_wins / recent_total * 100
    
    print(f"\n📅 ÚLTIMOS 30 DÍAS:")
    print(f"Total trades: {recent_total}")
    print(f"Wins: {recent_wins}")
    print(f"Losses: {recent_total - recent_wins}")
    print(f"Winrate: {recent_wr:.1f}%")

# Last 20 trades
print(f"\n📋 ÚLTIMOS 20 TRADES:")
print("-"*60)
last_20 = audcad.head(20)
for idx, row in last_20.iterrows():
    result_emoji = "✅" if row['result'] == 'WIN' else "❌"
    strategy = row.get('pattern_detected', 'N/A')
    timestamp = row['timestamp'].strftime('%Y-%m-%d %H:%M')
    print(f"{result_emoji} {timestamp} | {strategy}")

# By strategy
print(f"\n🎯 WINRATE POR ESTRATEGIA:")
print("-"*60)
by_strategy = audcad.groupby('pattern_detected').agg({
    'result': lambda x: f"{(x=='WIN').sum()}/{len(x)} ({(x=='WIN').mean()*100:.1f}%)"
}).reset_index()
by_strategy.columns = ['Estrategia', 'Wins/Total (Winrate)']
print(by_strategy.to_string(index=False))

# By hour
audcad['hour'] = audcad['timestamp'].dt.hour
print(f"\n⏰ WINRATE POR HORA (mínimo 3 trades):")
print("-"*60)
by_hour = audcad.groupby('hour').agg({
    'result': [lambda x: (x=='WIN').sum(), 'count', lambda x: (x=='WIN').mean()*100]
})
by_hour.columns = ['Wins', 'Total', 'Winrate']
by_hour = by_hour[by_hour['Total'] >= 3].sort_values('Winrate', ascending=False)
print(by_hour.to_string())

print("\n" + "="*60)
