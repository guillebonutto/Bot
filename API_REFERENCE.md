"""
API REFERENCE - Trade Logger System
===================================
Referencia completa de clases y métodos disponibles.
"""

# ============================================================================
# CLASE: TradeLogger (trade_logger.py)
# ============================================================================

class TradeLogger:
    """
    Logger profesional para guardar trades en CSV.
    
    Uso:
        from trade_logger import trade_logger
        trade_logger.log_trade({...})
    """
    
    def __init__(self, logs_dir="logs/trades", filename_pattern="trades_{date}.csv"):
        """
        Inicializar logger.
        
        Args:
            logs_dir (str): Directorio donde guardar CSV
            filename_pattern (str): Patrón de nombre de archivo
        
        Ejemplo:
            logger = TradeLogger()
            logger = TradeLogger(logs_dir="mi_carpeta")
        """
        pass
    
    def log_trade(self, trade_data):
        """
        Registrar un trade ANTES de que expire.
        
        Args:
            trade_data (dict): Diccionario con datos del trade
        
        Campos disponibles:
            - timestamp: datetime (requerido)
            - trade_id: str (requerido)
            - pair: str (requerido)
            - timeframe: str (M5, M15, M30)
            - decision: str (BUY o SELL)
            - signal_score: int (0-7)
            - pattern_detected: str (Breakout, etc)
            - price: float
            - ema: float
            - rsi: float
            - ema_conf: int (-1, 0, 1)
            - tf_signal: int (-1, 0, 1)
            - atr: float
            - triangle_active: int (0 o 1)
            - reversal_candle: int (0 o 1)
            - near_support: bool
            - near_resistance: bool
            - support_level: float
            - resistance_level: float
            - htf_signal: int (-1, 0, 1)
            - result: str ('PENDING', 'WIN', 'LOSS')
            - profit_loss: float (USD)
            - expiry_time: int (segundos)
            - notes: str (campo libre)
        
        Returns:
            bool: True si se guardó correctamente
        
        Ejemplo:
            success = trade_logger.log_trade({
                'timestamp': datetime.utcnow(),
                'trade_id': '12345',
                'pair': 'EURUSD_otc',
                'decision': 'BUY',
                'signal_score': 5,
                'result': 'PENDING'
            })
        """
        pass
    
    def update_trade_result(self, trade_id, result, profit_loss=None, notes=None):
        """
        Actualizar resultado de un trade después de expirar.
        
        Args:
            trade_id (str): ID del trade a actualizar
            result (str): 'WIN' o 'LOSS'
            profit_loss (float, optional): Ganancia/pérdida en USD
            notes (str, optional): Notas adicionales
        
        Returns:
            bool: True si se actualizó correctamente
        
        Ejemplo:
            trade_logger.update_trade_result(
                trade_id='12345',
                result='WIN',
                profit_loss=12.50
            )
        """
        pass
    
    def get_todays_trades(self):
        """
        Obtener todos los trades de hoy.
        
        Returns:
            pd.DataFrame: DataFrame con los trades
        
        Ejemplo:
            df = trade_logger.get_todays_trades()
            print(f"Total trades: {len(df)}")
        """
        pass
    
    def get_stats(self):
        """
        Calcular estadísticas del día actual.
        
        Returns:
            dict: Diccionario con estadísticas
                - total: int (número de operaciones)
                - wins: int (operaciones ganadoras)
                - losses: int (operaciones perdidas)
                - pending: int (operaciones pendientes)
                - winrate: float (porcentaje, 0-100)
                - total_profit: float (ganancia neta)
        
        Ejemplo:
            stats = trade_logger.get_stats()
            print(f"Winrate: {stats['winrate']:.1f}%")
            print(f"Ganancias: ${stats['total_profit']:.2f}")
        """
        pass


# ============================================================================
# FUNCIÓN: analyze_trades.py
# ============================================================================

def load_trades(date=None):
    """
    Cargar trades de un CSV específico.
    
    Args:
        date (str, optional): Fecha en formato YYYYMMDD. Si None usa hoy.
    
    Returns:
        pd.DataFrame: DataFrame con los trades
    
    Ejemplo:
        df = load_trades()  # Hoy
        df = load_trades('20251124')  # Fecha específica
    """
    pass


def print_summary_stats(df):
    """
    Mostrar estadísticas resumidas en pantalla.
    
    Args:
        df (pd.DataFrame): DataFrame con trades
    
    Ejemplo:
        print_summary_stats(df)
    """
    pass


def print_pair_stats(df):
    """
    Mostrar estadísticas desglosadas por par.
    
    Args:
        df (pd.DataFrame): DataFrame con trades
    
    Ejemplo:
        print_pair_stats(df)
    """
    pass


def print_indicator_analysis(df):
    """
    Analizar qué indicadores funcionan mejor.
    
    Args:
        df (pd.DataFrame): DataFrame con trades
    
    Muestra:
        - Winrate por indicador
        - Efectividad de cada patrón
        - Niveles de soporte/resistencia
    
    Ejemplo:
        print_indicator_analysis(df)
    """
    pass


def export_excel(df, output_file=None):
    """
    Exportar trades a archivo CSV compatible con Excel.
    
    Args:
        df (pd.DataFrame): DataFrame con trades
        output_file (str, optional): Nombre del archivo. 
                                    Si None, auto genera.
    
    Ejemplo:
        export_excel(df)
        export_excel(df, 'mi_reporte.csv')
    """
    pass


# ============================================================================
# COMANDO: LÍNEA DE COMANDOS analyze_trades.py
# ============================================================================

"""
python analyze_trades.py [opciones]

Opciones:
    --date YYYYMMDD          Especificar fecha (por defecto: hoy)
    --trade-id ID            Ver detalles de un trade específico
    --summary                Mostrar resumen (opción por defecto)
    --pairs                  Estadísticas desglosadas por par
    --indicators             Análisis de indicadores
    --export                 Exportar a CSV/Excel
    --all                    Mostrar todo

Ejemplos:
    python analyze_trades.py
    python analyze_trades.py --date 20251122
    python analyze_trades.py --indicators
    python analyze_trades.py --export
    python analyze_trades.py --all
"""


# ============================================================================
# COMANDO: LÍNEA DE COMANDOS trades_dashboard.py
# ============================================================================

class TradesDashboard:
    """
    Dashboard en tiempo real para monitorear trades.
    
    Uso:
        python trades_dashboard.py
        python trades_dashboard.py --interval 10
    """
    
    def __init__(self, update_interval=5):
        """
        Inicializar dashboard.
        
        Args:
            update_interval (int): Segundos entre actualizaciones
        """
        pass
    
    def run(self):
        """
        Ejecutar dashboard con actualizaciones periódicas.
        Presiona Ctrl+C para salir.
        
        Ejemplo:
            dashboard = TradesDashboard(update_interval=5)
            dashboard.run()
        """
        pass


# ============================================================================
# COMANDO: LÍNEA DE COMANDOS demo_trades.py
# ============================================================================

"""
python demo_trades.py [opciones]

Opciones:
    [N]          Crear N trades de demostración
    --results    Simular resultados para trades existentes

Ejemplos:
    python demo_trades.py 20       # Crear 20 trades demo
    python demo_trades.py --results # Simular resultados
"""


# ============================================================================
# USO INTEGRADO EN main.py
# ============================================================================

"""
El logging está integrado automáticamente en main.py.

Flujo:
    1. ANTES de operar: trade_logger.log_trade({...})
       └─ Se guarda con result='PENDING'
    
    2. Esperar expiración
    
    3. DESPUÉS de expiración: trade_logger.update_trade_result(
                                trade_id, result, profit_loss)
       └─ Se actualiza con WIN/LOSS y P/L

Ejemplo de cómo se usa en main.py:

    # ANTES de operar
    trade_logger.log_trade({
        'timestamp': datetime.utcnow(),
        'trade_id': trade_id,
        'pair': sig['pair'],
        'timeframe': sig['tf'],
        'decision': sig['signal'],
        'signal_score': sig.get('score', 0),
        'pattern_detected': sig.get('pattern', 'Indicadores'),
        'price': sig.get('price', 0),
        'ema': sig.get('ema', 0),
        'rsi': indicators.get('RSI'),
        # ... más campos
        'result': 'PENDING',
    })

    # Esperar resultado
    await asyncio.sleep(sig['duration'] + 10)

    # DESPUÉS, actualizar resultado
    trade_logger.update_trade_result(
        trade_id=trade_id,
        result='WIN' if win else 'LOSS',
        profit_loss=profit if win else None
    )
"""


# ============================================================================
# ESTRUCTURA DEL CSV (Columnas)
# ============================================================================

"""
timestamp            Datetime - YYYY-MM-DD HH:MM:SS UTC
trade_id             String - ID único del trade
pair                 String - EURUSD_otc, GBPUSD_otc, etc
timeframe            String - M5, M15, M30
decision             String - BUY o SELL
signal_score         Integer - 0 a 7
pattern_detected     String - Nombre del patrón o indicadores
price                Float - Precio de entrada (5 decimales)
ema                  Float - Valor de EMA
rsi                  Float - Índice de Fuerza Relativa (0-100)
ema_conf             Integer - -1 (SELL), 0 (NEUTRAL), 1 (BUY)
tf_signal            Integer - -1 (SELL), 0 (NEUTRAL), 1 (BUY)
atr                  Float - Average True Range
triangle_active      Integer - 0 o 1
reversal_candle      Integer - 0 o 1
near_support         Boolean - True o False
near_resistance      Boolean - True o False
support_level        Float - Nivel de soporte
resistance_level     Float - Nivel de resistencia
htf_signal           Integer - -1 (SELL), 0 (NEUTRAL), 1 (BUY)
result               String - WIN, LOSS, o PENDING
profit_loss          Float - Ganancia/pérdida en USD
expiry_time          Integer - Duración en segundos
notes                String - Campo libre
"""


# ============================================================================
# EJEMPLOS PRÁCTICOS
# ============================================================================

"""
EJEMPLO 1: Registrar y actualizar un trade

    from trade_logger import trade_logger
    from datetime import datetime
    
    # Registrar ANTES de operar
    trade_logger.log_trade({
        'timestamp': datetime.utcnow(),
        'trade_id': '123456',
        'pair': 'EURUSD_otc',
        'timeframe': 'M15',
        'decision': 'BUY',
        'signal_score': 5,
        'pattern_detected': 'Breakout',
        'price': 1.08750,
        'ema': 1.08700,
        'rsi': 65.2,
        'ema_conf': 1,
        'tf_signal': 1,
        'atr': 0.00085,
        'triangle_active': 0,
        'reversal_candle': 1,
        'near_support': False,
        'near_resistance': True,
        'support_level': 1.08650,
        'resistance_level': 1.08850,
        'htf_signal': 1,
        'result': 'PENDING',
        'expiry_time': 900,
    })
    
    # Esperar a que expire la operación...
    
    # Actualizar resultado
    trade_logger.update_trade_result(
        trade_id='123456',
        result='WIN',
        profit_loss=15.50
    )


EJEMPLO 2: Analizar trades del día

    from analyze_trades import load_trades, print_summary_stats
    
    df = load_trades()  # Cargar trades de hoy
    
    print_summary_stats(df)  # Ver resumen
    
    # Exportar a Excel
    df.to_csv('reporte.csv', index=False)


EJEMPLO 3: Encontrar mejor patrón

    df = load_trades()
    
    # Filtrar solo trades completados
    completed = df[df['result'].isin(['WIN', 'LOSS'])]
    
    # Agrupar por patrón
    for pattern in completed['pattern_detected'].unique():
        pattern_df = completed[completed['pattern_detected'] == pattern]
        wins = len(pattern_df[pattern_df['result'] == 'WIN'])
        total = len(pattern_df)
        wr = wins / total * 100 if total > 0 else 0
        print(f"{pattern}: {wr:.1f}% ({wins}W/{total})")


EJEMPLO 4: Monitoreo en tiempo real

    while True:
        df = load_trades()
        
        # Calcular stats
        completed = df[df['result'].isin(['WIN', 'LOSS'])]
        wins = len(completed[completed['result'] == 'WIN'])
        losses = len(completed[completed['result'] == 'LOSS'])
        wr = wins / (wins+losses) * 100 if (wins+losses) > 0 else 0
        
        print(f"Winrate: {wr:.1f}% ({wins}W-{losses}L)")
        
        time.sleep(5)  # Actualizar cada 5 segundos
"""


# ============================================================================
# TIPS Y TRUCOS
# ============================================================================

"""
TIP 1: Filtrar por par en pandas
    df_eur = df[df['pair'] == 'EURUSD_otc']
    df_eur_wins = df_eur[df_eur['result'] == 'WIN']

TIP 2: Calcular estadísticas personalizadas
    total = len(df)
    winrate = len(df[df['result'] == 'WIN']) / total * 100
    avg_win = df[df['result'] == 'WIN']['profit_loss'].mean()
    avg_loss = abs(df[df['result'] == 'LOSS']['profit_loss'].mean())

TIP 3: Gráfico de equity curve
    df['profit_loss'].fillna(0).cumsum().plot()

TIP 4: Abrir en Google Sheets
    Sube el CSV a Google Drive
    Abre con Google Sheets
    Los cambios se sincronizan automáticamente

TIP 5: Crear alerta si WR baja
    if df['result'].value_counts().get('WIN', 0) / len(df) < 0.50:
        print("ALERTA: Winrate < 50%")
        tg_send("⚠️ Winrate crítico")
"""
