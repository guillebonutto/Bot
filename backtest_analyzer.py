#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Backtest Analysis Tool - EMA Pullback Strategy
Analiza logs de trades y datos históricos para optimizar horarios, pares y gestión de riesgo
"""

import pandas as pd
import numpy as np
import glob
import os
from datetime import datetime
import matplotlib.pyplot as plt
import seaborn as sns
from collections import defaultdict

# Configuración de visualización
sns.set_style("darkgrid")
plt.rcParams['figure.figsize'] = (14, 8)

class BacktestAnalyzer:
    def __init__(self, trades_dir="logs/trades", history_dir="history"):
        self.trades_dir = trades_dir
        self.history_dir = history_dir
        self.trades_df = None
        self.results = {}
        
    def load_trade_logs(self):
        """Carga todos los archivos CSV de trades"""
        print("📂 Cargando logs de trades...")
        
        all_files = glob.glob(os.path.join(self.trades_dir, "trades_*.csv"))
        
        if not all_files:
            print(f"⚠️ No se encontraron archivos en {self.trades_dir}")
            return None
        
        dfs = []
        for file in all_files:
            try:
                df = pd.read_csv(file)
                dfs.append(df)
            except Exception as e:
                print(f"⚠️ Error leyendo {file}: {e}")
        
        if not dfs:
            return None
            
        self.trades_df = pd.concat(dfs, ignore_index=True)
        
        # Convertir timestamp
        self.trades_df['timestamp'] = pd.to_datetime(self.trades_df['timestamp'])
        
        # Extraer información temporal
        self.trades_df['hour'] = self.trades_df['timestamp'].dt.hour
        self.trades_df['day_of_week'] = self.trades_df['timestamp'].dt.day_name()
        self.trades_df['date'] = self.trades_df['timestamp'].dt.date
        
        # Convertir result a binario
        self.trades_df['win'] = (self.trades_df['result'] == 'WIN').astype(int)
        
        print(f"✅ Cargados {len(self.trades_df)} trades desde {len(all_files)} archivos")
        return self.trades_df

    def analyze_strategies(self):
        """Analiza performance por estrategia (pattern_detected)"""
        print("\n🧠 Analizando performance por ESTRATEGIA...")
        
        if 'pattern_detected' not in self.trades_df.columns:
            print("⚠️ No se encontró la columna 'pattern_detected'")
            return

        patterns = self.trades_df['pattern_detected'].unique()
        
        strategy_report = []

        for pattern in patterns:
            df_pattern = self.trades_df[self.trades_df['pattern_detected'] == pattern]
            total_trades = len(df_pattern)
            if total_trades < 5: continue # Ignorar estrategias con muy pocos datos

            wins = df_pattern['win'].sum()
            winrate = (wins / total_trades) * 100
            
            # Mejor Par para esta estrategia
            best_pair_row = df_pattern.groupby('pair')['win'].agg(['mean', 'count'])
            best_pair_row = best_pair_row[best_pair_row['count'] >= 3] # Mínimo 3 trades
            if not best_pair_row.empty:
                best_pair = best_pair_row['mean'].idxmax()
                best_pair_wr = best_pair_row['mean'].max() * 100
            else:
                best_pair = "N/A"
                best_pair_wr = 0.0

            # Mejor Hora para esta estrategia
            best_hour_row = df_pattern.groupby('hour')['win'].agg(['mean', 'count'])
            best_hour_row = best_hour_row[best_hour_row['count'] >= 3]
            if not best_hour_row.empty:
                best_hour = best_hour_row['mean'].idxmax()
                best_hour_wr = best_hour_row['mean'].max() * 100
            else:
                best_hour = -1
                best_hour_wr = 0.0

            strategy_report.append({
                'Estrategia': pattern,
                'Trades': total_trades,
                'Winrate Global': winrate,
                'Mejor Par': best_pair,
                'Winrate Par': best_pair_wr,
                'Mejor Hora': best_hour,
                'Winrate Hora': best_hour_wr
            })

        # Convertir a DataFrame y ordenar
        if not strategy_report:
            print("⚠️ No hay suficientes datos por estrategia")
            return None
            
        report_df = pd.DataFrame(strategy_report).sort_values('Winrate Global', ascending=False)
        
        print("\n🏆 RANKING DE ESTRATEGIAS:")
        print(report_df.to_string(index=False, float_format=lambda x: "{:.1f}%".format(x) if isinstance(x, float) else str(x)))
        
        self.results['strategies'] = report_df
        return report_df
    
    def analyze_by_hour(self):
        """Analiza performance por hora del día"""
        print("\n⏰ Analizando performance por hora...")
        
        hourly = self.trades_df.groupby('hour').agg({
            'win': ['sum', 'count', 'mean'],
            'profit_loss': 'sum'
        }).round(3)
        
        hourly.columns = ['Wins', 'Total_Trades', 'Winrate', 'Total_PnL']
        hourly['Winrate'] = (hourly['Winrate'] * 100).round(1)
        
        # Ordenar por winrate
        hourly_sorted = hourly.sort_values('Winrate', ascending=False)
        
        print("\n🏆 TOP 5 MEJORES HORARIOS:")
        print(hourly_sorted.head())
        
        print("\n⚠️ TOP 5 PEORES HORARIOS:")
        print(hourly_sorted.tail())
        
        self.results['hourly'] = hourly
        return hourly
    
    def analyze_by_pair(self):
        """Analiza performance por par"""
        print("\n💱 Analizando performance por par...")
        
        pairs = self.trades_df.groupby('pair').agg({
            'win': ['sum', 'count', 'mean'],
            'profit_loss': 'sum'
        }).round(3)
        
        pairs.columns = ['Wins', 'Total_Trades', 'Winrate', 'Total_PnL']
        pairs['Winrate'] = (pairs['Winrate'] * 100).round(1)
        
        # Ordenar por winrate
        pairs_sorted = pairs.sort_values('Winrate', ascending=False)
        
        print("\n🏆 MEJORES PARES:")
        print(pairs_sorted)
        
        self.results['pairs'] = pairs
        return pairs
    
    def analyze_by_timeframe(self):
        """Analiza performance por timeframe"""
        print("\n⏱️ Analizando performance por timeframe...")
        
        tf = self.trades_df.groupby('timeframe').agg({
            'win': ['sum', 'count', 'mean'],
            'profit_loss': 'sum'
        }).round(3)
        
        tf.columns = ['Wins', 'Total_Trades', 'Winrate', 'Total_PnL']
        tf['Winrate'] = (tf['Winrate'] * 100).round(1)
        
        print(tf)
        
        self.results['timeframe'] = tf
        return tf
    
    def calculate_risk_metrics(self):
        """Calcula métricas de riesgo y drawdown"""
        print("\n📊 Calculando métricas de riesgo...")
        
        # Simular balance con diferentes % de riesgo
        risk_scenarios = [0.5, 1.0, 1.5, 2.0, 5.0, 10.0]
        initial_balance = 1000
        
        results = []
        
        for risk_pct in risk_scenarios:
            balance = initial_balance
            balances = [balance]
            max_balance = balance
            max_drawdown = 0
            
            for _, trade in self.trades_df.iterrows():
                amount = balance * (risk_pct / 100)
                
                if trade['result'] == 'WIN':
                    profit = amount * 0.92  # 92% payout
                    balance += profit
                else:
                    balance -= amount
                
                balances.append(balance)
                
                # Calcular drawdown
                if balance > max_balance:
                    max_balance = balance
                
                drawdown = ((max_balance - balance) / max_balance) * 100
                if drawdown > max_drawdown:
                    max_drawdown = drawdown
            
            final_balance = balance
            roi = ((final_balance - initial_balance) / initial_balance) * 100
            
            results.append({
                'Risk_%': risk_pct,
                'Final_Balance': round(final_balance, 2),
                'ROI_%': round(roi, 1),
                'Max_Drawdown_%': round(max_drawdown, 1),
                'Survived': 'SÍ' if final_balance > 0 else 'NO'
            })
        
        risk_df = pd.DataFrame(results)
        
        print("\n💰 SIMULACIÓN DE GESTIÓN DE RIESGO:")
        print(f"Capital inicial: ${initial_balance}")
        print(f"Total trades: {len(self.trades_df)}")
        print(f"Winrate global: {self.trades_df['win'].mean() * 100:.1f}%\n")
        print(risk_df.to_string(index=False))
        
        self.results['risk_simulation'] = risk_df
        return risk_df
    
    def analyze_streaks(self):
        """Analiza rachas ganadoras y perdedoras"""
        print("\n🎲 Analizando rachas...")
        
        # Calcular rachas
        streaks = []
        current_streak = 0
        current_type = None
        
        for win in self.trades_df['win']:
            if win == 1:
                if current_type == 'WIN':
                    current_streak += 1
                else:
                    if current_streak > 0:
                        streaks.append({'type': current_type, 'length': current_streak})
                    current_streak = 1
                    current_type = 'WIN'
            else:
                if current_type == 'LOSS':
                    current_streak += 1
                else:
                    if current_streak > 0:
                        streaks.append({'type': current_type, 'length': current_streak})
                    current_streak = 1
                    current_type = 'LOSS'
        
        if current_streak > 0:
            streaks.append({'type': current_type, 'length': current_streak})
        
        streaks_df = pd.DataFrame(streaks)
        
        if len(streaks_df) > 0:
            win_streaks = streaks_df[streaks_df['type'] == 'WIN']['length']
            loss_streaks = streaks_df[streaks_df['type'] == 'LOSS']['length']
            
            print(f"🏆 Racha ganadora máxima: {win_streaks.max() if len(win_streaks) > 0 else 0} trades")
            print(f"❌ Racha perdedora máxima: {loss_streaks.max() if len(loss_streaks) > 0 else 0} trades")
            print(f"📊 Racha ganadora promedio: {win_streaks.mean():.1f} trades" if len(win_streaks) > 0 else "")
            print(f"📊 Racha perdedora promedio: {loss_streaks.mean():.1f} trades" if len(loss_streaks) > 0 else "")
        
        self.results['streaks'] = streaks_df
        return streaks_df
    
    def generate_recommendations(self):
        """Genera recomendaciones basadas en el análisis"""
        print("\n" + "="*60)
        print("🎯 RECOMENDACIONES BASADAS EN TUS DATOS")
        print("="*60)
        
        # Mejores horarios
        if 'hourly' in self.results:
            hourly = self.results['hourly']
            best_hours = hourly[hourly['Total_Trades'] >= 5].nlargest(3, 'Winrate')
            
            if len(best_hours) > 0:
                print("\n⏰ MEJORES HORARIOS PARA OPERAR:")
                for hour, row in best_hours.iterrows():
                    print(f"   {hour:02d}:00 - Winrate: {row['Winrate']:.1f}% ({int(row['Total_Trades'])} trades)")
        
        # Mejores pares
        if 'pairs' in self.results:
            pairs = self.results['pairs']
            best_pairs = pairs[pairs['Total_Trades'] >= 5].nlargest(3, 'Winrate')
            
            if len(best_pairs) > 0:
                print("\n💱 MEJORES PARES PARA OPERAR:")
                for pair, row in best_pairs.iterrows():
                    print(f"   {pair} - Winrate: {row['Winrate']:.1f}% ({int(row['Total_Trades'])} trades)")
        
        # Gestión de riesgo recomendada
        if 'risk_simulation' in self.results:
            risk_df = self.results['risk_simulation']
            safe_risk = risk_df[risk_df['Max_Drawdown_%'] <= 20]
            
            if len(safe_risk) > 0:
                best_risk = safe_risk.nlargest(1, 'ROI_%').iloc[0]
                print(f"\n💰 GESTIÓN DE RIESGO RECOMENDADA:")
                print(f"   Riesgo por trade: {best_risk['Risk_%']}%")
                print(f"   ROI esperado: {best_risk['ROI_%']}%")
                print(f"   Drawdown máximo: {best_risk['Max_Drawdown_%']}%")
        
        print("\n" + "="*60)
    
    def plot_performance(self):
        """Genera gráficos de performance"""
        print("\n📈 Generando gráficos...")
        
        fig, axes = plt.subplots(2, 2, figsize=(16, 10))
        
        # 1. Winrate por hora
        if 'hourly' in self.results:
            hourly = self.results['hourly']
            axes[0, 0].bar(hourly.index, hourly['Winrate'], color='steelblue')
            axes[0, 0].axhline(y=50, color='r', linestyle='--', label='50% Breakeven')
            axes[0, 0].set_xlabel('Hora del día')
            axes[0, 0].set_ylabel('Winrate (%)')
            axes[0, 0].set_title('Winrate por Hora del Día')
            axes[0, 0].legend()
            axes[0, 0].grid(True, alpha=0.3)
        
        # 2. Winrate por par
        if 'pairs' in self.results:
            pairs = self.results['pairs'].sort_values('Winrate', ascending=True)
            axes[0, 1].barh(pairs.index, pairs['Winrate'], color='coral')
            axes[0, 1].axvline(x=50, color='r', linestyle='--', label='50% Breakeven')
            axes[0, 1].set_xlabel('Winrate (%)')
            axes[0, 1].set_title('Winrate por Par')
            axes[0, 1].legend()
            axes[0, 1].grid(True, alpha=0.3)
        
        # 3. Simulación de balance con diferentes riesgos
        if 'risk_simulation' in self.results:
            risk_df = self.results['risk_simulation']
            x = np.arange(len(risk_df))
            width = 0.35
            
            axes[1, 0].bar(x - width/2, risk_df['ROI_%'], width, label='ROI %', color='green', alpha=0.7)
            axes[1, 0].bar(x + width/2, risk_df['Max_Drawdown_%'], width, label='Max Drawdown %', color='red', alpha=0.7)
            axes[1, 0].set_xlabel('Riesgo por Trade (%)')
            axes[1, 0].set_ylabel('Porcentaje (%)')
            axes[1, 0].set_title('ROI vs Drawdown por Nivel de Riesgo')
            axes[1, 0].set_xticks(x)
            axes[1, 0].set_xticklabels(risk_df['Risk_%'])
            axes[1, 0].legend()
            axes[1, 0].grid(True, alpha=0.3)
        
        # 4. Evolución del balance acumulado
        self.trades_df['cumulative_pnl'] = self.trades_df['profit_loss'].cumsum()
        axes[1, 1].plot(self.trades_df.index, self.trades_df['cumulative_pnl'], linewidth=2, color='darkblue')
        axes[1, 1].fill_between(self.trades_df.index, 0, self.trades_df['cumulative_pnl'], alpha=0.3)
        axes[1, 1].axhline(y=0, color='r', linestyle='--', alpha=0.5)
        axes[1, 1].set_xlabel('Número de Trade')
        axes[1, 1].set_ylabel('P&L Acumulado ($)')
        axes[1, 1].set_title('Evolución del P&L Acumulado')
        axes[1, 1].grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        # Guardar gráfico
        output_file = 'backtest_analysis.png'
        plt.savefig(output_file, dpi=150, bbox_inches='tight')
        print(f"✅ Gráficos guardados en: {output_file}")
        
        # Mostrar (opcional)
        # plt.show()
    
    def run_full_analysis(self):
        """Ejecuta análisis completo"""
        print("\n" + "="*60)
        print("🚀 INICIANDO ANÁLISIS MULTI-ESTRATEGIA")
        print("="*60)
        
        # Cargar datos
        if self.load_trade_logs() is None:
            print("❌ No se pudieron cargar los datos")
            return
        
        # Análisis por estrategia
        self.analyze_strategies()
        
        # Análisis general (opcional, si se quiere ver el global)
        self.analyze_by_hour()
        self.analyze_by_pair()
        self.calculate_risk_metrics()
        
        print("\n✅ Análisis completado!")
        return self.results


if __name__ == "__main__":
    analyzer = BacktestAnalyzer()
    results = analyzer.run_full_analysis()
