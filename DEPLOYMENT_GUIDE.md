# 🚀 GUÍA DE DEPLOYMENT - BOT EMA PULLBACK (7 FEATURES)

## Estado Actual
✅ **Modelo ML**: Entrenado con 7 features (63.4% accuracy)
✅ **Backtesting**: Completado - 56% winrate en datos reales
✅ **Bot**: Listo para operar
⏳ **Credenciales**: Pendiente de configurar

---

## 📋 Checklist Pre-Deployment

### 1. Configurar Variables de Entorno (.env)

Necesitas obtener 3 credenciales:

#### POCKETOPTION_SSID
```
Dónde obtenerlo:
1. Ve a https://pocketoption.com
2. Inicia sesión con tu cuenta
3. Abre DevTools (F12)
4. Ve a Application > Cookies
5. Busca "ssid" o "PHPSESSID"
6. Copia el valor (son muchos caracteres)
7. Pégalo en .env como: POCKETOPTION_SSID=valor_aqui
```

#### TELEGRAM_TOKEN
```
Cómo obtenerlo:
1. Abre Telegram
2. Busca @BotFather
3. Escribe /start → /newbot
4. Dale un nombre a tu bot
5. @BotFather te dará un TOKEN
6. Formato: 123456:ABCdef-ghijklmnopqrst_uvwxyz123456
7. Pégalo en .env como: TELEGRAM_TOKEN=valor_aqui
```

#### TELEGRAM_CHAT_ID
```
Cómo obtenerlo:
1. Crea un grupo o usa chat privado conmigo
2. Escribe un mensaje
3. Abre en el navegador:
   https://api.telegram.org/bot{TOKEN}/getUpdates
   (Reemplaza {TOKEN} con tu TELEGRAM_TOKEN)
4. Busca "chat":{"id":12345678}
5. Ese número es tu CHAT_ID
6. Pégalo en .env como: TELEGRAM_CHAT_ID=12345678
```

### 2. Verificar Configuración

Una vez tengas las credenciales en `.env`, ejecuta:

```powershell
python deploy_check.py
```

Debería mostrar:
```
✅ PASS: Entorno
✅ PASS: Modelo ML
✅ PASS: Metadata
✅ PASS: Logging
✅ PASS: Telegram
✅ PASS: Backtesting

✅ TODO LISTO PARA DESPLEGAR
```

### 3. Iniciar el Bot

Una vez que deployment check pase todo:

```powershell
python bots/bot_ema_pullback.py
```

El bot debería mostrar:
```
BOT EMA PULLBACK INICIADO
Pares: 7 | Risk: 1.0% | Cooldown: 60s
✅ Modelo ML con hot-reload (threshold: 60%)
✅ Telegram Listener iniciado
```

---

## 📊 Especificaciones del Bot

| Característica | Valor |
|---|---|
| **Estrategia** | EMA Pullback (E8 > E21 > E55) |
| **Features ML** | 7 (price, duration, pair_idx, ema8, ema21, ema55, hour_normalized) |
| **Accuracy** | 63.4% (training), 56% (real data) |
| **Pares** | EURUSD, GBPUSD, AUDUSD, USDCAD, AUDCAD, USDMXN, USDCOP |
| **Timeframes** | M1 (60s), M5 (300s) |
| **Risk per Trade** | 1% del balance |
| **ML Threshold** | 60% (solo trades con ≥60% confianza) |
| **Check Interval** | Cada 7 segundos |
| **Cooldown** | 60 segundos entre trades del mismo par |

---

## 🎮 Comandos Telegram

Mientras el bot está corriendo, puedes usar estos comandos:

```
/balance      → Ver balance actual
/info         → Resumen de últimos trades
/info_details [FECHA] → Detalles por fecha (ej: /info_details 2025-12-07)
/range_stats  → Estadísticas por rango de horas
/range_detailed → Trades detallados en rango
/commands     → Ayuda de comandos
```

---

## 📈 Monitoreo

El bot mandará mensajes automáticos a Telegram cuando:

- 🚀 Genera una señal y entra a una operación
- ✅ Gana una operación (con ganancia)
- ❌ Pierde una operación (con pérdida)
- ⚠️ Hay errores o problemas de conexión

---

## 🔧 Troubleshooting

### "SSID inválido" o "Sesión expirada"
```
→ El SSID expira. Necesitas obtener uno nuevo de PocketOption
→ Repite el proceso de obtener SSID
→ Asegúrate de copiar TODO (es un string largo)
```

### "Telegram: Token inválido"
```
→ Revisa que copiaste el token completo de @BotFather
→ No debe tener espacios extras
→ Asegúrate de usar el token del bot correcto
```

### "No genera trades"
```
→ Revisa que haya suficientes datos históricos
→ Verifica las velas en el precio actual
→ Aumenta CHECK_EVERY_SECONDS si hay timeout
→ Revisa logs en logs/trades/
```

### Bot crashes
```
→ Revisa la consola para el error específico
→ Intenta con credenciales nuevas
→ Verifica conexión a internet
→ Revisa que POCKETOPTION_SSID sea válido
```

---

## 📝 Archivos Importantes

```
bots/bot_ema_pullback.py        → Bot principal
ml_model.pkl                     → Modelo ML entrenado
logs/trades/trades_YYYYMMDD.csv  → Logs de trades
.env                             → Variables de entorno (NO COMMITEAR)
deploy_check.py                  → Verificador de deployment
```

---

## 🔐 Seguridad

⚠️ **IMPORTANTE:**
- Nunca compartas tu SSID de PocketOption
- Nunca compartas tu TELEGRAM_TOKEN
- Nunca hagas commit del archivo `.env`
- Guarda backups de tus credenciales en lugar seguro

---

## 📞 Soporte

Si hay problemas:

1. Ejecuta `python deploy_check.py` para diagnóstico
2. Revisa `logs/trades/` para ver qué trades se ejecutaron
3. Revisa mensajes de Telegram para alertas
4. Mira la consola del bot para errores

---

## 🚀 ¡A Operar!

Una vez tengas todo configurado:

```powershell
# Terminal 1: Iniciar bot
python bots/bot_ema_pullback.py

# Terminal 2: Monitorear (opcional)
python backtest_real_ema_7features.py  # Ver análisis en tiempo real
```

**El bot operará automáticamente cada 7 segundos.**
**Monitorea en Telegram para alertas en tiempo real.**

---

**Fecha de preparación**: 2025-12-07
**Modelo**: 7 Features EMA Pullback
**Estado**: ✅ Listo para desplegar
