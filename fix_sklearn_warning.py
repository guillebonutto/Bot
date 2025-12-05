#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Fix sklearn warning by using DataFrame for features"""

# Leer archivo
with open('bots/bot_ema_pullback.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Buscar la línea donde se importa pandas
import_line = None
for i, line in enumerate(lines):
    if 'import pandas as pd' in line:
        import_line = i
        break

# Buscar y reemplazar las líneas de features
modified = False
for i, line in enumerate(lines):
    if 'features = [[c, duration/60, pair_idx, e8, e21, e55]]' in line:
        # Reemplazar con DataFrame
        indent = ' ' * 12  # 12 espacios de indentación
        lines[i] = f'{indent}# Crear DataFrame con nombres de columnas para evitar warning\n'
        lines.insert(i+1, f'{indent}import pandas as pd\n')
        lines.insert(i+2, f'{indent}features = pd.DataFrame([[c, duration/60, pair_idx, e8, e21, e55]], \n')
        lines.insert(i+3, f'{indent}                        columns=[\'price\', \'duration_minutes\', \'pair_idx\', \'ema8\', \'ema21\', \'ema55\'])\n')
        modified = True
        print(f"✅ Línea {i+1} modificada")
        break  # Solo modificar la primera ocurrencia

# Guardar
if modified:
    with open('bots/bot_ema_pullback.py', 'w', encoding='utf-8') as f:
        f.writelines(lines)
    print(f"\n✅ Archivo guardado")
else:
    print("⚠️ No se encontraron líneas para modificar")
