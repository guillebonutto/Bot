"""
ml_trades_integration.py
=======================
Vinculación entre el sistema de IA (ML_pipeline_for_PocketOption_bot.py)
y el sistema de logging de trades (trade_logger.py).

Propósito:
  1. Cada operación registrada en trade_logger.py se sincroniza con ML_pipeline
  2. El modelo IA mejora con datos reales de trades ejecutados
  3. Se crea retroalimentación: IA predice → Trade resultado → IA aprende

Uso:
  from ml_trades_integration import sync_trades_to_ml, predict_trade_success
"""

import os
import pandas as pd
import numpy as np
from datetime import datetime, timezone
from typing import Dict, Any, Tuple

# Importar módulos propios
from trade_logger import trade_logger
from ML_pipeline_for_PocketOption_bot import (
    feature_logger,
    model_wrapper,
    Trainer,
    should_execute,
    FEATURES_CSV,
    MODEL_FILE
)


class MLTradesIntegration:
    """Vincula trades ejecutados con el modelo de IA para mejora continua."""
    
    def __init__(self):
        self.trade_logger_path = None
        self.ml_features_path = FEATURES_CSV
    
    def get_todays_trade_file(self):
        """Obtener path del CSV de trades de hoy."""
        date_str = datetime.now(timezone.utc).strftime("%Y%m%d")
        trades_path = os.path.join("logs", "trades", f"trades_{date_str}.csv")
        return trades_path
    
    def load_trades_csv(self, csv_path=None):
        """Cargar trades del archivo CSV."""
        if csv_path is None:
            csv_path = self.get_todays_trade_file()
        
        if not os.path.exists(csv_path):
            print(f"⚠️ No se encontró: {csv_path}")
            return pd.DataFrame()
        
        try:
            df = pd.read_csv(csv_path)
            # Filtrar filas vacías (que solo tengan NaN)
            df = df.dropna(how='all')
            if df.empty:
                print(f"ℹ️ CSV vacío: {csv_path}")
            return df
        except pd.errors.EmptyDataError:
            print(f"ℹ️ CSV vacío (sin datos): {csv_path}")
            return pd.DataFrame()
        except Exception as e:
            print(f"❌ Error leyendo {csv_path}: {e}")
            return pd.DataFrame()
    
    def trade_to_ml_features(self, trade_row: pd.Series) -> Dict[str, Any]:
        """
        Convertir un row del trade_logger a features para el ML.
        
        Mapeo de columnas:
        trade_logger.py → ML_pipeline features
        """
        features = {
            # Identificadores
            'timestamp': str(trade_row.get('timestamp', '')),
            'trade_id': str(trade_row.get('trade_id', '')),
            'pair': str(trade_row.get('pair', '')),
            'timeframe': str(trade_row.get('timeframe', '')),
            'decision': str(trade_row.get('decision', '')).upper(),
            
            # Indicadores técnicos (normalizados)
            'rsi': float(trade_row.get('rsi', np.nan)) if pd.notna(trade_row.get('rsi')) else np.nan,
            'ema_conf': int(trade_row.get('ema_conf', 0)),
            'tf_signal': int(trade_row.get('tf_signal', 0)),
            'atr': float(trade_row.get('atr', np.nan)) if pd.notna(trade_row.get('atr')) else np.nan,
            'price': float(trade_row.get('price', np.nan)) if pd.notna(trade_row.get('price')) else np.nan,
            'ema': float(trade_row.get('ema', np.nan)) if pd.notna(trade_row.get('ema')) else np.nan,
            
            # Patrones
            'triangle_active': int(trade_row.get('triangle_active', 0)),
            'reversal_candle': int(trade_row.get('reversal_candle', 0)),
            'near_support': int(trade_row.get('near_support', False)),
            'near_resistance': int(trade_row.get('near_resistance', False)),
            'htf_signal': int(trade_row.get('htf_signal', 0)),
            
            # Score y metadata
            'signal_score': int(trade_row.get('signal_score', 0)),
            'expiry_time': int(trade_row.get('expiry_time', 0)) if pd.notna(trade_row.get('expiry_time')) else 0,
            
            # Resultado (para entrenar)
            'label': 1 if str(trade_row.get('result', '')).upper() == 'WIN' else (
                0 if str(trade_row.get('result', '')).upper() == 'LOSS' else np.nan
            )
        }
        
        return features
    
    def sync_trades_to_ml(self, trades_csv_path=None, auto_train=False):
        """
        Sincronizar trades ejecutados con el archivo de features ML.
        
        Args:
            trades_csv_path: path al CSV de trades. Si None, usa el de hoy
            auto_train: si True, entrena el modelo después de sincronizar
        
        Returns:
            int: número de trades sincronizados
        """
        try:
            trades_df = self.load_trades_csv(trades_csv_path)
        except Exception as e:
            print(f"❌ Error cargando trades: {e}")
            return 0
        
        if trades_df.empty:
            print("ℹ️ Sin trades para sincronizar")
            return 0
        
        synced_count = 0
        
        # Filtrar solo trades completados
        trades_df = trades_df[trades_df['result'].isin(['WIN', 'LOSS'])]
        
        if trades_df.empty:
            print("ℹ️ Sin trades completados (PENDING o sin resultado)")
            return 0
        
        for idx, trade_row in trades_df.iterrows():
            try:
                # Convertir trade a features ML
                features = self.trade_to_ml_features(trade_row)
                
                # Guardar en feature_logger (append es seguro incluso si el archivo está vacío)
                feature_logger.append(features)
                synced_count += 1
            except Exception as e:
                print(f"⚠️ Error sincronizando trade {trade_row.get('trade_id', 'unknown')}: {e}")
                continue
        
        if synced_count > 0:
            print(f"✅ Sincronizados {synced_count} trades con ML")
        else:
            print("ℹ️ No hay trades nuevos para sincronizar")
        
        if auto_train and synced_count > 0:
            try:
                print("\n🤖 Entrenando modelo ML...")
                trainer = Trainer()
                trainer.train()
                # Recargar modelo
                model_wrapper.load()
                print("✅ Modelo entrenado exitosamente")
            except Exception as e:
                print(f"⚠️ Error entrenando modelo: {e}")
        
        return synced_count
    
    def predict_trade_success(self, trade_features: Dict[str, Any]) -> Tuple[bool, float]:
        """
        Predecir probabilidad de éxito de un trade ANTES de ejecutarlo.
        
        Args:
            trade_features: dict con indicadores del trade
        
        Returns:
            (should_execute, probability)
        """
        should_trade, prob = should_execute(trade_features)
        return should_trade, prob
    
    def get_trade_performance_vs_ml(self, date_str=None):
        """
        Analizar correlación entre predicciones ML y resultados reales.
        
        Returns:
            dict con estadísticas de acuracidad
        """
        if date_str:
            trades_path = os.path.join("logs", "trades", f"trades_{date_str}.csv")
        else:
            trades_path = self.get_todays_trade_file()
        
        trades_df = self.load_trades_csv(trades_path)
        
        if trades_df.empty:
            return None
        
        # Filtrar trades completados
        completed = trades_df[trades_df['result'].isin(['WIN', 'LOSS'])]
        
        if completed.empty:
            return None
        
        stats = {
            'total_trades': len(completed),
            'wins': len(completed[completed['result'] == 'WIN']),
            'losses': len(completed[completed['result'] == 'LOSS']),
            'winrate': len(completed[completed['result'] == 'WIN']) / len(completed) * 100
        }
        
        return stats
    
    def export_ml_training_data(self, output_file="ml_training_data.csv"):
        """Exportar datos de trades como dataset para ML."""
        trades_df = self.load_trades_csv()
        
        if trades_df.empty:
            print("Sin datos para exportar")
            return
        
        # Convertir todas las filas
        ml_rows = []
        for idx, trade in trades_df.iterrows():
            features = self.trade_to_ml_features(trade)
            ml_rows.append(features)
        
        # Crear DataFrame y guardar
        ml_df = pd.DataFrame(ml_rows)
        ml_df.to_csv(output_file, index=False)
        print(f"✅ Datos exportados a: {output_file}")
        print(f"   Total filas: {len(ml_df)}")
        print(f"   Filas con etiqueta: {ml_df['label'].notna().sum()}")


# Instancia global
ml_trades = MLTradesIntegration()


# Funciones de conveniencia
def sync_trades_now(auto_train=False):
    """Sincronizar trades actuales con ML."""
    return ml_trades.sync_trades_to_ml(auto_train=auto_train)


def predict_success(features: Dict[str, Any]) -> Tuple[bool, float]:
    """Predecir éxito de un trade."""
    return ml_trades.predict_trade_success(features)


def get_ml_performance():
    """Obtener performance del modelo vs resultados reales."""
    return ml_trades.get_trade_performance_vs_ml()


def export_training_data(output="ml_training_data.csv"):
    """Exportar datos para entrenar externamente."""
    ml_trades.export_ml_training_data(output)


# ============================================================================
# CLI para uso directo
# ============================================================================

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Vincular trades con ML')
    parser.add_argument('--sync', action='store_true', help='Sincronizar trades con ML')
    parser.add_argument('--sync-train', action='store_true', help='Sincronizar y entrenar')
    parser.add_argument('--export', action='store_true', help='Exportar datos ML')
    parser.add_argument('--stats', action='store_true', help='Ver estadísticas')
    parser.add_argument('--date', type=str, default=None, help='Fecha específica (YYYYMMDD)')
    
    args = parser.parse_args()
    
    if args.sync:
        sync_trades_now(auto_train=False)
    
    if args.sync_train:
        sync_trades_now(auto_train=True)
    
    if args.export:
        export_training_data()
    
    if args.stats:
        stats = get_ml_performance()
        if stats:
            print("\n📊 ESTADÍSTICAS ML vs TRADES")
            print("=" * 50)
            for key, value in stats.items():
                print(f"{key}: {value}")
        else:
            print("Sin datos")
