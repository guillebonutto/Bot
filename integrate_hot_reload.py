"""
Script para integrar ml_model_manager en bot_ema_pullback.py
Ejecutar este script para aplicar las optimizaciones automáticamente
"""

import re

def integrate_hot_reload():
    bot_file = "bots/bot_ema_pullback.py"
    
    with open(bot_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 1. Reemplazar la sección de carga del modelo
    old_model_loading = r'''try:
    import joblib
    model = joblib.load\("ml_model\.pkl"\)
    ML_ACTIVE = True
    ML_THRESHOLD = 0\.70  # Optimizado de 0\.62 a 0\.70 basado en análisis
    print\("Modelo ML cargado"\)
except:
    ML_ACTIVE = False
    print\("Sin modelo ML"\)'''
    
    new_model_loading = '''# ========================= ML MODEL WITH HOT-RELOAD =========================
try:
    from ml_model_manager import ml_manager
    ML_ACTIVE = ml_manager.is_active()
    ML_THRESHOLD = 0.70  # Optimizado basado en análisis
    print(f"✅ Modelo ML con hot-reload (threshold: {ML_THRESHOLD:.0%})")
except ImportError:
    # Fallback si ml_model_manager no está disponible
    try:
        import joblib
        model = joblib.load("ml_model.pkl")
        ml_manager = None
        ML_ACTIVE = True
        ML_THRESHOLD = 0.70
        print("⚠️ Modelo ML sin hot-reload")
    except:
        model = None
        ml_manager = None
        ML_ACTIVE = False
        ML_THRESHOLD = 0.70
        print("❌ Sin modelo ML")'''
    
    content = re.sub(old_model_loading, new_model_loading, content, flags=re.MULTILINE)
    
    # 2. Actualizar predicciones para usar ml_manager (BUY)
    old_predict_buy = r'            features = \[\[c, e8, e21, e55, duration/60, pair_idx\]\]\n            prob = model\.predict_proba\(features\)\[0\]\[1\]'
    
    new_predict_buy = '''            features = [[c, e8, e21, e55, duration/60, pair_idx]]
            # Usar ml_manager si está disponible (thread-safe)
            if 'ml_manager' in globals() and ml_manager is not None:
                prob_result = ml_manager.predict_proba(features)
                if prob_result is None:
                    return None
                prob = prob_result[0][1]
            else:
                prob = model.predict_proba(features)[0][1]'''
    
    content = re.sub(old_predict_buy, new_predict_buy, content, count=1)
    
    # 3. Actualizar predicciones para usar ml_manager (SELL)
    old_predict_sell = r'            features = \[\[c, e8, e21, e55, duration/60, pair_idx\]\]\n            prob = model\.predict_proba\(features\)\[0\]\[0\]'
    
    new_predict_sell = '''            features = [[c, e8, e21, e55, duration/60, pair_idx]]
            # Usar ml_manager si está disponible (thread-safe)
            if 'ml_manager' in globals() and ml_manager is not None:
                prob_result = ml_manager.predict_proba(features)
                if prob_result is None:
                    return None
                prob = prob_result[0][0]
            else:
                prob = model.predict_proba(features)[0][0]'''
    
    content = re.sub(old_predict_sell, new_predict_sell, content, count=1)
    
    # Guardar cambios
    with open(bot_file, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("✅ Integración completada!")
    print("   - Hot-reload activado")
    print("   - Auto-entrenamiento cada 24h")
    print("   - Threshold optimizado a 70%")
    print("\nReinicia el bot para aplicar los cambios.")

if __name__ == "__main__":
    integrate_hot_reload()
