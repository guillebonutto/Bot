#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Integrar TradeLogger en bot_round_levels.py (Fixed)
"""

# Leer archivo
with open('bots/bot_round_levels.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# 1. Agregar import del TradeLogger
import_added = False
for i, line in enumerate(lines):
    if 'from dotenv import load_dotenv' in line and not import_added:
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
    if 'if signal["direction"] == "BUY":' in line and not logging_added:
        # Insertar logging ANTES de esta línea
        indent = ' ' * 16  # Indentación correcta (dentro del if signal)
        
        # Preparar el bloque de código
        code_block = [
            f'{indent}# Generar trade_id y loguear operación\n',
            f'{indent}import uuid\n',
            f'{indent}trade_id = str(uuid.uuid4())[:8]\n',
            f'{indent}trade_logger.log_trade({{\n',
            f'{indent}    "timestamp": datetime.now(),\n',
            f'{indent}    "trade_id": trade_id,\n',
            f'{indent}    "pair": signal["pair"],\n',
            f'{indent}    "timeframe": "M5",\n',
            f'{indent}    "decision": signal["direction"],\n',
            f'{indent}    "signal_score": 1.0,\n',
            f'{indent}    "pattern_detected": "Round Level",\n',
            f'{indent}    "price": signal["price"],\n',
            f'{indent}    "support_level": signal.get("level", 0),\n',
            f'{indent}    "expiry_time": DURATION,\n',
            f'{indent}    "result": "PENDING",\n',
            f'{indent}    "notes": "Round level distance=" + str(round(signal.get("distance", 0)*10000, 1)) + " pips"\n',
            f'{indent}}})\n',
            f'{indent}\n'
        ]
        
        # Insertar líneas en orden inverso
        for code_line in reversed(code_block):
            lines.insert(i, code_line)
            
        logging_added = True
        print(f"✅ Logging agregado antes de línea {i}")
        break

# Guardar
with open('bots/bot_round_levels.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)

print("\n✅ bot_round_levels.py actualizado con TradeLogger")
