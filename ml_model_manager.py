"""
ML Model Manager with Hot-Reload
Handles model loading, reloading, and auto-training scheduling
"""

import os
import time
import threading
import joblib
import json
from datetime import datetime, timedelta
import subprocess

class MLModelManager:
    def __init__(self, model_path="ml_model.pkl", auto_train_enabled=True, auto_train_interval_hours=24):
        self.model_path = model_path
        self.metadata_path = "ml_model_metadata.json"
        self.model = None
        self.model_lock = threading.Lock()
        self.model_last_modified = 0
        self.ml_active = False
        self.ml_threshold = 0.62
        
        # Auto-training config
        self.auto_train_enabled = auto_train_enabled
        self.auto_train_interval_hours = auto_train_interval_hours
        self.last_training_time = None
        
        # Initial load
        self.load_model()
        
        # Start background threads
        self.start_monitor()
        if self.auto_train_enabled:
            self.start_auto_trainer()
    
    def load_model(self):
        """Load or reload ML model (thread-safe)"""
        try:
            if os.path.exists(self.model_path):
                current_mtime = os.path.getmtime(self.model_path)
                
                if current_mtime != self.model_last_modified:
                    with self.model_lock:
                        new_model = joblib.load(self.model_path)
                        self.model = new_model
                        self.model_last_modified = current_mtime
                        self.ml_active = True
                        
                        # Load metadata if available
                        try:
                            with open(self.metadata_path, 'r') as f:
                                metadata = json.load(f)
                                print(f"🔄 Modelo ML recargado (entrenado: {metadata.get('training_date', 'unknown')})")
                                print(f"   Winrate validación: {metadata.get('validation_winrate', 'N/A')}%")
                        except:
                            print("🔄 Modelo ML recargado")
                        
                        return True
            return False
        except Exception as e:
            print(f"⚠️ Error cargando modelo: {e}")
            self.ml_active = False
            return False
    
    def predict_proba(self, features):
        """Thread-safe prediction"""
        with self.model_lock:
            if self.model is not None:
                return self.model.predict_proba(features)
            else:
                return None
    
    def is_active(self):
        """Check if ML model is active"""
        return self.ml_active
    
    def get_threshold(self):
        """Get ML threshold"""
        return self.ml_threshold
    
    def monitor_thread(self):
        """Background thread to monitor model file changes"""
        print("👁️ Monitor de modelo iniciado")
        while True:
            try:
                self.load_model()
                time.sleep(10)  # Check every 10 seconds
            except Exception as e:
                print(f"⚠️ Error en monitor de modelo: {e}")
                time.sleep(30)
    
    def auto_training_thread(self):
        """Background thread for automatic model retraining"""
        print(f"🤖 Auto-entrenamiento activado (cada {self.auto_train_interval_hours}h)")
        
        while True:
            try:
                current_time = datetime.now()
                
                # Check if it's time to retrain
                if self.last_training_time is None or \
                   (current_time - self.last_training_time).total_seconds() >= self.auto_train_interval_hours * 3600:
                    
                    print(f"\n🔄 Iniciando auto-entrenamiento...")
                    
                    # Run auto_trainer.py usando el mismo Python que está ejecutando este script
                    import sys
                    result = subprocess.run(
                        [sys.executable, "auto_trainer.py"],
                        capture_output=True,
                        text=True
                    )
                    
                    if result.returncode == 0:
                        print("✅ Auto-entrenamiento completado")
                        if result.stdout:
                            print(result.stdout)
                    else:
                        print(f"⚠️ Error en auto-entrenamiento: {result.stderr}")
                    
                    self.last_training_time = current_time
                
                # Sleep for 1 hour before checking again
                time.sleep(3600)
                
            except Exception as e:
                print(f"⚠️ Error en auto-entrenamiento: {e}")
                time.sleep(3600)
    
    def start_monitor(self):
        """Start model file monitor thread"""
        monitor = threading.Thread(target=self.monitor_thread, daemon=True)
        monitor.start()
    
    def start_auto_trainer(self):
        """Start auto-training thread"""
        trainer = threading.Thread(target=self.auto_training_thread, daemon=True)
        trainer.start()


# Global instance
ml_manager = MLModelManager(
    auto_train_enabled=True,
    auto_train_interval_hours=24
)
