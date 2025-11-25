"""
GUÍA PRÁCTICA - Cómo Usar el Sistema en la Vida Real
=====================================================
Instrucciones paso a paso para integrar todo.
"""

# =============================================================================
# PASO 1: LANZAR EL BOT
# =============================================================================

"""
Ejecuta tu bot como siempre:

    cd c:\Users\nico\Downloads\PocketOptions\Bot
    python main.py

El logging de trades sucede AUTOMÁTICAMENTE.
No necesitas hacer nada especial.

Cada operación se registra en:
    logs/trades/trades_YYYYMMDD.csv

Ejemplo de lo que se guarda:
    - 10:15:30 BUY EURUSD_otc M15 score=5 → WIN +$12.50
    - 10:20:45 SELL GBPUSD_otc M5 score=3 → LOSS
    - 10:25:10 BUY USDJPY_otc M30 score=6 → WIN +$15.00
"""


# =============================================================================
# PASO 2: MONITOREO EN TIEMPO REAL (OPCIONAL)
# =============================================================================

"""
Mientras el bot está corriendo, en otra terminal:

    python trades_dashboard.py

Verás un dashboard actualizado cada 5 segundos con:
    - Total de trades ejecutados
    - Últimos 10 trades
    - Winrate actual
    - Performance por par
    - Patrones más efectivos

Este dashboard es ideal para monitoreo mientras el bot corre.
"""


# =============================================================================
# PASO 3: ANÁLISIS AL FINAL DEL DÍA
# =============================================================================

"""
Después de que el bot termina (o cada hora), ejecuta:

    python analyze_trades.py

Verás:
    ================================================================================
    📊 ESTADÍSTICAS RESUMIDAS
    ================================================================================
    Total Operaciones: 47
    ✅ Ganadas: 33 (70.2%)
    ❌ Perdidas: 14 (29.8%)
    ⏳ Pendientes: 0

    📈 Winrate: 70.2%
    💰 Ganancia: $487.50
    💸 Pérdida: $245.00
    📊 Resultado Neto: $242.50

    💵 Promedio por operación:
       • Ganancia promedio: $14.77
       • Pérdida promedio: $17.50
       • Profit Factor: 1.99
"""


# =============================================================================
# PASO 4: IDENTIFICAR PROBLEMAS
# =============================================================================

"""
Si el winrate es bajo, ejecuta:

    python analyze_trades.py --indicators

Esto te mostrará:
    - Qué indicadores funcionan mejor
    - Cuál patrón tiene peor WR
    - Si soporte/resistencia no funciona

Ejemplo de output:

    🔹 RSI:
       Trades con RSI: 30 | Winrate: 45.0%  ← MALO, reducir
    
    🔹 Triangle:
       Activos: 10 trades | WR: 85.0%       ← BUENO, usar más
    
    🔹 Reversal Candles:
       Detectados: 25 trades | WR: 55.0%    ← REGULAR

Acciones:
    - RSI bajo WR: Ajusta RSI_OVERSOLD/OVERBOUGHT en main.py
    - Triangle alto WR: Aumenta el weight en score_signal()
"""


# =============================================================================
# PASO 5: ANALIZAR POR PAR
# =============================================================================

"""
Ejecuta:

    python analyze_trades.py --pairs

Verás performance de cada par:

    Par             Total  Ganadas  Perdidas  Winrate  Neto P/L
    ─────────────────────────────────────────────────────────
    EURUSD_otc        12      8        4       66.7%    $75.50
    GBPUSD_otc        15     12        3       80.0%   $145.00
    USDJPY_otc        10      7        3       70.0%    $82.50
    AUDCAD_otc         6      3        3       50.0%    -$20.00

Acciones:
    - GBPUSD funciona bien → considerar aumentar capital
    - AUDCAD tiene 50% WR → deshabilitar o investigar más
    - EURUSD está al mínimo → podría mejorar
"""


# =============================================================================
# PASO 6: REVISAR TRADES ESPECÍFICOS
# =============================================================================

"""
Si quieres auditar un trade específico:

    python analyze_trades.py --trade-id 12345

Verás:
    📌 Trade ID: 12345
       ⏰ Timestamp: 2025-11-24 10:15:30
       📈 Par: EURUSD_otc | TF: M15
       🎯 Decisión: BUY | Score: 5
       🔍 Patrón: Breakout
       💵 Precio: 1.08750 | EMA: 1.08700
       📊 Indicadores:
          • RSI: 65.2
          • EMA_conf: 1
          • TF Signal: 1
          • ATR: 0.00085
          • Triangle: 0 | Reversal: 1
       🎯 Niveles:
          • Near Support: False | Level: 1.08650
          • Near Resistance: True | Level: 1.08850
       📈 HTF Signal: 1
       ✅ Resultado: WIN | P/L: $15.00
       ⏱️ Expiración: 900s
"""


# =============================================================================
# PASO 7: EXPORTAR A EXCEL
# =============================================================================

"""
Para abrir en Excel/Google Sheets:

    python analyze_trades.py --export

Se crea: trades_export_YYYYMMDD.csv

Puedes:
    1. Abrir en Excel
    2. Crear gráficos
    3. Filtrar por par/timeframe
    4. Sortear por RSI/score
    5. Subir a Google Sheets para compartir

Consejos Excel:
    - Filtro automático en headers: Ctrl+Shift+L
    - Crear tabla dinámica de resultados
    - Gráfico de equity curve en profit_loss
    - Heatmap de WR por par/timeframe
"""


# =============================================================================
# PASO 8: MEJORA ITERATIVA
# =============================================================================

"""
Ciclo de mejora:

Día 1:
    1. Bot corre 8 horas
    2. Ejecuta: python analyze_trades.py --all
    3. Identifica problemas
    4. Nota qué cambiar

Día 2:
    1. Ajusta main.py basado en insights
    2. Bot corre de nuevo
    3. Ejecuta análisis nuevamente
    4. Compara resultados

Día 3:
    1. Revisa histórico: python analyze_trades.py --date 20251124
    2. Compara Día 1 vs Día 2 vs Día 3
    3. Acepta cambios que funcionan
    4. Revierte cambios que no ayudan

Ejemplo de cambios:

Si triángulos tienen 85% WR:
    # En main.py, aumentar su peso:
    if row.get('triangle', 0) == 1:
        score += 2  # Cambiar de 1 a 2

Si RSI tiene 40% WR:
    # Reducir confianza en RSI:
    if USE_RSI and not pd.isna(row.get('RSI')):
        # Comentar esta línea:
        # score += 1
        pass

Si EURUSD tiene 45% WR (malo):
    # Deshabilitar par temporalmente:
    PAIRS = [
        'EURUSD_otc',  # ← Comentar esta línea
        'GBPUSD_otc',
        'USDJPY_otc',
        ...
    ]
"""


# =============================================================================
# PASO 9: ANÁLISIS PROFUNDO
# =============================================================================

"""
Script Python personalizado para análisis avanzado:

    from analyze_trades import load_trades
    
    df = load_trades()
    
    # Trades ganadores vs perdedores
    winners = df[df['result'] == 'WIN']
    losers = df[df['result'] == 'LOSS']
    
    print(f"RSI promedio en ganadores: {winners['rsi'].mean():.1f}")
    print(f"RSI promedio en perdedores: {losers['rsi'].mean():.1f}")
    
    # Mejor timeframe
    for tf in ['M5', 'M15', 'M30']:
        tf_df = df[df['timeframe'] == tf]
        wr = len(tf_df[tf_df['result'] == 'WIN']) / len(tf_df) * 100
        print(f"{tf}: {wr:.1f}% WR")
    
    # Mejor hora del día
    df['hour'] = pd.to_datetime(df['timestamp']).dt.hour
    for hour in range(24):
        hour_df = df[df['hour'] == hour]
        if len(hour_df) == 0:
            continue
        wr = len(hour_df[hour_df['result'] == 'WIN']) / len(hour_df) * 100
        print(f"Hora {hour:02d}:00 - {wr:.1f}% ({len(hour_df)} trades)")
"""


# =============================================================================
# PASO 10: AUTOMATIZAR ANÁLISIS DIARIO
# =============================================================================

"""
Crear script batch para automatizar análisis cada día:

Archivo: run_daily_analysis.bat

    @echo off
    cd c:\Users\nico\Downloads\PocketOptions\Bot
    
    echo. 
    echo ========== ANÁLISIS DIARIO ==========
    echo.
    
    python analyze_trades.py --summary
    
    echo.
    echo ========== POR PAR ==========
    echo.
    
    python analyze_trades.py --pairs
    
    echo.
    echo ========== INDICADORES ==========
    echo.
    
    python analyze_trades.py --indicators
    
    echo.
    echo ========== EXPORTAR ==========
    echo.
    
    python analyze_trades.py --export
    
    echo.
    echo Análisis completado. Abre trades_export_*.csv en Excel
    pause

Ejecutar cada mañana:
    cmd /c run_daily_analysis.bat
"""


# =============================================================================
# ARCHIVOS DE REFERENCIA RÁPIDA
# =============================================================================

"""
Documentación incluida:

1. TRADES_QUICK_START.md
   └─ Inicio rápido (5 minutos)

2. TRADES_LOGGING_README.md
   └─ Guía completa (30 minutos)

3. API_REFERENCE.md
   └─ Referencia técnica (para programadores)

4. TRADES_SYSTEM_SUMMARY.md
   └─ Resumen del sistema creado

Para leer cualquiera:
    type TRADES_QUICK_START.md
    type TRADES_LOGGING_README.md
"""


# =============================================================================
# TROUBLESHOOTING COMÚN
# =============================================================================

"""
P: El bot no guarda nada
R: 1. Verifica que main.py ejecutó operaciones
   2. Revisa logs/trades/ existe
   3. Busca errors en main.py

P: Las estadísticas no coinciden
R: 1. Asegúrate de correr en la carpeta correcta
   2. Verifica la fecha en el CSV (trades_YYYYMMDD.csv)
   3. Revisa que no hay trades PENDING cuando calculas WR

P: Necesito datos históricos de otros días
R: Ejecuta: python analyze_trades.py --date 20251122
   (Cambia fecha por la que necesites)

P: Quiero sincronizar con Google Sheets
R: 1. Copia el CSV
   2. Abre Google Sheets
   3. File → Import → Selecciona CSV
   4. ¡Listo!

P: Los gráficos no se ven bien en Excel
R: 1. Selecciona datos
   2. Insert → Chart
   3. Elige tipo de gráfico
   4. Customiza según necesites
"""


# =============================================================================
# PRÓXIMOS PASOS
# =============================================================================

"""
Recomendación de uso:

SEMANA 1:
    □ Ejecutar bot 8 horas/día
    □ Revisar análisis cada 2 horas
    □ Anotar qué patrones funcionan
    □ Documentar bugs encontrados

SEMANA 2:
    □ Analizar datos de la semana 1
    □ Hacer 2-3 mejoras basadas en datos
    □ Bot corre 12 horas/día
    □ Crear reportes diarios

SEMANA 3:
    □ Validar cambios introducidos
    □ Mantener lo que funciona
    □ Revertir lo que no funciona
    □ Ajustar parámetros finos

SEMANA 4:
    □ Análisis profundo del mes
    □ Crear estrategia optimizada
    □ Documentar resultados
    □ Plan para próximo mes
"""


# =============================================================================
# CONTEO DE ARCHIVOS CREADOS
# =============================================================================

"""
✅ Archivos de código creados: 4
    1. trade_logger.py (157 líneas)
    2. analyze_trades.py (347 líneas)  
    3. trades_dashboard.py (196 líneas)
    4. demo_trades.py (134 líneas)

✅ Documentación creada: 5
    1. TRADES_QUICK_START.md
    2. TRADES_LOGGING_README.md
    3. API_REFERENCE.md
    4. TRADES_SYSTEM_SUMMARY.md
    5. TRADES_PRACTICAL_GUIDE.md (este archivo)

✅ Modificaciones a código existente: 1
    1. main.py (integración de logging)

✅ Total de líneas de código: 834
✅ Total de documentación: 2000+ líneas
"""


# =============================================================================
# VALIDACIÓN DEL SISTEMA
# =============================================================================

"""
Para validar que todo funciona:

1. Ejecutar demo trades:
   python demo_trades.py 20

2. Simular resultados:
   python demo_trades.py --results

3. Ver resumen:
   python analyze_trades.py --summary
   ✅ Debe mostrar estadísticas

4. Ver indicadores:
   python analyze_trades.py --indicators
   ✅ Debe mostrar qué funciona

5. Ver por par:
   python analyze_trades.py --pairs
   ✅ Debe mostrar performance

6. Exportar:
   python analyze_trades.py --export
   ✅ Debe crear trades_export_*.csv

Si todo funciona: ¡SISTEMA LISTO! 🎉
"""
