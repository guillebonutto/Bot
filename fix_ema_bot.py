"""
Script para arreglar el bot EMA Pullback
Soluciona el problema de ml_manager y model scope
"""

import re

def fix_bot():
    bot_file = "bots/bot_ema_pullback.py"
    
    with open(bot_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 1. Arreglar la inicialización del modelo
    old_init = r'''# ========================= ML MODEL WITH HOT-RELOAD =========================
try:
    from ml_model_manager import ml_manager
    ML_ACTIVE = ml_manager\.is_active\(\)
    ML_THRESHOLD = 0\.70  # Optimizado basado en análisis
    print\(f"✅ Modelo ML con hot-reload \(threshold: {ML_THRESHOLD:.0%}\)"\)
except ImportError:
    # Fallback si ml_model_manager no está disponible
    try:
        import joblib
        model = joblib\.load\("ml_model\.pkl"\)
        ml_manager = None
        ML_ACTIVE = True
        ML_THRESHOLD = 0\.70
        print\("⚠️ Modelo ML sin hot-reload"\)
    except:
        model = None
        ml_manager = None
        ML_ACTIVE = False
        ML_THRESHOLD = 0\.70
        print\("❌ Sin modelo ML"\)'''
    
    new_init = '''# ========================= ML MODEL WITH HOT-RELOAD =========================
# Inicializar variables globales primero
ml_manager = None
model = None

try:
    from ml_model_manager import ml_manager as _ml_manager
    ml_manager = _ml_manager
    ML_ACTIVE = ml_manager.is_active()
    ML_THRESHOLD = 0.70  # Optimizado basado en análisis
    print(f"✅ Modelo ML con hot-reload (threshold: {ML_THRESHOLD:.0%})")
except ImportError:
    # Fallback si ml_model_manager no está disponible
    try:
        import joblib
        model = joblib.load("ml_model.pkl")
        ML_ACTIVE = True
        ML_THRESHOLD = 0.70
        print(f"⚠️ Modelo ML sin hot-reload (threshold: {ML_THRESHOLD:.0%})")
    except Exception as e:
        ML_ACTIVE = False
        ML_THRESHOLD = 0.70
        print(f"❌ Sin modelo ML: {e}")'''
    
    content = re.sub(old_init, new_init, content, flags=re.MULTILINE | re.DOTALL)
    
    # 2. Arreglar predicción BUY (eliminar globals() check y duplicados)
    old_predict_buy = r'''            features = \[\[c, e8, e21, e55, duration/60, pair_idx\]\]
            # Usar ml_manager si está disponible \(thread-safe\)
            if 'ml_manager' in globals\(\) and ml_manager is not None:
                prob_result = ml_manager\.predict_proba\(features\)
                if prob_result is None:
                    return None
                prob = prob_result\[0\]\[1\]
            else:
                prob = model\.predict_proba\(features\)\[0\]\[1\]
            if prob < ML_THRESHOLD:
                return None
            if prob < ML_THRESHOLD:
                return None'''
    
    new_predict_buy = '''            features = [[c, e8, e21, e55, duration/60, pair_idx]]
            # Usar ml_manager si está disponible (thread-safe)
            if ml_manager is not None:
                prob_result = ml_manager.predict_proba(features)
                if prob_result is None:
                    return None
                prob = prob_result[0][1]
            elif model is not None:
                prob = model.predict_proba(features)[0][1]
            else:
                prob = 1.0  # Sin modelo, aceptar señal
            
            if prob < ML_THRESHOLD:
                return None'''
    
    content = re.sub(old_predict_buy, new_predict_buy, content, count=1)
    
    # 3. Arreglar predicción SELL
    old_predict_sell = r'''            features = \[\[c, e8, e21, e55, duration/60, pair_idx\]\]
            # Usar ml_manager si está disponible \(thread-safe\)
            if 'ml_manager' in globals\(\) and ml_manager is not None:
                prob_result = ml_manager\.predict_proba\(features\)
                if prob_result is None:
                    return None
                prob = prob_result\[0\]\[0\]
            else:
                prob = model\.predict_proba\(features\)\[0\]\[0\]
            if prob < ML_THRESHOLD:
                return None
            if prob < ML_THRESHOLD:
                return None'''
    
    new_predict_sell = '''            features = [[c, e8, e21, e55, duration/60, pair_idx]]
            # Usar ml_manager si está disponible (thread-safe)
            if ml_manager is not None:
                prob_result = ml_manager.predict_proba(features)
                if prob_result is None:
                    return None
                prob = prob_result[0][0]
            elif model is not None:
                prob = model.predict_proba(features)[0][0]
            else:
                prob = 1.0  # Sin modelo, aceptar señal
            
            if prob < ML_THRESHOLD:
                return None'''
    
    content = re.sub(old_predict_sell, new_predict_sell, content, count=1)
    
    # Guardar cambios
    with open(bot_file, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("✅ Bot arreglado!")
    print("   - ml_manager y model ahora son variables globales")
    print("   - Eliminados checks duplicados de threshold")
    print("   - Fallback correcto cuando no hay modelo")
    print("\nReinicia el bot para aplicar los cambios.")

if __name__ == "__main__":
    fix_bot()
