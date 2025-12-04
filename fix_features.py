#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Fix feature order in bot_ema_pullback.py"""

# Leer archivo
with open('bots/bot_ema_pullback.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Buscar y reemplazar las líneas específicas
modified = False
for i, line in enumerate(lines):
    # Línea 91 y 104
    if 'features = [[c, e8, e21, e55, duration/60, pair_idx]]' in line:
        lines[i] = line.replace(
            'features = [[c, e8, e21, e55, duration/60, pair_idx]]',
            'features = [[c, duration/60, pair_idx, e8, e21, e55]]'
        )
        modified = True
        print(f"✅ Línea {i+1} modificada")

# Guardar
if modified:
    with open('bots/bot_ema_pullback.py', 'w', encoding='utf-8') as f:
        f.writelines(lines)
    print(f"\n✅ Archivo guardado con {sum(1 for line in lines if 'features = [[c, duration/60, pair_idx, e8, e21, e55]]' in line)} cambios")
else:
    print("⚠️ No se encontraron líneas para modificar")
