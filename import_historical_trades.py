"""
Script simplificado para importar trades históricos
"""
import re
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path
import csv
import uuid

def parse_telegram_messages(filepath):
    """Parsear mensajes de Telegram - versión simplificada."""
    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    trades = []
    current_signal = None
    
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        
        # Detectar inicio de señal
        if '📌 SEÑAL DETECTADA' in line:
            # Buscar timestamp en línea anterior
            if i > 0:
                prev_line = lines[i-1].strip()
                timestamp_match = re.search(r'\[(\d{2}/\d{2}/\d{4} \d{2}:\d{2})\]', prev_line)
                if timestamp_match:
                    timestamp_str = timestamp_match.group(1)
                    timestamp = datetime.strptime(timestamp_str, '%d/%m/%Y %H:%M')
                    
                    # Buscar datos de la señal en las siguientes líneas
                    signal_data = {'timestamp': timestamp}
                    
                    for j in range(i, min(i+15, len(lines))):
                        l = lines[j].strip()
                        
                        if l.startswith('Par:'):
                            signal_data['pair'] = l.split(':', 1)[1].strip()
                        elif l.startswith('TF:'):
                            signal_data['timeframe'] = l.split(':', 1)[1].strip()
                        elif l.startswith('Dirección:'):
                            signal_data['direction'] = l.split(':', 1)[1].strip()
                        elif l.startswith('Score:'):
                            signal_data['score'] = int(l.split(':', 1)[1].strip())
                        elif l.startswith('Patrón:'):
                            pattern = l.split(':', 1)[1].strip()
                            signal_data['pattern'] = pattern if pattern != 'None' else 'EMA Pullback'
                        elif '💰 Precio:' in l:
                            price_match = re.search(r'([\d.]+)', l)
                            if price_match:
                                signal_data['price'] = float(price_match.group(1))
                        elif '📊 EMA:' in l:
                            ema_match = re.search(r'([\d.]+)', l)
                            if ema_match:
                                signal_data['ema'] = float(ema_match.group(1))
                        elif '⏱️ Duración:' in l:
                            dur_match = re.search(r'(\d+)min', l)
                            if dur_match:
                                signal_data['duration'] = int(dur_match.group(1))
                        elif '💵 Monto:' in l:
                            amt_match = re.search(r'\$([\d.]+)', l)
                            if amt_match:
                                signal_data['amount'] = float(amt_match.group(1))
                    
                    current_signal = signal_data
        
        # Detectar resultado
        elif current_signal and ('✅ GANADA' in line or '❌ PERDIDA' in line):
            # Extraer profit/loss
            if '✅ GANADA' in line:
                profit_match = re.search(r'\+\$([\d.]+)', line)
                if profit_match:
                    current_signal['result'] = 'WIN'
                    current_signal['profit_loss'] = float(profit_match.group(1))
            elif '❌ PERDIDA' in line:
                loss_match = re.search(r'-\$([\d.]+)', line)
                if loss_match:
                    current_signal['result'] = 'LOSS'
                    current_signal['profit_loss'] = -float(loss_match.group(1))
            
            # Agregar trade completo
            if 'pair' in current_signal and 'direction' in current_signal:
                trades.append(current_signal)
            
            current_signal = None
        
        i += 1
    
    return trades

def add_to_excel(trades, excel_path='cuenta_real.xlsx'):
    """Agregar trades al Excel."""
    try:
        df_existing = pd.read_excel(excel_path)
    except:
        df_existing = pd.DataFrame()
    
    new_rows = []
    for trade in trades:
        duration = trade.get('duration', 5)
        close_time = trade['timestamp'] + timedelta(minutes=duration)
        
        row = {
            'direction': trade.get('direction', ''),
            'expiration': f"{duration}min",
            'asset': trade.get('pair', ''),
            'open': trade['timestamp'].strftime('%Y-%m-%d'),
            'time': trade['timestamp'].strftime('%H:%M:%S'),
            'close': close_time.strftime('%Y-%m-%d'),
            'time.1': close_time.strftime('%H:%M:%S'),
            'open price': trade.get('price', 0),
            'close price': '',
            'trade amount': trade.get('amount', 1.0),
            'profit': trade.get('profit_loss', 0),
            'label': trade.get('result', 'PENDING')
        }
        new_rows.append(row)
    
    df_new = pd.DataFrame(new_rows)
    df_combined = pd.concat([df_existing, df_new], ignore_index=True)
    df_combined.to_excel(excel_path, index=False)
    
    print(f"✅ Agregados {len(new_rows)} trades a {excel_path}")
    return len(new_rows)

def add_to_csv_logs(trades, logs_dir='logs/trades'):
    """Agregar trades a los CSVs."""
    logs_path = Path(logs_dir)
    logs_path.mkdir(parents=True, exist_ok=True)
    
    # Agrupar por fecha
    trades_by_date = {}
    for trade in trades:
        date_str = trade['timestamp'].strftime('%Y%m%d')
        if date_str not in trades_by_date:
            trades_by_date[date_str] = []
        trades_by_date[date_str].append(trade)
    
    headers = [
        'timestamp', 'trade_id', 'pair', 'timeframe', 'decision', 'signal_score',
        'pattern_detected', 'price', 'ema', 'rsi', 'ema_conf', 'tf_signal', 'atr',
        'triangle_active', 'reversal_candle', 'near_support', 'near_resistance',
        'support_level', 'resistance_level', 'htf_signal', 'result', 'profit_loss',
        'expiry_time', 'notes'
    ]
    
    total_added = 0
    
    for date_str, date_trades in trades_by_date.items():
        filename = logs_path / f"trades_{date_str}.csv"
        
        # Leer existentes
        existing_trades = []
        if filename.exists():
            with open(filename, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                existing_trades = list(reader)
        
        # Agregar nuevos
        for trade in date_trades:
            row = {
                'timestamp': trade['timestamp'].strftime('%Y-%m-%d %H:%M:%S'),
                'trade_id': str(uuid.uuid4())[:8],
                'pair': trade.get('pair', ''),
                'timeframe': trade.get('timeframe', 'M5'),
                'decision': trade.get('direction', ''),
                'signal_score': trade.get('score', 0),
                'pattern_detected': trade.get('pattern', 'EMA Pullback'),
                'price': trade.get('price', 0),
                'ema': trade.get('ema', 0),
                'rsi': '',
                'ema_conf': 1 if trade.get('direction') == 'BUY' else -1,
                'tf_signal': '',
                'atr': '',
                'triangle_active': '',
                'reversal_candle': '',
                'near_support': '',
                'near_resistance': '',
                'support_level': '',
                'resistance_level': '',
                'htf_signal': '',
                'result': trade.get('result', 'PENDING'),
                'profit_loss': trade.get('profit_loss', 0),
                'expiry_time': trade.get('duration', 5) * 60,
                'notes': f"Importado de Telegram"
            }
            existing_trades.append(row)
        
        # Escribir
        with open(filename, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=headers)
            writer.writeheader()
            writer.writerows(existing_trades)
        
        print(f"✅ {filename.name}: +{len(date_trades)} trades")
        total_added += len(date_trades)
    
    return total_added

def main():
    print("🔄 Importando trades históricos...")
    print("="*60)
    
    print("\n📖 Parseando Operaciones_sin_registrar.txt...")
    trades = parse_telegram_messages('Operaciones_sin_registrar.txt')
    print(f"   ✅ Encontrados {len(trades)} trades")
    
    if not trades:
        print("❌ No se encontraron trades")
        return
    
    # Resumen
    wins = sum(1 for t in trades if t.get('result') == 'WIN')
    losses = sum(1 for t in trades if t.get('result') == 'LOSS')
    total_pnl = sum(t.get('profit_loss', 0) for t in trades)
    
    print(f"\n📊 Resumen:")
    print(f"   Período: {trades[0]['timestamp'].strftime('%d/%m/%Y')} - {trades[-1]['timestamp'].strftime('%d/%m/%Y')}")
    print(f"   Wins: {wins} | Losses: {losses}")
    print(f"   P&L: ${total_pnl:.2f}")
    
    print(f"\n📊 Agregando a cuenta_real.xlsx...")
    add_to_excel(trades)
    
    print(f"\n📁 Agregando a logs/trades/...")
    add_to_csv_logs(trades)
    
    print("\n" + "="*60)
    print(f"✅ Importación completada: {len(trades)} trades")

if __name__ == "__main__":
    main()
