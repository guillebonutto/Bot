#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
telegram_formatter.py
═════════════════════
Módulo para enviar mensajes bonitos a Telegram
"""

import os
import requests
from datetime import datetime


class TelegramFormatter:
    """Formateador de mensajes para Telegram."""
    
    def __init__(self, token=None, chat_id=None):
        """Inicializar con token y chat_id."""
        self.token = token or os.getenv("TELEGRAM_TOKEN")
        self.chat_id = chat_id or os.getenv("TELEGRAM_CHAT_ID")
    
    def is_configured(self):
        """Verificar si Telegram está configurado."""
        return bool(self.token and self.chat_id)
    
    def send(self, text, parse_mode="HTML"):
        """Enviar mensaje a Telegram."""
        if not self.is_configured():
            return False
        
        try:
            response = requests.post(
                f"https://api.telegram.org/bot{self.token}/sendMessage",
                json={
                    "chat_id": self.chat_id,
                    "text": text,
                    "parse_mode": parse_mode
                },
                timeout=10
            )
            return response.status_code == 200
        except Exception as e:
            print(f"⚠️ Error Telegram: {e}")
            return False
    
    def trade_signal(self, pair, direction, price, timeframe, confidence=None):
        """Formato bonito para señal de trading."""
        emoji_direction = "📈 BUY" if direction.upper() == "BUY" else "📉 SELL"
        emoji_pair = self._get_pair_emoji(pair)
        
        message = f"""
<b>🎯 NUEVA SEÑAL</b>

<b>Par:</b> {emoji_pair} {pair}
<b>Dirección:</b> {emoji_direction}
<b>Timeframe:</b> ⏱️ {timeframe}
<b>Precio:</b> 💲 {price:.5f}"""
        
        if confidence:
            message += f"\n<b>Confianza:</b> 📊 {confidence*100:.1f}%"
        
        message += f"\n\n<i>⏰ {datetime.now().strftime('%H:%M:%S')}</i>"
        
        return self.send(message)
    
    def trade_result(self, pair, direction, amount, result, profit_loss=None):
        """Formato bonito para resultado de operación."""
        emoji_result = "✅ WIN" if result.upper() == "WIN" else "❌ LOSS"
        emoji_pair = self._get_pair_emoji(pair)
        emoji_direction = "📈" if direction.upper() == "BUY" else "📉"
        
        message = f"""
<b>🏁 OPERACIÓN FINALIZADA</b>

<b>Resultado:</b> {emoji_result}
<b>Par:</b> {emoji_pair} {pair}
<b>Dirección:</b> {emoji_direction} {direction.upper()}
<b>Monto:</b> 💵 ${amount:.2f}"""
        
        if profit_loss is not None:
            emoji_profit = "📈" if profit_loss >= 0 else "📉"
            message += f"\n<b>Ganancia/Pérdida:</b> {emoji_profit} ${profit_loss:+.2f}"
        
        message += f"\n\n<i>⏰ {datetime.now().strftime('%H:%M:%S')}</i>"
        
        return self.send(message)
    
    def session_started(self, bot_name):
        """Formato para inicio de sesión."""
        message = f"""
<b>🚀 SESIÓN INICIADA</b>

<b>Bot:</b> {bot_name}
<b>Hora:</b> ⏰ {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}

Estado: ✅ Operando
        """
        return self.send(message)
    
    def session_error(self, error_msg, bot_name=None):
        """Formato para errores."""
        title = f"❌ ERROR ({bot_name})" if bot_name else "❌ ERROR"
        message = f"""
<b>{title}</b>

<b>Mensaje:</b>
<code>{error_msg}</code>

<i>⏰ {datetime.now().strftime('%H:%M:%S')}</i>
        """
        return self.send(message)
    
    def balance_alert(self, balance, threshold=50):
        """Alerta de balance bajo."""
        message = f"""
<b>⚠️ ALERTA DE BALANCE</b>

<b>Balance Actual:</b> 💰 ${balance:.2f}
<b>Umbral Crítico:</b> 🔴 ${threshold:.2f}

⚠️ El balance es bajo. Considera hacer depósito.

<i>⏰ {datetime.now().strftime('%H:%M:%S')}</i>
        """
        return self.send(message)
    
    def daily_stats(self, total_trades, wins, losses, winrate, balance):
        """Resumen diario de estadísticas."""
        message = f"""
<b>📊 RESUMEN DIARIO</b>

<b>Operaciones:</b> 📈 {total_trades}
<b>Ganancias:</b> ✅ {wins}
<b>Pérdidas:</b> ❌ {losses}
<b>Tasa de Ganancia:</b> 📊 {winrate:.1f}%
<b>Balance:</b> 💰 ${balance:.2f}

<i>⏰ {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}</i>
        """
        return self.send(message)
    
    def status_update(self, pairs_monitored, active_bots, current_balance):
        """Actualización de estado del sistema."""
        message = f"""
<b>🔔 ESTADO DEL SISTEMA</b>

<b>Pares Monitoreados:</b> 📊 {pairs_monitored}
<b>Bots Activos:</b> 🤖 {active_bots}
<b>Balance:</b> 💰 ${current_balance:.2f}

Estado: ✅ En operación

<i>⏰ {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}</i>
        """
        return self.send(message)
    
    def custom_message(self, title, content_dict):
        """Mensaje personalizado con diccionario de contenido."""
        message = f"<b>{title}</b>\n\n"
        
        for key, value in content_dict.items():
            message += f"<b>{key}:</b> {value}\n"
        
        message += f"\n<i>⏰ {datetime.now().strftime('%H:%M:%S')}</i>"
        
        return self.send(message)
    
    @staticmethod
    def _get_pair_emoji(pair):
        """Obtener emoji para el par de monedas."""
        emojis = {
            'EUR': '🇪🇺',
            'USD': '🇺🇸',
            'GBP': '🇬🇧',
            'JPY': '🇯🇵',
            'AUD': '🇦🇺',
            'CAD': '🇨🇦',
            'CHF': '🇨🇭',
            'MXN': '🇲🇽',
            'COP': '🇨🇴',
        }
        
        # Extraer monedas base y cotizada
        if '_otc' in pair:
            pair = pair.replace('_otc', '')
        
        if len(pair) >= 6:
            base = pair[:3]
            quote = pair[3:6]
            return f"{emojis.get(base, '💱')}/{emojis.get(quote, '💱')}"
        
        return '💱'


# Instancia global para usar fácilmente
telegram = TelegramFormatter()


def send_trade_signal(pair, direction, price, timeframe, confidence=None):
    """Función auxiliar: Enviar señal de trading."""
    return telegram.trade_signal(pair, direction, price, timeframe, confidence)


def send_trade_result(pair, direction, amount, result, profit_loss=None):
    """Función auxiliar: Enviar resultado de operación."""
    return telegram.trade_result(pair, direction, amount, result, profit_loss)


def send_session_started(bot_name="Trading Bot"):
    """Función auxiliar: Sesión iniciada."""
    return telegram.session_started(bot_name)


def send_error(error_msg, bot_name=None):
    """Función auxiliar: Enviar error."""
    return telegram.session_error(error_msg, bot_name)


def send_balance_alert(balance, threshold=50):
    """Función auxiliar: Alerta de balance bajo."""
    return telegram.balance_alert(balance, threshold)


def send_daily_stats(total_trades, wins, losses, winrate, balance):
    """Función auxiliar: Estadísticas diarias."""
    return telegram.daily_stats(total_trades, wins, losses, winrate, balance)


def send_status_update(pairs_monitored, active_bots, current_balance):
    """Función auxiliar: Actualización de estado."""
    return telegram.status_update(pairs_monitored, active_bots, current_balance)


if __name__ == "__main__":
    # Test
    formatter = TelegramFormatter()
    
    if formatter.is_configured():
        print("✅ Telegram está configurado")
        print("\nEnviando mensajes de prueba...")
        
        # Probar diferentes formatos
        formatter.trade_signal("EURUSD_otc", "BUY", 1.0950, "M5", 85.5)
        formatter.trade_result("EURUSD_otc", "BUY", 10.0, "WIN", 5.5)
        formatter.session_started("Bot EMA Pullback")
        formatter.daily_stats(15, 10, 5, 66.7, 250.50)
        
        print("✅ Mensajes enviados")
    else:
        print("⚠️ Telegram no está configurado")
        print("   Configura TELEGRAM_TOKEN y TELEGRAM_CHAT_ID en .env")
