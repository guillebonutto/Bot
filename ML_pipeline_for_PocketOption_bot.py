"""
Pipeline ML nivel 2 para tu bot de PocketOption
Archivo: ML_pipeline_for_PocketOption_bot.py

Este archivo contiene:
 - Logger de features: `FeatureLogger` (guarda cada señal/operación en CSV)
 - Entrenador automático: `Trainer` (RandomForest/XGBoost/LightGBM)
 - Predictor/Wrapper: `ModelWrapper` (carga modelo, predice prob de win)
 - Integraci\u00f3n: funciones para usar desde tu bot (`log_signal_for_training`, `should_execute`)

Instrucciones rápidas:
 1) Añadí llamadas a `log_signal_for_training(features)` justo cuando generás una señal (antes de filtrar por riesgo).
 2) Entrená diariamente: `python ML_pipeline_for_PocketOption_bot.py --train` o programalo con cron/task scheduler.
 3) En el runtime del bot llamá `ModelWrapper.predict_proba(features)` para obtener prob de win y filtrar por umbral.

Requisitos Python (pip):
 pip install pandas scikit-learn joblib lightgbm
 (Si querés XGBoost reemplazá lightgbm por xgboost)

Notas:
 - El sistema está pensado como "nivel 2": la IA sugiere probabilidad, el bot decide con un umbral.
 - Guardá los CSVs y modelos en una carpeta `ml_data/` dentro del proyecto.

"""

import os
import json
import time
from datetime import datetime
from typing import Dict, Any
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, roc_auc_score, precision_recall_fscore_support
import joblib

# Intentar importar lightgbm si está disponible
try:
    import lightgbm as lgb
    LIGHTGBM_AVAILABLE = True
except Exception:
    LIGHTGBM_AVAILABLE = False


# ---------------------------
# Rutas y configuraciones
# ---------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ML_DIR = os.path.join(BASE_DIR, "ml_data")
os.makedirs(ML_DIR, exist_ok=True)
FEATURES_CSV = os.path.join(ML_DIR, "features_log.csv")
MODEL_FILE = os.path.join(ML_DIR, "model.pkl")
MODEL_META = os.path.join(ML_DIR, "model_meta.json")

# Hiperparámetros iniciales (podés ajustar)
MODEL_TYPE = "lgb" if LIGHTGBM_AVAILABLE else "rf"  # 'lgb' o 'rf'
RANDOM_STATE = 42
TRAIN_TEST_SPLIT = 0.2
MIN_EXAMPLES_TO_TRAIN = 370  # no entrenar si hay pocos datos
PROB_THRESHOLD = 0.58  # umbral por defecto para ejecutar


# ---------------------------
# Utilities
# ---------------------------

def now_utc_iso():
    return datetime.utcnow().isoformat()


# ---------------------------
# Feature Logger
# ---------------------------
class FeatureLogger:
    """Guarda líneas (features + label) en un CSV. Si label no está presente, guarda label como NaN.
    Espera un dict con keys consistentes que usará el trainer más tarde.
    """
    def __init__(self, csv_path=FEATURES_CSV):
        self.csv_path = csv_path
        self.csv_dir = os.path.dirname(csv_path)
        if self.csv_dir:
            os.makedirs(self.csv_dir, exist_ok=True)

    def append(self, row: Dict[str, Any]):
        df = pd.DataFrame([row])
        # Si archivo no existe, escribir con header
        # Si existe, escribir sin header (append)
        if not os.path.exists(self.csv_path):
            df.to_csv(self.csv_path, index=False)
        else:
            df.to_csv(self.csv_path, mode='a', header=False, index=False)

    def read(self) -> pd.DataFrame:
        if not os.path.exists(self.csv_path):
            return pd.DataFrame()
        
        file_size = os.path.getsize(self.csv_path)
        if file_size == 0:
            return pd.DataFrame()
        
        try:
            df = pd.read_csv(self.csv_path)
            # Si está completamente vacío (solo headers), devolver DataFrame vacío
            if df.empty:
                return pd.DataFrame()
            return df
        except pd.errors.EmptyDataError:
            # Archivo con solo saltos de línea o vacío
            return pd.DataFrame()
        except pd.errors.ParserError:
            # Error de parseo
            return pd.DataFrame()
        except Exception as e:
            print(f"⚠️ Error leyendo {self.csv_path}: {e}")
            return pd.DataFrame()


feature_logger = FeatureLogger()


# ---------------------------
# Model wrapper
# ---------------------------
class ModelWrapper:
    def __init__(self, model_path=MODEL_FILE, meta_path=MODEL_META):
        self.model_path = model_path
        self.meta_path = meta_path
        self.model = None
        self.meta = {}
        self.load()

    def load(self):
        if os.path.exists(self.model_path):
            try:
                self.model = joblib.load(self.model_path)
                if os.path.exists(self.meta_path):
                    with open(self.meta_path, 'r') as f:
                        self.meta = json.load(f)
                print(f"[ML] Modelo cargado: {self.model_path}")
            except Exception as e:
                print(f"[ML] Error cargando modelo: {e}")
                self.model = None
        else:
            print("[ML] No hay modelo entrenado todavía.")

    def save(self):
        if self.model is not None:
            joblib.dump(self.model, self.model_path)
            with open(self.meta_path, 'w') as f:
                json.dump(self.meta, f)
            print(f"[ML] Modelo guardado en {self.model_path}")

    def predict_proba(self, feature_dict: Dict[str, Any]):
        """Devuelve la probabilidad de clase positiva (win)"""
        if self.model is None:
            return None

        X = self._dict_to_dataframe(feature_dict)

        try:
            # LightGBM
            if self.meta.get('model_type') == 'lgb':
                proba = self.model.predict(X)
                return float(proba[0])

            # Scikit-learn (RandomForest, etc)
            elif hasattr(self.model, 'predict_proba'):
                proba = self.model.predict_proba(X)[:, 1]
                return float(proba[0])

            # Fallback
            else:
                pred = self.model.predict(X)
                return float(pred[0])

        except Exception as e:
            print(f"[ML] Error prediciendo: {e}")
            return None

    def _dict_to_dataframe(self, d: Dict[str, Any]):
        # Mantener orden determinista: usar meta['feature_columns'] si existe
        if 'feature_columns' in self.meta:
            cols = self.meta['feature_columns']
        else:
            cols = list(d.keys())
        # llenar NaN para columnas que falten
        row = {c: d.get(c, np.nan) for c in cols}
        return pd.DataFrame([row])


model_wrapper = ModelWrapper()


# ---------------------------
# Trainer
# ---------------------------
class Trainer:
    def __init__(self, csv_path=FEATURES_CSV, model_type=MODEL_TYPE):
        self.csv_path = csv_path
        self.model_type = model_type

    def load_data(self) -> pd.DataFrame:
        # Permitir leer XLSX directamente
        if str(self.csv_path).lower().endswith('.xlsx'):
            try:
                df = pd.read_excel(self.csv_path)
                print(f"[Trainer] XLSX cargado: {self.csv_path} (filas: {len(df)})")
                return df
            except Exception as e:
                print(f"[Trainer] Error leyendo XLSX: {e}")
                return pd.DataFrame()

        # Caso CSV por defecto
        if not os.path.exists(self.csv_path):
            print("[Trainer] No hay archivo de datos")
            return pd.DataFrame()

        df = pd.read_csv(self.csv_path)
        print(f"[Trainer] CSV cargado: {self.csv_path} (filas: {len(df)})")
        return df

    def preprocess(self, df: pd.DataFrame):
        # Expecting a column 'label' con 1=win, 0=loss
        df = df.copy()
        if 'timestamp' in df.columns:
            df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
        # Drop rows without label for training
        df_train = df.dropna(subset=['label'])
        if df_train.empty:
            return None, None

        # Simple preprocessing: numeric columns only
        X = df_train.drop(columns=['label', 'timestamp', 'pair', 'decision'], errors='ignore')
        # Convert booleans to ints
        for c in X.select_dtypes(include=['bool']).columns:
            X[c] = X[c].astype(int)
        # Fill NaN
        X = X.ffill().fillna(0)
        y = df_train['label'].astype(int)
        return X, y

    def train(self):
        df = self.load_data()
        if df.empty:
            print('[Trainer] Sin datos para entrenar')
            return False

        X, y = self.preprocess(df)
        if X is None or len(X) < MIN_EXAMPLES_TO_TRAIN:
            print(f"[Trainer] No hay suficientes ejemplos etiquetados ({0 if X is None else len(X)})")
            return False

        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=TRAIN_TEST_SPLIT, random_state=RANDOM_STATE
        )

        # Entrenar modelo
        if self.model_type == 'lgb' and LIGHTGBM_AVAILABLE:
            train_data = lgb.Dataset(X_train, label=y_train)
            params = {
                'objective': 'binary',
                'metric': 'auc',
                'verbosity': -1,
                'num_leaves': 31,
                'learning_rate': 0.05,
                'feature_fraction': 0.9
            }
            model = lgb.train(params, train_data, num_boost_round=200)

            # CAMBIO CRÍTICO: Convertir probabilidades a clases binarias
            y_proba = model.predict(X_test)
            y_pred = (y_proba >= 0.5).astype(int)  # Umbral 0.5

        else:
            model = RandomForestClassifier(
                n_estimators=200,
                max_depth=10,
                random_state=RANDOM_STATE,
                n_jobs=-1
            )
            model.fit(X_train, y_train)

            # RandomForest ya devuelve clases binarias
            y_pred = model.predict(X_test)
            y_proba = model.predict_proba(X_test)[:, 1]

        # Evaluar
        acc = accuracy_score(y_test, y_pred)

        try:
            auc = roc_auc_score(y_test, y_proba)
        except Exception as e:
            print(f"[Trainer] Warning calculando AUC: {e}")
            auc = float('nan')

        precision, recall, f1, _ = precision_recall_fscore_support(
            y_test, y_pred, average='binary', zero_division=0
        )

        print(f"\n{'=' * 50}")
        print(f"[Trainer] MÉTRICAS DEL MODELO")
        print(f"{'=' * 50}")
        print(f"  Accuracy:  {acc:.4f}")
        print(f"  AUC:       {auc:.4f}")
        print(f"  Precision: {precision:.4f}")
        print(f"  Recall:    {recall:.4f}")
        print(f"  F1-Score:  {f1:.4f}")
        print(f"{'=' * 50}\n")

        # Guardar modelo y meta
        meta = {
            'model_type': self.model_type,
            'feature_columns': list(X.columns),
            'trained_at': now_utc_iso(),
            'metrics': {
                'acc': float(acc),
                'auc': float(auc) if not np.isnan(auc) else None,
                'precision': float(precision),
                'recall': float(recall),
                'f1': float(f1)
            },
            'train_size': len(X_train),
            'test_size': len(X_test)
        }

        # Guardar modelo
        if self.model_type == 'lgb' and LIGHTGBM_AVAILABLE:
            model.save_model(MODEL_FILE)
        else:
            joblib.dump(model, MODEL_FILE)

        # Guardar metadata
        with open(MODEL_META, 'w') as f:
            json.dump(meta, f, indent=2)

        print(f'[Trainer] ✅ Modelo guardado en: {MODEL_FILE}')
        print(f'[Trainer] ✅ Metadata guardada en: {MODEL_META}\n')

        return True


# ---------------------------
# Funciones de integraci\u00f3n
# ---------------------------

def log_signal_for_training(signal_info: Dict[str, Any], label: int = None):
    """Llamar desde tu bot cuando detectás una señal.
    signal_info: dict con features. Debe incluir al menos: timestamp, pair, decision (BUY/SELL), price
    label: opcional, 1=win, 0=loss (podés setearlo más tarde cuando verifiques resultado)
    """
    row = signal_info.copy()
    row['timestamp'] = row.get('timestamp', now_utc_iso())
    row['label'] = label if label is not None else np.nan
    feature_logger.append(row)


def label_last_trade(trade_timestamp: str, result_win: bool):
    """Si querés etiquetar automáticamente una operación anterior una vez que su resultado esté disponible.
    trade_timestamp debe existir en el CSV en columna 'timestamp' exactamente (o buscá por proximidad).
    """
    df = feature_logger.read()
    if df.empty:
        print('[ML] No hay registro')
        return False
    # buscar por timestamp exacto
    mask = df['timestamp'] == trade_timestamp
    if mask.sum() == 0:
        # fallback: buscar la fila más cercana en tiempo
        df['ts'] = pd.to_datetime(df['timestamp'], errors='coerce')
        t = pd.to_datetime(trade_timestamp, errors='coerce')
        df['delta'] = (df['ts'] - t).abs()
        idx = df['delta'].idxmin()
        df.at[idx, 'label'] = int(result_win)
    else:
        df.loc[mask, 'label'] = int(result_win)

    df = df.drop(columns=['ts', 'delta'], errors='ignore')
    df.to_csv(FEATURES_CSV, index=False)
    print('[ML] Etiqueta actualizada')
    return True


def should_execute(feature_dict: Dict[str, Any], threshold: float = PROB_THRESHOLD) -> (bool, float):
    """Llamar desde el runtime justo antes de operar.
    Devuelve (boolean, prob) -> si model absent devuelve (True, None) para no bloquear (o podes cambiarlo a False).
    """
    prob = model_wrapper.predict_proba(feature_dict)
    if prob is None:
        # no hay modelo: permitir por defecto (o cambiar comportamiento)
        return True, None
    return (prob >= threshold), prob


# ---------------------------
# CLI simple para entrenar / inspeccionar
# ---------------------------
if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--train', action='store_true', help='Entrenar modelo con los datos actuales')
    parser.add_argument('--show', action='store_true', help='Mostrar primeras filas del CSV')
    args = parser.parse_args()

    if args.show:
        df = feature_logger.read()
        if df.empty:
            print('Sin datos guardados aún')
        else:
            print(df.head(50).to_string(index=False))

    if args.train:
        trainer = Trainer()
        ok = trainer.train()
        if ok:
            # recargar el modelo en memoria
            model_wrapper.load()

