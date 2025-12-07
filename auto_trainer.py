#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Auto-Trainer with Validation
Automatically retrains ML model and updates only if it improves on validation set.
"""

import pandas as pd
import numpy as np
import glob
import os
import joblib
import json
from datetime import datetime
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report

# Configuration
MIN_TRADES_FOR_TRAINING = 300  # Lowered from 500 for initial testing
VALIDATION_SPLIT = 0.2
MODEL_PATH = "ml_model.pkl"
MODEL_METADATA_PATH = "ml_model_metadata.json"
TRAINING_HISTORY_PATH = "logs/training_history.csv"
BACKUP_MODELS_TO_KEEP = 3

class AutoTrainer:
    def __init__(self):
        self.current_model = None
        self.current_metadata = None
        self.load_current_model()
        
    def load_current_model(self):
        """Load the current production model"""
        try:
            self.current_model = joblib.load(MODEL_PATH)
            with open(MODEL_METADATA_PATH, 'r') as f:
                self.current_metadata = json.load(f)
            print(f"[OK] Loaded current model (trained: {self.current_metadata.get('training_date', 'unknown')})")
        except FileNotFoundError:
            print("[INFO] No current model found. Will create first model.")
            self.current_model = None
            self.current_metadata = None
    
    def load_recent_trades(self, n=1000):
        """Load the most recent N trades from logs"""
        print(f"\n[INFO] Loading last {n} trades...")
        
        all_files = glob.glob("logs/trades/trades_*.csv")
        if not all_files:
            print("[ERROR] No trade logs found")
            return None
        
        # Load all trades
        dfs = []
        for file in sorted(all_files, reverse=True):  # Most recent first
            try:
                df = pd.read_csv(file)
                dfs.append(df)
            except Exception as e:
                print(f"[WARN] Error reading {file}: {e}")
        
        if not dfs:
            return None
            
        dfs = [d for d in dfs if not d.empty and not d.isna().all().all()]
        if not dfs:
            return None

        all_trades = pd.concat(dfs, ignore_index=True)
        
        # Filter only completed trades (not PENDING)
        all_trades = all_trades[all_trades['result'].isin(['WIN', 'LOSS'])]
        
        # Sort by timestamp and take last N
        all_trades['timestamp'] = pd.to_datetime(all_trades['timestamp'])
        all_trades = all_trades.sort_values('timestamp', ascending=False).head(n)
        
        print(f"[OK] Loaded {len(all_trades)} completed trades")
        return all_trades
    
    def prepare_features(self, df):
        """Prepare features for training"""
        # Extract features (same as train_ml_model.py)
        features = []
        labels = []
        
        for _, row in df.iterrows():
            try:
                # Features: price, duration_minutes, pair_idx, ema8, ema21, ema55, hour_normalized
                pair_idx = 0  # Default if pair not in list
                
                # Try to extract pair index (you may need to adjust this based on your data)
                if 'pair' in row:
                    pair_name = str(row['pair'])
                    # Simple hash-based index
                    pair_idx = hash(pair_name) % 100
                
                duration_minutes = row.get('expiry_time', 300) / 60  # Convert to minutes
                
                # Extract hour from timestamp (0-23 normalized to 0-1)
                hour_normalized = 0.5  # Default middle of day
                if 'timestamp' in row:
                    try:
                        ts = pd.to_datetime(row['timestamp'])
                        hour_normalized = ts.hour / 24
                    except:
                        pass
                
                feature_row = [
                    row.get('price', 0),
                    duration_minutes,
                    pair_idx,
                    row.get('ema', 0),  # ema8
                    row.get('ema', 0),  # ema21 (if not available, use same as ema8)
                    row.get('ema', 0),  # ema55
                    hour_normalized,  # 7th feature: hour of day
                ]
                
                label = 1 if row['result'] == 'WIN' else 0
                
                features.append(feature_row)
                labels.append(label)
            except Exception as e:
                continue
        
        return np.array(features), np.array(labels)
    
    def train_new_model(self, X_train, y_train):
        """Train a new Random Forest model"""
        print("\n[INFO] Training new model...")
        
        model = RandomForestClassifier(
            n_estimators=100,
            max_depth=10,
            min_samples_split=10,
            min_samples_leaf=5,
            random_state=42,
            n_jobs=-1
        )
        
        model.fit(X_train, y_train)
        print("[OK] Model trained")
        return model
    
    def evaluate_model(self, model, X_val, y_val):
        """Evaluate model on validation set"""
        y_pred = model.predict(X_val)
        accuracy = accuracy_score(y_val, y_pred)
        
        # Calculate winrate (percentage of correct predictions)
        winrate = accuracy * 100
        
        return winrate, y_pred
    
    def backup_current_model(self):
        """Create backup of current model before updating"""
        if not os.path.exists(MODEL_PATH):
            return
        
        # Rotate backups
        for i in range(BACKUP_MODELS_TO_KEEP - 1, 0, -1):
            old_backup = f"ml_model_backup_{i}.pkl"
            new_backup = f"ml_model_backup_{i+1}.pkl"
            if os.path.exists(old_backup):
                if os.path.exists(new_backup):
                    os.remove(new_backup)
                os.rename(old_backup, new_backup)
        
        # Create new backup
        import shutil
        shutil.copy2(MODEL_PATH, "ml_model_backup_1.pkl")
        print("[INFO] Created model backup")
    
    def save_model(self, model, metadata):
        """Save model and metadata"""
        self.backup_current_model()
        
        joblib.dump(model, MODEL_PATH)
        with open(MODEL_METADATA_PATH, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        print(f"[OK] Model saved to {MODEL_PATH}")
    
    def log_training_attempt(self, trades_used, current_wr, new_wr, updated, reason):
        """Log training attempt to history"""
        os.makedirs("logs", exist_ok=True)
        
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'trades_used': trades_used,
            'current_model_wr': current_wr,
            'new_model_wr': new_wr,
            'updated': updated,
            'reason': reason
        }
        
        # Append to CSV
        df = pd.DataFrame([log_entry])
        if os.path.exists(TRAINING_HISTORY_PATH):
            df.to_csv(TRAINING_HISTORY_PATH, mode='a', header=False, index=False)
        else:
            df.to_csv(TRAINING_HISTORY_PATH, index=False)
    
    def run(self):
        """Main auto-training workflow"""
        print("="*60)
        print(" AUTO-TRAINER STARTED")
        print("="*60)
        
        # 1. Load recent trades
        trades_df = self.load_recent_trades(n=1000)
        
        if trades_df is None or len(trades_df) < MIN_TRADES_FOR_TRAINING:
            reason = f"Not enough trades ({len(trades_df) if trades_df is not None else 0} < {MIN_TRADES_FOR_TRAINING})"
            print(f"[SKIP] {reason}")
            self.log_training_attempt(
                len(trades_df) if trades_df is not None else 0,
                0, 0, False, reason
            )
            return
        
        # 2. Prepare features
        print("\n[INFO] Preparing features...")
        X, y = self.prepare_features(trades_df)
        
        if len(X) < MIN_TRADES_FOR_TRAINING:
            reason = f"Not enough valid features ({len(X)} < {MIN_TRADES_FOR_TRAINING})"
            print(f"[SKIP] {reason}")
            self.log_training_attempt(len(X), 0, 0, False, reason)
            return
        
        # 3. Split train/validation
        X_train, X_val, y_train, y_val = train_test_split(
            X, y, test_size=VALIDATION_SPLIT, random_state=42, stratify=y
        )
        
        print(f"[INFO] Train: {len(X_train)} | Validation: {len(X_val)}")
        
        # 4. Train new model
        new_model = self.train_new_model(X_train, y_train)
        
        # 5. Evaluate new model
        new_wr, _ = self.evaluate_model(new_model, X_val, y_val)
        print(f"\n[INFO] New model validation winrate: {new_wr:.1f}%")
        
        # 6. Compare with current model (if exists)
        if self.current_model is not None:
            current_wr, _ = self.evaluate_model(self.current_model, X_val, y_val)
            print(f"[INFO] Current model validation winrate: {current_wr:.1f}%")
            
            # Decision: Update only if new is better
            if new_wr > current_wr:
                improvement = new_wr - current_wr
                print(f"\n[OK] NEW MODEL IS BETTER (+{improvement:.1f}%)")
                print("[UPDATE] Updating model...")
                
                metadata = {
                    'training_date': datetime.now().isoformat(),
                    'trades_used': len(X),
                    'train_samples': len(X_train),
                    'validation_samples': len(X_val),
                    'validation_winrate': new_wr,
                    'previous_winrate': current_wr,
                    'improvement': improvement
                }
                
                self.save_model(new_model, metadata)
                self.log_training_attempt(len(X), current_wr, new_wr, True, f"Improved by {improvement:.1f}%")
                
                print("\n[SUCCESS] MODEL UPDATED SUCCESSFULLY!")
            else:
                decline = current_wr - new_wr
                reason = f"New model worse by {decline:.1f}%"
                print(f"\n[SKIP] {reason}")
                print("[INFO] Keeping current model")
                self.log_training_attempt(len(X), current_wr, new_wr, False, reason)
        else:
            # No current model, save this as first model
            print("\n[OK] No current model. Saving as first model...")
            
            metadata = {
                'training_date': datetime.now().isoformat(),
                'trades_used': len(X),
                'train_samples': len(X_train),
                'validation_samples': len(X_val),
                'validation_winrate': new_wr,
                'is_first_model': True
            }
            
            self.save_model(new_model, metadata)
            self.log_training_attempt(len(X), 0, new_wr, True, "First model created")
            
            print("\n[SUCCESS] FIRST MODEL CREATED SUCCESSFULLY!")
        
        print("\n" + "="*60)
        print("[OK] AUTO-TRAINER COMPLETED")
        print("="*60)


if __name__ == "__main__":
    trainer = AutoTrainer()
    trainer.run()
