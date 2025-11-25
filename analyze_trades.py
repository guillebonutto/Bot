"""
analyze_trades.py
=================
Script para analizar y visualizar trades guardados en CSV.
Genera reportes y estadísticas detalladas.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta, timezone
from pathlib import Path
import argparse


def load_trades(date=None):
    """
    Cargar trades de un día específico.
    
    Args:
        date: str en formato YYYYMMDD o None para hoy
    
    Returns:
        DataFrame con los trades
    """
    if date is None:
        date = datetime.now(timezone.utc).strftime("%Y%m%d")
    
    filepath = Path("logs") / "trades" / f"trades_{date}.csv"
    
    if not filepath.exists():
        print(f"❌ No se encontró archivo: {filepath}")
        return pd.DataFrame()
    
    try:
        df = pd.read_csv(filepath)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        return df
    except Exception as e:
        print(f"❌ Error cargando trades: {e}")
        return pd.DataFrame()


def print_trade_details(df, trade_id=None):
    """Mostrar detalles de un trade específico o todos."""
    if df.empty:
        print("❌ Sin datos de trades")
        return
    
    if trade_id:
        trade = df[df['trade_id'] == str(trade_id)]
        if trade.empty:
            print(f"❌ Trade {trade_id} no encontrado")
            return
    else:
        trade = df
    
    print("\n" + "=" * 100)
    print("📊 DETALLES DE TRADES")
    print("=" * 100)
    
    for _, row in trade.iterrows():
        print(f"\n📌 Trade ID: {row['trade_id']}")
        print(f"   ⏰ Timestamp: {row['timestamp']}")
        print(f"   📈 Par: {row['pair']} | TF: {row['timeframe']}")
        print(f"   🎯 Decisión: {row['decision']} | Score: {row['signal_score']}")
        print(f"   🔍 Patrón: {row['pattern_detected']}")
        print(f"   💵 Precio: {row['price']:.5f} | EMA: {row['ema']:.5f}")
        print(f"   📊 Indicadores:")
        print(f"      • RSI: {row['rsi'] if pd.notna(row['rsi']) else 'N/A'}")
        print(f"      • EMA_conf: {row['ema_conf']}")
        print(f"      • TF Signal: {row['tf_signal']}")
        print(f"      • ATR: {row['atr']:.5f}")
        print(f"      • Triangle: {row['triangle_active']} | Reversal: {row['reversal_candle']}")
        print(f"   🎯 Niveles:")
        print(f"      • Near Support: {row['near_support']} | Level: {row['support_level']}")
        print(f"      • Near Resistance: {row['near_resistance']} | Level: {row['resistance_level']}")
        print(f"   📈 HTF Signal: {row['htf_signal']}")
        print(f"   ✅ Resultado: {row['result']} | P/L: {row['profit_loss']}")
        print(f"   ⏱️ Expiración: {row['expiry_time']}s")
        if pd.notna(row['notes']) and row['notes']:
            print(f"   📝 Notas: {row['notes']}")


def print_summary_stats(df):
    """Mostrar estadísticas resumidas."""
    if df.empty:
        print("❌ Sin datos de trades")
        return
    
    total = len(df)
    wins = len(df[df['result'] == 'WIN'])
    losses = len(df[df['result'] == 'LOSS'])
    pending = len(df[df['result'] == 'PENDING'])
    
    winrate = (wins / (wins + losses) * 100) if (wins + losses) > 0 else 0
    total_profit = df[df['result'] == 'WIN']['profit_loss'].sum()
    total_loss = abs(df[df['result'] == 'LOSS']['profit_loss'].sum())
    net_result = total_profit - total_loss
    
    print("\n" + "=" * 80)
    print("📊 ESTADÍSTICAS RESUMIDAS")
    print("=" * 80)
    print(f"Total Operaciones: {total}")
    print(f"✅ Ganadas: {wins} ({wins/total*100:.1f}%)")
    print(f"❌ Perdidas: {losses} ({losses/total*100:.1f}%)")
    print(f"⏳ Pendientes: {pending}")
    print(f"\n📈 Winrate: {winrate:.1f}%")
    print(f"💰 Ganancia: ${total_profit:.2f}")
    print(f"💸 Pérdida: ${total_loss:.2f}")
    print(f"📊 Resultado Neto: ${net_result:.2f}")
    
    if (wins + losses) > 0:
        avg_win = total_profit / wins if wins > 0 else 0
        avg_loss = total_loss / losses if losses > 0 else 0
        profit_factor = total_profit / total_loss if total_loss > 0 else 0
        
        print(f"\n💵 Promedio por operación:")
        print(f"   • Ganancia promedio: ${avg_win:.2f}")
        print(f"   • Pérdida promedio: ${avg_loss:.2f}")
        print(f"   • Profit Factor: {profit_factor:.2f}")


def print_pair_stats(df):
    """Estadísticas por par."""
    if df.empty:
        print("❌ Sin datos de trades")
        return
    
    print("\n" + "=" * 80)
    print("📊 ESTADÍSTICAS POR PAR")
    print("=" * 80)
    
    for pair in df['pair'].unique():
        pair_df = df[df['pair'] == pair]
        total = len(pair_df)
        wins = len(pair_df[pair_df['result'] == 'WIN'])
        losses = len(pair_df[pair_df['result'] == 'LOSS'])
        wr = (wins / (wins + losses) * 100) if (wins + losses) > 0 else 0
        
        print(f"\n{pair}: {total} ops | {wins}W-{losses}L | WR: {wr:.1f}%")


def print_indicator_analysis(df):
    """Análisis de qué indicadores funcionan mejor."""
    if df.empty:
        print("❌ Sin datos de trades")
        return
    
    completed = df[(df['result'] == 'WIN') | (df['result'] == 'LOSS')]
    if completed.empty:
        print("❌ Sin trades completados para análisis")
        return
    
    print("\n" + "=" * 80)
    print("📊 ANÁLISIS DE INDICADORES")
    print("=" * 80)
    
    # RSI
    print("\n🔹 RSI:")
    rsi_data = completed[completed['rsi'].notna()]
    if len(rsi_data) > 0:
        rsi_wins = len(rsi_data[rsi_data['result'] == 'WIN'])
        rsi_total = len(rsi_data)
        rsi_wr = rsi_wins / rsi_total * 100
        print(f"   Trades con RSI: {rsi_total} | Winrate: {rsi_wr:.1f}%")
        print(f"   Oversold (<30): {len(rsi_data[rsi_data['rsi'] < 30])} trades")
        print(f"   Overbought (>70): {len(rsi_data[rsi_data['rsi'] > 70])} trades")
    
    # EMA_conf
    print("\n🔹 EMA_conf:")
    for val in [1, -1, 0]:
        ema_data = completed[completed['ema_conf'] == val]
        if len(ema_data) > 0:
            ema_wins = len(ema_data[ema_data['result'] == 'WIN'])
            ema_wr = ema_wins / len(ema_data) * 100
            label = "BUY" if val == 1 else "SELL" if val == -1 else "NEUTRAL"
            print(f"   {label}: {len(ema_data)} trades | WR: {ema_wr:.1f}%")
    
    # Triángulos
    print("\n🔹 Triangle:")
    tri_data = completed[completed['triangle_active'] == 1]
    if len(tri_data) > 0:
        tri_wins = len(tri_data[tri_data['result'] == 'WIN'])
        tri_wr = tri_wins / len(tri_data) * 100
        print(f"   Activos: {len(tri_data)} trades | WR: {tri_wr:.1f}%")
    
    # Reversal Candles
    print("\n🔹 Reversal Candles:")
    rev_data = completed[completed['reversal_candle'] == 1]
    if len(rev_data) > 0:
        rev_wins = len(rev_data[rev_data['result'] == 'WIN'])
        rev_wr = rev_wins / len(rev_data) * 100
        print(f"   Detectados: {len(rev_data)} trades | WR: {rev_wr:.1f}%")
    
    # Soporte/Resistencia
    print("\n🔹 Support/Resistance:")
    sup_data = completed[completed['near_support'] == True]
    res_data = completed[completed['near_resistance'] == True]
    if len(sup_data) > 0:
        sup_wins = len(sup_data[sup_data['result'] == 'WIN'])
        sup_wr = sup_wins / len(sup_data) * 100
        print(f"   Near Support: {len(sup_data)} trades | WR: {sup_wr:.1f}%")
    if len(res_data) > 0:
        res_wins = len(res_data[res_data['result'] == 'WIN'])
        res_wr = res_wins / len(res_data) * 100
        print(f"   Near Resistance: {len(res_data)} trades | WR: {res_wr:.1f}%")


def export_excel(df, output_file=None):
    """Exportar trades a Excel (versión CSV compatible con Excel)."""
    if df.empty:
        print("❌ Sin datos para exportar")
        return
    
    if output_file is None:
        date = df['timestamp'].iloc[0].strftime("%Y%m%d") if isinstance(df['timestamp'].iloc[0], str) else str(df['timestamp'].iloc[0])[:10]
        output_file = f"trades_export_{date}.csv"
    
    try:
        # Guardar como CSV pero con formato que Excel abre bien
        df.to_csv(output_file, index=False, encoding='utf-8-sig')
        
        # También intentar crear Excel si openpyxl está disponible
        try:
            import openpyxl
            excel_file = output_file.replace('.csv', '.xlsx')
            with pd.ExcelWriter(excel_file, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name='Trades', index=False)
                
                # Resumen
                summary_data = {
                    'Métrica': ['Total', 'Ganadas', 'Perdidas', 'Pendientes', 'Winrate %'],
                    'Valor': [
                        len(df),
                        len(df[df['result'] == 'WIN']),
                        len(df[df['result'] == 'LOSS']),
                        len(df[df['result'] == 'PENDING']),
                        (len(df[df['result'] == 'WIN']) / len(df[df['result'].isin(['WIN', 'LOSS'])]) * 100) 
                        if len(df[df['result'].isin(['WIN', 'LOSS'])]) > 0 else 0
                    ]
                }
                summary_df = pd.DataFrame(summary_data)
                summary_df.to_excel(writer, sheet_name='Summary', index=False)
            
            print(f"✅ Exportado a Excel: {excel_file}")
        except ImportError:
            print(f"✅ Exportado a CSV: {output_file}")
            print("   (Para Excel con opciones avanzadas: pip install openpyxl)")
        except Exception as e:
            print(f"✅ Exportado a CSV: {output_file}")
            print(f"   (Nota: {e})")
            
    except Exception as e:
        print(f"❌ Error exportando: {e}")


def main():
    parser = argparse.ArgumentParser(description='Analizar trades guardados')
    parser.add_argument('--date', default=None, help='Fecha en formato YYYYMMDD')
    parser.add_argument('--trade-id', default=None, help='ID específico de trade')
    parser.add_argument('--summary', action='store_true', help='Mostrar resumen')
    parser.add_argument('--pairs', action='store_true', help='Estadísticas por par')
    parser.add_argument('--indicators', action='store_true', help='Análisis de indicadores')
    parser.add_argument('--export', action='store_true', help='Exportar a Excel')
    parser.add_argument('--all', action='store_true', help='Mostrar todo')
    
    args = parser.parse_args()
    
    # Por defecto, mostrar resumen
    if not any([args.trade_id, args.summary, args.pairs, args.indicators, args.export, args.all]):
        args.summary = True
    
    df = load_trades(args.date)
    
    if df.empty:
        return
    
    if args.all or args.summary:
        print_summary_stats(df)
    
    if args.all or args.pairs:
        print_pair_stats(df)
    
    if args.all or args.indicators:
        print_indicator_analysis(df)
    
    if args.trade_id:
        print_trade_details(df, args.trade_id)
    elif args.all:
        print_trade_details(df)
    
    if args.export:
        export_excel(df)


if __name__ == "__main__":
    main()
