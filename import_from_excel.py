"""
Script para importar trades desde cuenta_real.xlsx a los CSVs de logs/trades/
"""
import pandas as pd
from datetime import datetime
from pathlib import Path
import csv
import uuid

def import_from_excel(excel_path='cuenta_real.xlsx', logs_dir='logs/trades'):
    """Importar trades desde Excel a CSVs."""
    
    print("🔄 Importando desde cuenta_real.xlsx...")
    print("="*60)
    
    # Leer Excel
    try:
        df = pd.read_excel(excel_path)
    except Exception as e:
        print(f"❌ Error leyendo Excel: {e}")
        return
    
    print(f"📊 Total de trades en Excel: {len(df)}")
    
    # Convertir fechas
    df['open'] = pd.to_datetime(df['open'])
    df['time'] = pd.to_timedelta(df['time'].astype(str))
    df['timestamp'] = df['open'] + df['time']
    
    # Mostrar rango
    print(f"📅 Rango: {df['timestamp'].min()} - {df['timestamp'].max()}")
    
    # Agrupar por fecha
    df['date_str'] = df['timestamp'].dt.strftime('%Y%m%d')
    trades_by_date = df.groupby('date_str')
    
    logs_path = Path(logs_dir)
    logs_path.mkdir(parents=True, exist_ok=True)
    
    headers = [
        'timestamp', 'trade_id', 'pair', 'timeframe', 'decision', 'signal_score',
        'pattern_detected', 'price', 'ema', 'rsi', 'ema_conf', 'tf_signal', 'atr',
        'triangle_active', 'reversal_candle', 'near_support', 'near_resistance',
        'support_level', 'resistance_level', 'htf_signal', 'result', 'profit_loss',
        'expiry_time', 'notes'
    ]
    
    total_added = 0
    files_created = 0
    
    for date_str, group in trades_by_date:
        filename = logs_path / f"trades_{date_str}.csv"
        
        # Leer existentes si hay
        existing_trades = []
        existing_ids = set()
        
        if filename.exists():
            with open(filename, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                existing_trades = list(reader)
                # Crear set de timestamps existentes para evitar duplicados
                for trade in existing_trades:
                    existing_ids.add(trade['timestamp'])
        
        # Convertir trades del grupo
        new_count = 0
        for _, row in group.iterrows():
            timestamp_str = row['timestamp'].strftime('%Y-%m-%d %H:%M:%S')
            
            # Evitar duplicados
            if timestamp_str in existing_ids:
                continue
            
            # Parsear timeframe
            expiration = str(row.get('expiration', '5min'))
            duration_match = pd.Series([expiration]).str.extract(r'(\d+)')[0][0]
            duration = int(duration_match) if duration_match else 5
            
            # Determinar resultado
            profit = row.get('profit', 0)
            if pd.isna(profit):
                result = 'PENDING'
                profit_loss = 0
            elif profit > 0:
                result = 'WIN'
                profit_loss = profit
            elif profit < 0:
                result = 'LOSS'
                profit_loss = profit
            else:
                result = 'LOSS'
                profit_loss = -row.get('trade amount', 1.0)
            
            trade_row = {
                'timestamp': timestamp_str,
                'trade_id': str(uuid.uuid4())[:8],
                'pair': row.get('asset', ''),
                'timeframe': expiration,
                'decision': row.get('direction', ''),
                'signal_score': '',
                'pattern_detected': 'Importado de Excel',
                'price': row.get('open price', 0),
                'ema': '',
                'rsi': '',
                'ema_conf': 1 if row.get('direction') == 'BUY' else -1,
                'tf_signal': '',
                'atr': '',
                'triangle_active': '',
                'reversal_candle': '',
                'near_support': '',
                'near_resistance': '',
                'support_level': '',
                'resistance_level': '',
                'htf_signal': '',
                'result': result,
                'profit_loss': profit_loss,
                'expiry_time': duration * 60,
                'notes': f"Importado de cuenta_real.xlsx"
            }
            
            existing_trades.append(trade_row)
            existing_ids.add(timestamp_str)
            new_count += 1
        
        # Escribir archivo
        if new_count > 0:
            with open(filename, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=headers)
                writer.writeheader()
                writer.writerows(existing_trades)
            
            print(f"✅ {filename.name}: +{new_count} trades")
            total_added += new_count
            files_created += 1
    
    print("\n" + "="*60)
    print(f"✅ Importación completada")
    print(f"   Trades agregados: {total_added}")
    print(f"   Archivos actualizados: {files_created}")

if __name__ == "__main__":
    import_from_excel()
