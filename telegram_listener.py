#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
telegram_listener.py
====================
Módulo para escuchar comandos de Telegram y responder con información del bot.
Soporta:
- /balance: Muestra el balance actual
- /info: Muestra estadísticas y gráfico de progreso
"""

import os
import time
import threading
import requests
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime
import io
import glob

# Configurar matplotlib para backend no interactivo (thread-safe)
plt.switch_backend('Agg')

class TelegramListener:
    def __init__(self, token, get_balance_callback=None):
        self.token = token
        self.get_balance_callback = get_balance_callback
        self.offset = 0
        self.running = False
        self.base_url = f"https://api.telegram.org/bot{self.token}"
        self.logs_dir = "logs/trades"
    
    def start(self):
        """Iniciar el listener en un hilo separado."""
        if not self.token:
            print("⚠️ TelegramListener: No token provided")
            return
        
        self.running = True
        thread = threading.Thread(target=self._poll_loop, daemon=True)
        thread.start()
        print("🎧 TelegramListener iniciado (esperando comandos /balance, /info)")
    
    def stop(self):
        """Detener el listener."""
        self.running = False
    
    def _poll_loop(self):
        """Bucle principal de polling."""
        while self.running:
            try:
                updates = self._get_updates()
                for update in updates:
                    self._process_update(update)
                    # Actualizar offset para no procesar el mismo mensaje
                    self.offset = update["update_id"] + 1
                
                time.sleep(2)  # Polling interval
            except Exception as e:
                print(f"⚠️ Error en Telegram polling: {e}")
                time.sleep(5)
    
    def _get_updates(self):
        """Obtener actualizaciones de Telegram."""
        try:
            url = f"{self.base_url}/getUpdates"
            params = {"offset": self.offset, "timeout": 10}
            response = requests.get(url, params=params, timeout=15)
            if response.status_code == 200:
                return response.json().get("result", [])
        except Exception:
            pass
        return []
    
    def _process_update(self, update):
        """Procesar una actualización (mensaje)."""
        message = update.get("message")
        if not message:
            return
        
        chat_id = message.get("chat", {}).get("id")
        text = message.get("text", "").strip()
        
        if not chat_id or not text:
            return
        
        if text.lower() == "/balance":
            self._handle_balance(chat_id)
        elif text.lower() == "/info":
            self._handle_info(chat_id)
    
    def _handle_balance(self, chat_id):
        """Manejar comando /balance."""
        balance = "Desconocido"
        if self.get_balance_callback:
            try:
                balance = self.get_balance_callback()
            except Exception as e:
                balance = f"Error: {e}"
        
        if isinstance(balance, (int, float)):
            msg = f"💰 <b>Balance Actual:</b> ${balance:.2f}"
        else:
            msg = f"💰 <b>Balance Actual:</b> {balance}"
        
        self._send_message(chat_id, msg)
    
    def _handle_info(self, chat_id):
        """Manejar comando /info (estadísticas + gráfico)."""
        self._send_message(chat_id, "⏳ Generando reporte histórico...")
        
        # 1. Obtener estadísticas
        stats = self._get_stats()
        
        # 2. Generar gráfico
        chart_buffer = self._generate_chart()
        
        # 3. Enviar mensaje con estadísticas
        start_date = stats.get('start_date', 'N/A')
        
        msg = f"""
<b>📊 REPORTE HISTÓRICO</b>
<i>Desde: {start_date}</i>

<b>💰 Balance Actual:</b> ${stats['balance']:.2f}

<b>🏆 GLOBAL (Todo el historial)</b>
• Trades: {stats['total_trades']}
• Winrate: {stats['total_winrate']:.1f}%
• P&L: {stats['total_pnl']:+.2f}

<b>📅 HOY</b>
• Trades: {stats['today_trades']}
• Winrate: {stats['today_winrate']:.1f}%
• P&L: {stats['today_pnl']:+.2f}

<i>Generado: {datetime.now().strftime('%H:%M:%S')}</i>
        """
        
        if chart_buffer:
            self._send_photo(chat_id, chart_buffer, caption=msg)
        else:
            self._send_message(chat_id, msg)
    
    def _get_stats(self):
        """Calcular estadísticas desde los logs."""
        stats = {
            'balance': 0.0,
            'today_trades': 0,
            'today_winrate': 0.0,
            'today_pnl': 0.0,
            'total_trades': 0,
            'total_winrate': 0.0,
            'total_pnl': 0.0
        }
        
        # Obtener balance actual
        if self.get_balance_callback:
            try:
                stats['balance'] = float(self.get_balance_callback())
            except:
                pass
        
        # Cargar trades
        try:
            all_files = glob.glob(os.path.join(self.logs_dir, "trades_*.csv"))
            if not all_files:
                return stats
            
            df = pd.concat((pd.read_csv(f) for f in all_files), ignore_index=True)
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            
            # Filtrar completados
            completed = df[df['result'].isin(['WIN', 'LOSS'])]
            
            if len(completed) > 0:
                stats['start_date'] = completed['timestamp'].min().strftime('%d/%m/%Y')
                stats['total_trades'] = len(completed)
                wins = len(completed[completed['result'] == 'WIN'])
                stats['total_winrate'] = (wins / len(completed)) * 100
                if 'profit_loss' in completed.columns:
                    stats['total_pnl'] = completed['profit_loss'].sum()
            
            # Trades de hoy
            today = datetime.now().date()
            df_today = completed[completed['timestamp'].dt.date == today]
            
            if len(df_today) > 0:
                stats['today_trades'] = len(df_today)
                wins_today = len(df_today[df_today['result'] == 'WIN'])
                stats['today_winrate'] = (wins_today / len(df_today)) * 100
                if 'profit_loss' in df_today.columns:
                    stats['today_pnl'] = df_today['profit_loss'].sum()
                    
        except Exception as e:
            print(f"⚠️ Error calculando stats: {e}")
        
        return stats
    
    def _generate_chart(self):
        """Generar gráfico de balance/P&L acumulado."""
        try:
            all_files = glob.glob(os.path.join(self.logs_dir, "trades_*.csv"))
            if not all_files:
                return None
            
            df = pd.concat((pd.read_csv(f) for f in all_files), ignore_index=True)
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df = df.sort_values('timestamp')
            
            # Filtrar completados con P&L
            if 'profit_loss' not in df.columns:
                return None
            
            df = df[df['result'].isin(['WIN', 'LOSS'])].copy()
            if len(df) == 0:
                return None
            
            # Calcular P&L acumulado
            df['cumulative_pnl'] = df['profit_loss'].cumsum()
            
            # Crear gráfico
            plt.figure(figsize=(12, 6))
            
            # Estilo moderno
            plt.style.use('bmh')  # Estilo limpio
            
            # Graficar línea principal
            plt.plot(df['timestamp'], df['cumulative_pnl'], label='P&L Acumulado', color='#2ecc71', linewidth=2)
            
            # Relleno suave (opcional, pero mejor configurado)
            plt.fill_between(df['timestamp'], df['cumulative_pnl'], alpha=0.1, color='#2ecc71')
            
            # Línea de cero (breakeven)
            plt.axhline(y=0, color='gray', linestyle='--', alpha=0.5, linewidth=1)
            
            # Puntos en máximos y mínimos
            max_pnl = df['cumulative_pnl'].max()
            min_pnl = df['cumulative_pnl'].min()
            
            # Títulos y etiquetas
            plt.title(f'Crecimiento de la Cuenta (Total: ${df["cumulative_pnl"].iloc[-1]:.2f})', fontsize=14, fontweight='bold')
            plt.xlabel('Fecha', fontsize=10)
            plt.ylabel('Ganancia Neta ($)', fontsize=10)
            
            # Grid suave
            plt.grid(True, alpha=0.3, linestyle='--')
            plt.legend(loc='upper left')
            
            # Formato de fechas inteligente
            plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%d/%m'))
            plt.gca().xaxis.set_major_locator(mdates.DayLocator(interval=1))  # Un tick por día si es posible
            plt.gcf().autofmt_xdate()  # Rotar fechas
            
            # Márgenes
            plt.tight_layout()
            
            # Guardar en buffer
            buf = io.BytesIO()
            plt.savefig(buf, format='png', dpi=100)
            buf.seek(0)
            plt.close()
            
            return buf
        except Exception as e:
            print(f"⚠️ Error generando gráfico: {e}")
            return None
    
    def _send_message(self, chat_id, text):
        """Enviar mensaje de texto."""
        try:
            requests.post(
                f"{self.base_url}/sendMessage",
                json={"chat_id": chat_id, "text": text, "parse_mode": "HTML"},
                timeout=10
            )
        except Exception as e:
            print(f"⚠️ Error enviando mensaje Telegram: {e}")

    def _send_photo(self, chat_id, photo_buffer, caption=None):
        """Enviar foto."""
        try:
            files = {'photo': ('chart.png', photo_buffer, 'image/png')}
            data = {'chat_id': chat_id, 'parse_mode': 'HTML'}
            if caption:
                data['caption'] = caption
            
            requests.post(
                f"{self.base_url}/sendPhoto",
                data=data,
                files=files,
                timeout=20
            )
        except Exception as e:
            print(f"⚠️ Error enviando foto Telegram: {e}")

# Instancia global (se inicializará desde el bot)
telegram_listener = None
