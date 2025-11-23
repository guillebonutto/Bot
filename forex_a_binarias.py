"""
forex_to_binary_converter.py

Convierte datos de operaciones de Forex al formato de Opciones Binarias
para entrenamiento de ML.

Diferencias clave:
- Forex: Ganancia proporcional al movimiento (profit en pips/USD)
- Binarias: Todo o nada (dirección correcta = +85%, incorrecta = -100%)

Uso:
    python forex_to_binary_converter.py --input forex_trades.xlsx --out forex_adapted.csv
"""

import pandas as pd
import numpy as np
import argparse
from datetime import datetime


def parse_datetime(date_col, time_col):
    """Combina columnas de fecha y hora"""
    try:
        combined = pd.to_datetime(date_col.astype(str) + ' ' + time_col.astype(str))
        return combined
    except:
        return pd.to_datetime(date_col)


def calculate_duration_seconds(open_dt, close_dt):
    """Calcula duración en segundos"""
    try:
        return (close_dt - open_dt).dt.total_seconds()
    except:
        return 300  # default 5 minutos


def forex_to_binary_options(df, max_duration_minutes=60):
    """
    Convierte operaciones de Forex a formato de Opciones Binarias

    Args:
        df: DataFrame con columnas de Forex
        max_duration_minutes: Filtrar operaciones más largas (default 60min)

    Returns:
        DataFrame adaptado para opciones binarias
    """
    print("=" * 70)
    print("🔄 CONVERSIÓN FOREX → OPCIONES BINARIAS")
    print("=" * 70)
    print(f"\n📊 Datos originales:")
    print(f"   Total operaciones: {len(df)}")
    print(f"   Columnas: {df.columns.tolist()}\n")

    # 1. Normalizar nombres de columnas
    df.columns = df.columns.str.lower().str.strip()

    # 2. Parsear timestamps
    print("⏰ Parseando timestamps...")

    # Detectar formato de tiempo
    if 'open' in df.columns and 'time' in df.columns:
        # Caso: columnas separadas 'open' (fecha) y 'time' (hora)
        df['open_time'] = parse_datetime(df['open'], df['time'])

        # Para close, buscar la segunda columna 'time' (time.1)
        if 'close' in df.columns:
            time_cols = [c for c in df.columns if 'time' in c]
            if len(time_cols) >= 2:
                df['close_time'] = parse_datetime(df['close'], df[time_cols[1]])
            else:
                # Si no hay time.1, asumir misma fecha con hora de cierre
                df['close_time'] = parse_datetime(df['close'], df['time'])
    else:
        # Fallback: buscar columnas que contengan 'open' y 'close'
        time_cols = [c for c in df.columns if 'time' in c.lower()]
        if len(time_cols) >= 2:
            df['open_time'] = pd.to_datetime(df[time_cols[0]])
            df['close_time'] = pd.to_datetime(df[time_cols[1]])

    # 3. Calcular duración
    print("⏱️ Calculando duraciones...")
    df['duration_seconds'] = calculate_duration_seconds(df['open_time'], df['close_time'])
    df['duration_minutes'] = df['duration_seconds'] / 60

    # Estadísticas de duración
    print(f"\n📊 Estadísticas de duración:")
    print(f"   Media: {df['duration_minutes'].mean():.1f} min")
    print(f"   Mediana: {df['duration_minutes'].median():.1f} min")
    print(f"   Min: {df['duration_minutes'].min():.1f} min")
    print(f"   Max: {df['duration_minutes'].max():.1f} min")

    # 4. FILTRAR operaciones cortas (más parecidas a binarias)
    print(f"\n🔍 Filtrando operaciones < {max_duration_minutes} minutos...")
    original_len = len(df)
    df = df[df['duration_minutes'] <= max_duration_minutes].copy()
    print(f"   Operaciones restantes: {len(df)} ({len(df) / original_len * 100:.1f}%)")

    if len(df) == 0:
        print("❌ No hay operaciones que cumplan el criterio de duración")
        return pd.DataFrame()

    # 5. VERIFICAR Y CORREGIR LABEL
    print("\n🏷️ Verificando labels...")

    if 'label' in df.columns:
        # Verificar que label sea consistente con profit
        if 'profit' in df.columns:
            # Calcular label correcto basado en profit
            correct_label = (df['profit'] > 0).astype(int)

            # Comparar con label existente
            if 'label' in df.columns:
                mismatches = (df['label'] != correct_label).sum()
                if mismatches > 0:
                    print(f"   ⚠️ Detectadas {mismatches} inconsistencias entre label y profit")
                    print(f"   Corrigiendo labels basándose en profit...")
                    df['label'] = correct_label
    else:
        # Crear label desde profit o dirección + precio
        if 'profit' in df.columns:
            df['label'] = (df['profit'] > 0).astype(int)
            print("   ✅ Label creado desde columna 'profit'")
        elif 'open price' in df.columns and 'close price' in df.columns and 'direction' in df.columns:
            def calc_label(row):
                price_change = row['close price'] - row['open price']
                if row['direction'].upper() in ['BUY', 'CALL']:
                    return 1 if price_change > 0 else 0
                else:  # SELL/PUT
                    return 1 if price_change < 0 else 0

            df['label'] = df.apply(calc_label, axis=1)
            print("   ✅ Label calculado desde dirección + precios")

    # 6. Calcular winrate
    winrate = df['label'].mean()
    wins = df['label'].sum()
    losses = (df['label'] == 0).sum()

    print(f"\n📈 Distribución de resultados:")
    print(f"   Wins: {wins} ({winrate * 100:.1f}%)")
    print(f"   Losses: {losses} ({(1 - winrate) * 100:.1f}%)")

    if winrate < 0.50:
        print(f"\n⚠️⚠️⚠️ ADVERTENCIA: Winrate < 50%")
        print(f"   El modelo aprenderá a perder si entrenas con estos datos")
        print(f"   Considera invertir las señales o filtrar mejor")

    # 7. Crear columnas adicionales para compatibilidad con binarias
    result_df = pd.DataFrame()

    # Columnas esenciales
    result_df['direction'] = df['direction']
    result_df['asset'] = df['asset'] if 'asset' in df.columns else 'UNKNOWN'
    result_df['open_time'] = df['open_time']
    result_df['open_price'] = df['open price']
    result_df['label'] = df['label']

    # Simular expiration (usar duración real redondeada)
    # Redondear a valores típicos de binarias: 60, 120, 300, 600, 900, 1800
    typical_expirations = [60, 120, 300, 600, 900, 1800]

    def round_to_typical(seconds):
        return min(typical_expirations, key=lambda x: abs(x - seconds))

    result_df['expiration'] = df['duration_seconds'].apply(
        lambda x: f"S{int(round_to_typical(x))}"
    )

    # Trade amount (normalizar si existe)
    if 'trade amount' in df.columns:
        result_df['trade_amount'] = df['trade amount']
    else:
        result_df['trade_amount'] = 1.0  # default

    # Features temporales
    result_df['hour'] = df['open_time'].dt.hour
    result_df['weekday'] = df['open_time'].dt.dayofweek
    result_df['is_weekend'] = (result_df['weekday'] >= 5).astype(int)

    # Marcar como datos de Forex (para dar menos peso en entrenamiento)
    result_df['source'] = 'forex'

    # 8. Estadísticas por asset
    print(f"\n📊 Distribución por asset:")
    asset_stats = result_df.groupby('asset').agg({
        'label': ['count', 'mean']
    }).round(3)
    asset_stats.columns = ['Operaciones', 'Winrate']
    print(asset_stats.to_string())

    # 9. Estadísticas por dirección
    print(f"\n📊 Distribución por dirección:")
    dir_stats = result_df.groupby('direction').agg({
        'label': ['count', 'mean']
    }).round(3)
    dir_stats.columns = ['Operaciones', 'Winrate']
    print(dir_stats.to_string())

    print("\n" + "=" * 70)
    print("✅ CONVERSIÓN COMPLETADA")
    print("=" * 70)
    print(f"Operaciones finales: {len(result_df)}")
    print(f"Winrate global: {result_df['label'].mean() * 100:.1f}%")
    print(f"Columnas: {result_df.columns.tolist()}")
    print("=" * 70 + "\n")

    return result_df


# ---------------------------
# CLI
# ---------------------------

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Convierte operaciones de Forex a formato de Opciones Binarias'
    )
    parser.add_argument('--input', '-i', required=True,
                        help='Archivo Excel/CSV con operaciones de Forex')
    parser.add_argument('--out', '-o', default='forex_adapted.csv',
                        help='Archivo CSV de salida')
    parser.add_argument('--max-duration', '-d', type=int, default=60,
                        help='Duración máxima en minutos (default: 60)')
    parser.add_argument('--combine-with', '-c',
                        help='Archivo de opciones binarias reales para combinar')
    args = parser.parse_args()

    # Cargar datos de Forex
    print(f"📂 Cargando {args.input}...\n")
    if args.input.endswith('.xlsx'):
        df_forex = pd.read_excel(args.input)
    else:
        df_forex = pd.read_csv(args.input)

    # Convertir
    df_converted = forex_to_binary_options(df_forex, max_duration_minutes=args.max_duration)

    if df_converted.empty:
        print("❌ Error: No se generaron datos convertidos")
        exit(1)

    # Combinar con datos reales si se especifica
    if args.combine_with:
        print(f"\n🔗 Combinando con {args.combine_with}...")

        if args.combine_with.endswith('.xlsx'):
            df_real = pd.read_excel(args.combine_with)
        else:
            df_real = pd.read_csv(args.combine_with)

        # Normalizar columnas de datos reales
        df_real.columns = df_real.columns.str.lower().str.strip()

        # Marcar como datos reales
        if 'source' not in df_real.columns:
            df_real['source'] = 'binary_real'

        # Asegurar que tengan las mismas columnas
        common_cols = list(set(df_converted.columns) & set(df_real.columns))
        df_converted_subset = df_converted[common_cols]
        df_real_subset = df_real[common_cols]

        # Combinar
        df_final = pd.concat([df_converted_subset, df_real_subset], ignore_index=True)

        print(f"\n📊 Dataset combinado:")
        print(f"   Forex: {len(df_converted)} operaciones")
        print(f"   Binary real: {len(df_real)} operaciones")
        print(f"   Total: {len(df_final)} operaciones")
        print(f"   Winrate global: {df_final['label'].mean() * 100:.1f}%")
    else:
        df_final = df_converted

    # Guardar
    df_final.to_csv(args.out, index=False)
    print(f"\n💾 Archivo guardado: {args.out}")
    print(f"   {len(df_final)} operaciones, {len(df_final.columns)} columnas\n")

    print("🚀 Siguiente paso:")
    print(f"   python pre_entrenamiento_IA.py --input {args.out} --out enriched.csv --train")