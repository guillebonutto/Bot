#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Integrar TradeLogger en bot_ema_pullback.py (Fixed)
"""

# Leer archivo
with open('bots/bot_ema_pullback.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# 1. Agregar import del TradeLogger
import_added = False
for i, line in enumerate(lines):
    if 'from telegram_formatter import' in line and not import_added:
        lines.insert(i+1, '\n')
        lines.insert(i+2, '# Importar trade logger\n')
        lines.insert(i+3, 'import sys\n')
        lines.insert(i+4, 'sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))\n')
        lines.insert(i+5, 'from trade_logger import trade_logger\n')
        import_added = True
        print(f"✅ Import agregado en línea {i+1}")
        break

# 2. Buscar donde insertar el logging (ANTES del if direction == BUY)
logging_added = False
for i, line in enumerate(lines):
    # Buscamos la línea que dice 'if signal["direction"] == "BUY":'
    if 'if signal["direction"] == "BUY":' in line and not logging_added:
        # Insertar logging ANTES de esta línea
        indent = ' ' * 28  # Indentación correcta (dentro del if signal and not traded)
        
        # Preparar el bloque de código
        code_block = [
            f'{indent}# Generar trade_id y loguear operación\n',
            f'{indent}import uuid\n',
            f'{indent}trade_id = str(uuid.uuid4())[:8]\n',
            f'{indent}trade_logger.log_trade({{\n',
            f'{indent}    "timestamp": datetime.now(),\n',
            f'{indent}    "trade_id": trade_id,\n',
            f'{indent}    "pair": pair,\n',
            f'{indent}    "timeframe": name,\n',
            f'{indent}    "decision": signal["direction"],\n',
            f'{indent}    "signal_score": signal.get("prob", 1.0),\n',
            f'{indent}    "pattern_detected": "EMA Pullback",\n',
            f'{indent}    "price": c,\n',
            f'{indent}    "ema": e8,\n',
            f'{indent}    "ema_conf": 1 if e8 > e21 else -1,\n',
            f'{indent}    "expiry_time": duration,\n',
            f'{indent}    "result": "PENDING",\n',
            f'{indent}    "notes": "ML_prob=" + str(round(signal.get("prob", 1.0)*100, 1)) + "%"\n',
            f'{indent}}})\n',
            f'{indent}\n'
        ]
        
        # Insertar líneas en orden inverso para mantener el índice i
        for code_line in reversed(code_block):
            lines.insert(i, code_line)
            
        logging_added = True
        print(f"✅ Logging agregado antes de línea {i}")
        break

# 3. Buscar donde se verifica el resultado y actualizar el log
for i, line in enumerate(lines):
    if 'balance_after = await api.balance()' in line:
        # Buscar las líneas de WIN y LOSS después de esto
        for j in range(i, min(i+40, len(lines))):
            if 'profit = balance_after - balance_before' in lines[j]:
                # Agregar actualización de trade_logger después del print de GANÓ
                # Buscamos la línea siguiente que suele ser el print
                indent = ' ' * 36
                lines.insert(j+2, f'{indent}trade_logger.update_trade_result(trade_id, "WIN", profit)\n')
                print(f"✅ Update WIN agregado en línea {j+2}")
            elif 'loss = balance_before - balance_after' in lines[j]:
                # Agregar actualización de trade_logger después del print de PERDIÓ
                indent = ' ' * 36
                lines.insert(j+2, f'{indent}trade_logger.update_trade_result(trade_id, "LOSS", -loss)\n')
                print(f"✅ Update LOSS agregado en línea {j+2}")
                break
        break

# Guardar
with open('bots/bot_ema_pullback.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)

print("\n✅ bot_ema_pullback.py actualizado con TradeLogger")
