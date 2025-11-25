"""
convert_json_to_csv.py
=====================
Convierte los históricos de JSON a CSV (formato que espera el sistema).
"""

import json
import csv
from pathlib import Path
import pandas as pd


def convert_json_to_csv():
    """Convierte históricos JSON a CSV."""
    print("\n" + "=" * 70)
    print("📝 CONVIRTIENDO JSON a CSV")
    print("=" * 70)
    
    history_dir = Path("history")
    if not history_dir.exists():
        print("❌ Carpeta 'history' no existe")
        return
    
    converted = 0
    
    # Recorrer directorios de pares
    for pair_dir in history_dir.iterdir():
        if not pair_dir.is_dir():
            continue
        
        pair_name = pair_dir.name
        print(f"\n📊 {pair_name}:")
        
        # Recorrer archivos JSON de timeframes
        for json_file in pair_dir.glob("*.json"):
            tf_name = json_file.stem  # M5, M15, etc
            
            try:
                # Leer JSON
                with open(json_file, 'r') as f:
                    data = json.load(f)
                
                candles = data.get('candles', [])
                if not candles:
                    print(f"   ⚠️  {tf_name}: Sin velas")
                    continue
                
                # Convertir a DataFrame
                df = pd.DataFrame(candles)
                
                # Crear nombre del CSV (formato esperado: PAIR_TF.csv)
                csv_name = f"{pair_name}_{tf_name}.csv"
                csv_path = history_dir / csv_name
                
                # Guardar CSV
                df.to_csv(csv_path, index=False)
                
                print(f"   ✅ {tf_name}: {len(candles)} velas → {csv_name}")
                converted += 1
            
            except Exception as e:
                print(f"   ❌ {tf_name}: Error - {e}")
    
    print(f"\n{'=' * 70}")
    print(f"✅ {converted} archivos convertidos")
    print(f"   Los CSV están listos en: {history_dir.absolute()}")
    print(f"{'=' * 70}\n")


if __name__ == "__main__":
    convert_json_to_csv()
