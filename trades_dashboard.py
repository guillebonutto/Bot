"""
trades_dashboard.py
===================
Dashboard simple para monitorear trades en tiempo real desde terminal.
"""

import pandas as pd
import time
from datetime import datetime, timezone
from pathlib import Path
from collections import defaultdict
import os


class TradesDashboard:
    """Dashboard de trades en tiempo real."""
    
    def __init__(self, update_interval=5):
        self.update_interval = update_interval
        self.last_count = 0
    
    def get_current_trades(self):
        """Obtener trades del día actual."""
        date = datetime.now(timezone.utc).strftime("%Y%m%d")
        filepath = Path("logs") / "trades" / f"trades_{date}.csv"
        
        if not filepath.exists():
            return pd.DataFrame()
        
        try:
            df = pd.read_csv(filepath)
            return df
        except:
            return pd.DataFrame()
    
    def clear_screen(self):
        """Limpiar pantalla."""
        os.system('cls' if os.name == 'nt' else 'clear')
    
    def format_number(self, val, decimals=2):
        """Formatear número con decimales."""
        if pd.isna(val):
            return "N/A"
        if isinstance(val, (int, float)):
            return f"{val:.{decimals}f}"
        return str(val)
    
    def print_dashboard(self, df):
        """Imprimir dashboard formateado."""
        self.clear_screen()
        
        now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        print(f"🤖 TRADES DASHBOARD - {now}")
        print("=" * 120)
        
        if df.empty:
            print("⏳ Sin trades aún...")
            return
        
        # Estadísticas generales
        total = len(df)
        completed = df[df['result'].isin(['WIN', 'LOSS'])]
        pending = len(df[df['result'] == 'PENDING'])
        wins = len(df[df['result'] == 'WIN'])
        losses = len(df[df['result'] == 'LOSS'])
        
        if len(completed) > 0:
            wr = wins / len(completed) * 100
        else:
            wr = 0
        
        total_profit = df[df['result'] == 'WIN']['profit_loss'].sum()
        total_loss = abs(df[df['result'] == 'LOSS']['profit_loss'].sum())
        net = total_profit - total_loss
        
        # Fila de stats
        print(f"📊 Total: {total} | ✅ {wins}W | ❌ {losses}L | ⏳ {pending}P | 📈 WR: {wr:.1f}%")
        print(f"💰 Ganancia: ${total_profit:.2f} | 💸 Pérdida: ${total_loss:.2f} | 📊 Neto: ${net:.2f}")
        print("=" * 120)
        
        # Últimos 10 trades (más recientes primero)
        recent = df.tail(10).iloc[::-1]
        
        print("\n📌 ÚLTIMOS 10 TRADES:")
        print("-" * 120)
        print(f"{'ID':<12} {'Timestamp':<19} {'Par':<12} {'TF':<5} {'Dir':<5} {'Score':<6} {'Precio':<10} {'Result':<8} {'P/L':<10}")
        print("-" * 120)
        
        for _, row in recent.iterrows():
            timestamp = row['timestamp'][:19] if isinstance(row['timestamp'], str) else str(row['timestamp'])[:19]
            pair = str(row['pair'])[:12]
            tf = str(row['timeframe'])
            direction = row['decision']
            score = f"{row['signal_score']:.0f}"
            price = f"{row['price']:.5f}"
            result = row['result']
            profit = row['profit_loss'] if pd.notna(row['profit_loss']) else 0
            
            # Color según resultado
            result_icon = "✅" if result == "WIN" else "❌" if result == "LOSS" else "⏳"
            
            print(f"{str(row['trade_id']):<12} {timestamp:<19} {pair:<12} {tf:<5} {direction:<5} {score:<6} {price:<10} {result_icon} {result:<7} ${profit:>8.2f}")
        
        # Estadísticas por par
        print("\n" + "=" * 120)
        print("📊 ESTADÍSTICAS POR PAR:")
        print("-" * 120)
        print(f"{'Par':<15} {'Total':<8} {'Ganadas':<10} {'Perdidas':<10} {'Winrate':<10} {'Neto P/L':<12}")
        print("-" * 120)
        
        for pair in sorted(df['pair'].unique()):
            pair_df = df[df['pair'] == pair]
            pair_total = len(pair_df)
            pair_wins = len(pair_df[pair_df['result'] == 'WIN'])
            pair_losses = len(pair_df[pair_df['result'] == 'LOSS'])
            pair_wr = (pair_wins / (pair_wins + pair_losses) * 100) if (pair_wins + pair_losses) > 0 else 0
            pair_net = (pair_df[pair_df['result'] == 'WIN']['profit_loss'].sum() - 
                       abs(pair_df[pair_df['result'] == 'LOSS']['profit_loss'].sum()))
            
            print(f"{pair:<15} {pair_total:<8} {pair_wins:<10} {pair_losses:<10} {pair_wr:>8.1f}% ${pair_net:>10.2f}")
        
        # Patrones más efectivos
        print("\n" + "=" * 120)
        print("🔍 PATRONES MÁS EFECTIVOS:")
        print("-" * 120)
        
        patterns = defaultdict(lambda: {'total': 0, 'wins': 0})
        for _, row in completed.iterrows():
            pattern = row['pattern_detected']
            patterns[pattern]['total'] += 1
            if row['result'] == 'WIN':
                patterns[pattern]['wins'] += 1
        
        sorted_patterns = sorted(
            patterns.items(),
            key=lambda x: (x[1]['wins'] / x[1]['total'] if x[1]['total'] > 0 else 0),
            reverse=True
        )
        
        for pattern, stats in sorted_patterns[:5]:
            if stats['total'] == 0:
                continue
            wr = stats['wins'] / stats['total'] * 100
            print(f"  {pattern:<30} | Trades: {stats['total']:<4} | Ganadas: {stats['wins']:<4} | WR: {wr:>5.1f}%")
        
        print("\n" + "=" * 120)
        print(f"⏰ Actualización cada {self.update_interval}s | Presiona Ctrl+C para salir")
    
    def run(self):
        """Ejecutar dashboard con actualizaciones periódicas."""
        try:
            while True:
                df = self.get_current_trades()
                self.print_dashboard(df)
                time.sleep(self.update_interval)
        except KeyboardInterrupt:
            self.clear_screen()
            print("\n👋 Dashboard cerrado")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Dashboard de trades en tiempo real')
    parser.add_argument('--interval', type=int, default=5, help='Intervalo de actualización en segundos')
    args = parser.parse_args()
    
    dashboard = TradesDashboard(update_interval=args.interval)
    dashboard.run()


if __name__ == "__main__":
    main()
