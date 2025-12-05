import requests
import os
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

print("=" * 60)
print("🧪 TEST DE CONFIGURACIÓN DE TELEGRAM")
print("=" * 60)

# Obtener credenciales
token = os.getenv("TELEGRAM_TOKEN")
chat_id = os.getenv("TELEGRAM_CHAT_ID")

# Mostrar estado
print(f"\n📋 Estado de variables:")
if token:
    print(f"✅ TELEGRAM_TOKEN: {token[:10]}...{token[-5:]} ({len(token)} chars)")
else:
    print("❌ TELEGRAM_TOKEN: No configurado")

if chat_id:
    print(f"✅ TELEGRAM_CHAT_ID: {chat_id}")
else:
    print("❌ TELEGRAM_CHAT_ID: No configurado")

# Intentar enviar mensaje de prueba
if token and chat_id:
    print(f"\n📤 Enviando mensaje de prueba...")
    try:
        response = requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={
                "chat_id": chat_id,
                "text": "🧪 Test desde PocketOptions Bot\n\n✅ La configuración de Telegram está funcionando correctamente!"
            },
            timeout=10
        )
        
        print(f"\n📊 Respuesta del servidor:")
        print(f"Status Code: {response.status_code}")
        
        result = response.json()
        print(f"Response: {result}")
        
        if response.status_code == 200 and result.get('ok'):
            print("\n✅ ¡ÉXITO! El mensaje fue enviado correctamente.")
            print("   Revisá tu Telegram para ver el mensaje.")
        else:
            print(f"\n❌ ERROR: {result.get('description', 'Unknown error')}")
            
            if 'Unauthorized' in str(result):
                print("\n💡 Solución: El token es inválido. Verificá que:")
                print("   1. Hayas copiado el token completo del BotFather")
                print("   2. No haya espacios al inicio o final")
                
            elif 'chat not found' in str(result).lower():
                print("\n💡 Solución: El chat_id es incorrecto. Para obtenerlo:")
                print("   1. Enviá un mensaje a tu bot en Telegram")
                print("   2. Visitá: https://api.telegram.org/bot{TOKEN}/getUpdates")
                print("   3. Buscá el 'chat' -> 'id' en la respuesta")
                
    except requests.exceptions.Timeout:
        print("\n⏱️ ERROR: Timeout - No se pudo conectar a Telegram")
        print("   Verificá tu conexión a internet")
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
else:
    print("\n⚠️ No se puede enviar mensaje de prueba.")
    print("   Configurá TELEGRAM_TOKEN y TELEGRAM_CHAT_ID en tu .env")
    print("\n📝 Formato del archivo .env:")
    print("   TELEGRAM_TOKEN=123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11")
    print("   TELEGRAM_CHAT_ID=123456789")

print("\n" + "=" * 60)
