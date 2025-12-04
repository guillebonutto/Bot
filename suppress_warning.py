#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Add warning suppression to bot_ema_pullback.py"""

# Leer archivo
with open('bots/bot_ema_pullback.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Buscar la línea "load_dotenv()"
for i, line in enumerate(lines):
    if 'load_dotenv()' in line:
        # Insertar las líneas de supresión de warnings después de load_dotenv()
        lines.insert(i+1, '\n')
        lines.insert(i+2, '# Suprimir warning de sklearn sobre nombres de features\n')
        lines.insert(i+3, 'import warnings\n')
        lines.insert(i+4, 'warnings.filterwarnings(\'ignore\', category=UserWarning, module=\'sklearn\')\n')
        print(f"✅ Warning suppression agregado después de línea {i+1}")
        break

# Guardar
with open('bots/bot_ema_pullback.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)

print("✅ Archivo guardado")
