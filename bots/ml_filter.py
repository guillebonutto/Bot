"""
ML Filter - Common ML prediction filter for all bots
"""
import os
import joblib
import numpy as np
import pandas as pd
from typing import Dict, Optional

class MLFilter:
    """
    Common ML filter that loads a trained model and predicts success probability.
    """
    
    def __init__(self, model_path: str, threshold: float = 0.65):
        """
        Args:
            model_path: Path to the trained model (.pkl file)
            threshold: Minimum probability to accept signal (0-1)
        """
        self.threshold = threshold
        self.model = None
        
        if os.path.exists(model_path):
            try:
                self.model = joblib.load(model_path)
                print(f"✅ ML Model loaded: {model_path}")
            except Exception as e:
                print(f"⚠️ Error loading model {model_path}: {e}")
                self.model = None
        else:
            print(f"⚠️ Model not found: {model_path} - ML filter disabled")
    
    def predict(self, features: Dict[str, float]) -> float:
        """
        Predict success probability for a signal.
        
        Args:
            features: Dict with feature names and values
            
        Returns:
            float: Probability of success (0-1), or 1.0 if model not loaded
        """
        if self.model is None:
            # No model loaded, accept all signals
            return 1.0
        
        try:
            # Convert features dict to DataFrame
            X = pd.DataFrame([features])
            
            # Predict probability
            proba = self.model.predict_proba(X)[0][1]
            
            return float(proba)
            
        except Exception as e:
            print(f"⚠️ ML prediction error: {e}")
            return 0.0
    
    def should_trade(self, features: Dict[str, float]) -> bool:
        """
        Check if signal passes ML filter threshold.
        
        Args:
            features: Dict with feature names and values
            
        Returns:
            bool: True if probability >= threshold
        """
        proba = self.predict(features)
        return proba >= self.threshold
