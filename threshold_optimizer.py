#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Threshold Optimizer for EMA Pullback Strategy
Analyzes historical trades to find optimal ML confidence threshold
"""

import pandas as pd
import numpy as np
import glob
import os
import matplotlib.pyplot as plt
import seaborn as sns

# Configuration
sns.set_style("darkgrid")

def load_ema_pullback_trades():
    """Load only EMA Pullback trades"""
    print("📂 Cargando trades de EMA Pullback...")
    
    all_files = glob.glob("logs/trades/trades_*.csv")
    if not all_files:
        print("❌ No se encontraron archivos")
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
    
    all_trades = pd.concat(dfs, ignore_index=True)
    
    # Filter only EMA Pullback
    ema_trades = all_trades[all_trades['pattern_detected'] == 'EMA Pullback']
    
    # Filter only completed trades
    ema_trades = ema_trades[ema_trades['result'].isin(['WIN', 'LOSS'])]
    
    # Convert timestamp
    ema_trades['timestamp'] = pd.to_datetime(ema_trades['timestamp'])
    ema_trades['hour'] = ema_trades['timestamp'].dt.hour
    ema_trades['win'] = (ema_trades['result'] == 'WIN').astype(int)
    
    print(f"✅ Cargados {len(ema_trades)} trades de EMA Pullback")
    return ema_trades

def analyze_threshold_impact(df):
    """Analyze impact of different thresholds"""
    print("\n🎯 Analizando impacto de diferentes thresholds...")
    
    # Test different thresholds
    thresholds = [0.50, 0.55, 0.60, 0.62, 0.65, 0.70, 0.75, 0.80]
    results = []
    
    for threshold in thresholds:
        # Filter trades by signal_score (ML confidence)
        if 'signal_score' in df.columns:
            filtered = df[df['signal_score'] >= threshold]
        else:
            # If no signal_score, assume all trades pass
            filtered = df
        
        if len(filtered) > 0:
            winrate = filtered['win'].mean() * 100
            total_trades = len(filtered)
            
            # Calculate expected profit (assuming 92% payout, 1% risk)
            wins = filtered['win'].sum()
            losses = total_trades - wins
            expected_profit = (wins * 0.92) - losses
            roi = (expected_profit / total_trades) * 100 if total_trades > 0 else 0
            
            results.append({
                'Threshold': f"{threshold:.0%}",
                'Trades': total_trades,
                'Winrate': winrate,
                'Expected_ROI': roi
            })
    
    results_df = pd.DataFrame(results)
    
    print("\n📊 RESULTADOS POR THRESHOLD:")
    print(results_df.to_string(index=False))
    
    # Find optimal threshold (best ROI with reasonable volume)
    results_df['Score'] = results_df['Expected_ROI'] * np.log(results_df['Trades'] + 1)
    best_idx = results_df['Score'].idxmax()
    best_threshold = results_df.iloc[best_idx]
    
    print(f"\n🏆 THRESHOLD ÓPTIMO: {best_threshold['Threshold']}")
    print(f"   Trades: {int(best_threshold['Trades'])}")
    print(f"   Winrate: {best_threshold['Winrate']:.1f}%")
    print(f"   Expected ROI: {best_threshold['Expected_ROI']:.1f}%")
    
    return results_df

def analyze_best_pairs(df):
    """Analyze best pairs for EMA Pullback"""
    print("\n💱 Analizando mejores pares...")
    
    pairs = df.groupby('pair').agg({
        'win': ['sum', 'count', 'mean']
    }).round(3)
    
    pairs.columns = ['Wins', 'Total', 'Winrate']
    pairs['Winrate'] = (pairs['Winrate'] * 100).round(1)
    
    # Filter pairs with at least 5 trades
    pairs = pairs[pairs['Total'] >= 5].sort_values('Winrate', ascending=False)
    
    print("\n🏆 TOP PARES (EMA Pullback):")
    print(pairs.head(5).to_string())
    
    return pairs

def analyze_best_hours(df):
    """Analyze best hours for EMA Pullback"""
    print("\n⏰ Analizando mejores horarios...")
    
    hours = df.groupby('hour').agg({
        'win': ['sum', 'count', 'mean']
    }).round(3)
    
    hours.columns = ['Wins', 'Total', 'Winrate']
    hours['Winrate'] = (hours['Winrate'] * 100).round(1)
    
    # Filter hours with at least 3 trades
    hours = hours[hours['Total'] >= 3].sort_values('Winrate', ascending=False)
    
    print("\n🏆 TOP HORARIOS (EMA Pullback):")
    print(hours.head(5).to_string())
    
    return hours

def plot_threshold_analysis(results_df):
    """Plot threshold analysis"""
    print("\n📈 Generando gráficos...")
    
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    
    # Plot 1: Winrate vs Threshold
    axes[0].plot(results_df['Threshold'], results_df['Winrate'], 
                marker='o', linewidth=2, markersize=8, color='steelblue')
    axes[0].axhline(y=52, color='r', linestyle='--', label='Breakeven (52%)')
    axes[0].set_xlabel('Threshold')
    axes[0].set_ylabel('Winrate (%)')
    axes[0].set_title('Winrate por Threshold')
    axes[0].legend()
    axes[0].grid(True, alpha=0.3)
    axes[0].tick_params(axis='x', rotation=45)
    
    # Plot 2: Volume vs Threshold
    axes[1].bar(results_df['Threshold'], results_df['Trades'], color='coral', alpha=0.7)
    axes[1].set_xlabel('Threshold')
    axes[1].set_ylabel('Número de Trades')
    axes[1].set_title('Volumen de Trades por Threshold')
    axes[1].grid(True, alpha=0.3)
    axes[1].tick_params(axis='x', rotation=45)
    
    plt.tight_layout()
    plt.savefig('threshold_analysis.png', dpi=150, bbox_inches='tight')
    print("✅ Gráfico guardado: threshold_analysis.png")

def main():
    print("="*60)
    print("🎯 OPTIMIZADOR DE THRESHOLD - EMA PULLBACK")
    print("="*60)
    
    # Load data
    df = load_ema_pullback_trades()
    
    if df is None or len(df) == 0:
        print("❌ No hay datos suficientes")
        return
    
    # Analyze threshold impact
    results_df = analyze_threshold_impact(df)
    
    # Analyze best pairs
    best_pairs = analyze_best_pairs(df)
    
    # Analyze best hours
    best_hours = analyze_best_hours(df)
    
    # Plot results
    try:
        plot_threshold_analysis(results_df)
    except Exception as e:
        print(f"⚠️ Error generando gráficos: {e}")
    
    print("\n" + "="*60)
    print("✅ ANÁLISIS COMPLETADO")
    print("="*60)

if __name__ == "__main__":
    main()
