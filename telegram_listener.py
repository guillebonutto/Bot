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
        
        if text.lower() == "/commands":
            self._command_list(chat_id)
        elif text.lower() == "/balance":
            self._handle_balance(chat_id)
        elif text.lower() == "/info":
            self._handle_info(chat_id)
        elif text.lower().startswith("/info_details"):
            # Robust parsing: remove command prefix and handle separators
            cmd_len = len("/info_details")
            date_arg = text[cmd_len:].strip()
            
            # Remove leading underscore if present (e.g. /info_details_2025...)
            if date_arg.startswith("_"):
                date_arg = date_arg[1:].strip()
            
            self._handle_info_details(chat_id, date_arg)
        elif text.lower().startswith("/range_stats"):
            # Comando para filtrar por rango de fechas y horas
            cmd_len = len("/range_stats")
            args = text[cmd_len:].strip()
            
            # Remove leading underscore if present
            if args.startswith("_"):
                args = args[1:].strip()
            
            self._handle_range_stats(chat_id, args)
        elif text.lower().startswith("/range_detailed"):
            # Comando para ver detalle de cada operación
            cmd_len = len("/range_detailed")
            args = text[cmd_len:].strip()
            
            # Remove leading underscore if present
            if args.startswith("_"):
                args = args[1:].strip()
            
            self._handle_range_detailed(chat_id, args)

    def _command_list(self, chat_id):
        """Retornar la lista de comandos disponibles."""
        msg = """<b>🤖 Comandos Disponibles:</b>

<b>/balance</b>
Muestra el balance actual del bot.

<b>/info</b>
Muestra progreso general y estadísticas totales con gráfico.

<b>/info_details [FECHA]</b>
Muestra progreso del día especificado en detalle con gráfico.
Formato: YYYY-MM-DD o DD/MM/YYYY

<b>/range_stats FECHA_INICIO HORA_INICIO FECHA_FIN HORA_FIN</b>
Muestra estadísticas en un rango de fechas/horas específico (sin gráfico).
Formato: YYYY-MM-DD HH:MM o DD/MM/YYYY HH:MM

<b>/range_detailed FECHA_INICIO HORA_INICIO FECHA_FIN HORA_FIN</b>
Muestra cada operación en detalle en un rango específico.
Formato: YYYY-MM-DD HH:MM o DD/MM/YYYY HH:MM

<i>💡 Ejemplo:</i>
<code>/range_stats 2025-12-01 09:00 2025-12-02 18:00</code>
        """
        self._send_message(chat_id, msg)
    
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
            
    def _handle_info_details(self, chat_id, date_str=None):
        """Manejar comando /info_details (reporte diario detallado)."""
        target_date = datetime.now().date()
        parsing_success = False
        
        if date_str:
            # Intentar varios formatos
            for fmt in ['%Y-%m-%d', '%d/%m/%Y', '%d-%m-%Y', '%Y/%m/%d']:
                try:
                    target_date = datetime.strptime(date_str, fmt).date()
                    parsing_success = True
                    break
                except ValueError:
                    continue
            
            if not parsing_success:
                self._send_message(chat_id, f"⚠️ Formato de fecha no reconocido: '{date_str}'. Usando HOY.\nPrueba: YYYY-MM-DD o DD/MM/YYYY")
        
        self._send_message(chat_id, f"⏳ Generando reporte detallado para {target_date.strftime('%d/%m/%Y')}...")
        
        # Generar gráfico diario y recibir stats específicos
        chart_buffer, daily_stats = self._generate_daily_chart(target_date)
        
        if not daily_stats:
            self._send_message(chat_id, f"❌ No hay datos registrados para el {target_date.strftime('%d/%m/%Y')}.")
            return

        msg = f"""
<b>📅 REPORTE DETALLADO ({target_date.strftime('%d/%m/%Y')})</b>

<b>📊 Resumen del Día</b>
• Trades: {daily_stats['total_trades']}
• Winrate: {daily_stats['winrate']:.1f}%
• P&L Neto: {daily_stats['pnl']:+.2f}

<b>📈 Detalles</b>
• Wins: {daily_stats['wins']}
• Losses: {daily_stats['losses']}
• Mejor Racha: {daily_stats.get('best_streak', 0)} wins

<i>El gráfico muestra la evolución hora a hora.</i>
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
            
            dfs = []
            for f in all_files:
                try:
                    df_temp = pd.read_csv(f)
                    if not df_temp.empty and not df_temp.isna().all().all():
                        dfs.append(df_temp)
                except Exception:
                    continue
            
            if not dfs:
                return stats
                
            df = pd.concat(dfs, ignore_index=True)
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            
            # Filtrar completados
            completed = df[df['result'].isin(['WIN', 'LOSS'])]
            
            # Filtrar trades de DEMO
            if 'trade_id' in completed.columns:
                completed = completed[~completed['trade_id'].astype(str).str.startswith('DEMO')]
            
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

    def _generate_daily_chart(self, target_date):
        """Generar gráfico diario (eje X = horas) y devolver stats."""
        try:
            all_files = glob.glob(os.path.join(self.logs_dir, "trades_*.csv"))
            if not all_files:
                return None, None
            
            dfs = []
            for f in all_files:
                try:
                    df_temp = pd.read_csv(f)
                    if not df_temp.empty and not df_temp.isna().all().all():
                        dfs.append(df_temp)
                except Exception:
                    continue
            
            if not dfs:
                return None, None
                
            df = pd.concat(dfs, ignore_index=True)
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            
            # Filtrar por fecha específica
            df = df[df['timestamp'].dt.date == target_date].copy()
            df = df.sort_values('timestamp')
            
            # Filtrar completados y NO DEMO
            if 'profit_loss' not in df.columns:
                return None, None
            
            df = df[df['result'].isin(['WIN', 'LOSS'])].copy()
            if 'trade_id' in df.columns:
                df = df[~df['trade_id'].astype(str).str.startswith('DEMO')]
            
            if len(df) == 0:
                return None, None
            
            # Stats diarios
            wins = len(df[df['result'] == 'WIN'])
            losses = len(df[df['result'] == 'LOSS'])
            stats = {
                'total_trades': len(df),
                'wins': wins,
                'losses': losses,
                'winrate': (wins / len(df)) * 100 if len(df) > 0 else 0,
                'pnl': df['profit_loss'].sum(),
                # Cálculo simple de racha
                'best_streak': 0 # Simplificado
            }
            
            # Calcular P&L acumulado diario
            df['cumulative_pnl'] = df['profit_loss'].cumsum()
            
            # Crear gráfico
            plt.figure(figsize=(12, 6))
            plt.style.use('bmh')
            
            plt.plot(df['timestamp'], df['cumulative_pnl'], label='P&L Diario', color='#3498db', linewidth=2, marker='o', markersize=4)
            plt.fill_between(df['timestamp'], df['cumulative_pnl'], alpha=0.1, color='#3498db')
            plt.axhline(y=0, color='gray', linestyle='--', alpha=0.5)
            
            plt.title(f'P&L Diario - {target_date.strftime("%d/%m/%Y")} (Total: ${stats["pnl"]:.2f})', fontsize=14, fontweight='bold')
            plt.xlabel('Hora', fontsize=10)
            plt.ylabel('Ganancia Neta ($)', fontsize=10)
            plt.grid(True, alpha=0.3, linestyle='--')
            
            # Formato Eje X: HORAS
            plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
            # Ajustar intervalo de ticks automáticamente o cada hora si hay muchos datos
            # plt.gca().xaxis.set_major_locator(mdates.HourLocator(interval=1)) 
            plt.gcf().autofmt_xdate()
            
            plt.tight_layout()
            
            buf = io.BytesIO()
            plt.savefig(buf, format='png', dpi=100)
            buf.seek(0)
            plt.close()
            
            return buf, stats

        except Exception as e:
            print(f"⚠️ Error generando gráfico diario: {e}")
            return None, None

    def _generate_chart(self):
        """Generar gráfico de balance/P&L acumulado."""
        try:
            all_files = glob.glob(os.path.join(self.logs_dir, "trades_*.csv"))
            if not all_files:
                return None
            
            dfs = []
            for f in all_files:
                try:
                    df_temp = pd.read_csv(f)
                    if not df_temp.empty and not df_temp.isna().all().all():
                        dfs.append(df_temp)
                except Exception:
                    continue
            
            if not dfs:
                return None
                
            df = pd.concat(dfs, ignore_index=True)
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df = df.sort_values('timestamp')
            
            # Filtrar completados con P&L
            if 'profit_loss' not in df.columns:
                return None
            
            df = df[df['result'].isin(['WIN', 'LOSS'])].copy()
            
            # Filtrar trades de DEMO
            if 'trade_id' in df.columns:
                df = df[~df['trade_id'].astype(str).str.startswith('DEMO')]
            
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

    def _handle_range_stats(self, chat_id, args):
        """Manejar comando /range_stats para filtrar por rango de fechas y horas."""
        # Formato esperado: /range_stats YYYY-MM-DD HH:MM YYYY-MM-DD HH:MM
        # O: /range_stats DD/MM/YYYY HH:MM DD/MM/YYYY HH:MM
        
        self._send_message(chat_id, "⏳ Procesando rango de fechas y horas...")
        
        try:
            # Parsear argumentos
            parts = args.split()
            
            if len(parts) < 4:
                self._send_message(
                    chat_id, 
                    """❌ Formato incorrecto.
                    
<b>Uso:</b> /range_stats FECHA_INICIO HORA_INICIO FECHA_FIN HORA_FIN

<b>Ejemplos:</b>
• /range_stats 2025-12-01 09:00 2025-12-01 17:00
• /range_stats 01/12/2025 09:00 01/12/2025 17:00
• /range_stats 2025-12-01 09:00 2025-12-02 18:30

<b>Formatos de fecha aceptados:</b>
• YYYY-MM-DD (2025-12-01)
• DD/MM/YYYY (01/12/2025)
                    """
                )
                return
            
            fecha_inicio_str = parts[0]
            hora_inicio_str = parts[1]
            fecha_fin_str = parts[2]
            hora_fin_str = parts[3]
            
            # Parsear fechas
            fecha_inicio = None
            fecha_fin = None
            
            for fmt in ['%Y-%m-%d', '%d/%m/%Y']:
                try:
                    fecha_inicio = datetime.strptime(fecha_inicio_str, fmt).date()
                    break
                except ValueError:
                    continue
            
            for fmt in ['%Y-%m-%d', '%d/%m/%Y']:
                try:
                    fecha_fin = datetime.strptime(fecha_fin_str, fmt).date()
                    break
                except ValueError:
                    continue
            
            if not fecha_inicio or not fecha_fin:
                self._send_message(chat_id, "❌ Formato de fecha no reconocido. Usa YYYY-MM-DD o DD/MM/YYYY")
                return
            
            # Parsear horas
            try:
                hora_inicio = datetime.strptime(hora_inicio_str, '%H:%M').time()
                hora_fin = datetime.strptime(hora_fin_str, '%H:%M').time()
            except ValueError:
                self._send_message(chat_id, "❌ Formato de hora no válido. Usa HH:MM")
                return
            
            # Cargar y filtrar datos
            stats = self._get_range_stats(fecha_inicio, fecha_fin, hora_inicio, hora_fin)
            
            if not stats or stats['total_trades'] == 0:
                self._send_message(
                    chat_id, 
                    f"❌ No hay datos entre {fecha_inicio.strftime('%d/%m')} y {fecha_fin.strftime('%d/%m')} en el horario {hora_inicio.strftime('%H:%M')}-{hora_fin.strftime('%H:%M')}"
                )
                return
            
            # Formatear mensaje de resultados
            msg = f"""
<b>📊 ESTADÍSTICAS POR SESIÓN</b>
<i>Rango: {fecha_inicio.strftime('%d/%m')} al {fecha_fin.strftime('%d/%m')}</i>
<i>Horario: {hora_inicio.strftime('%H:%M')} - {hora_fin.strftime('%H:%M')}</i>

<b>📈 Resumen</b>
• <b>Trades:</b> {stats['total_trades']}
• <b>Wins:</b> {stats['wins']}
• <b>Losses:</b> {stats['losses']}
• <b>Winrate:</b> {stats['winrate']:.1f}%
• <b>P&L Neto:</b> <code>{stats['pnl']:+.2f}</code>

<b>🔧 Detalles por Par</b>
{stats['pairs_detail']}

<b>💡 Duración Promedio:</b> {stats['avg_duration']:.0f}s

<i>Generado: {datetime.now().strftime('%H:%M:%S')}</i>
            """
            
            self._send_message(chat_id, msg)
            
        except Exception as e:
            print(f"⚠️ Error en _handle_range_stats: {e}")
            self._send_message(chat_id, f"❌ Error procesando rango: {str(e)}")

    def _get_range_stats(self, fecha_inicio, fecha_fin, hora_inicio, hora_fin):
        """Calcular estadísticas para un rango de fechas FILTRANDO por horario diario."""
        try:
            all_files = glob.glob(os.path.join(self.logs_dir, "trades_*.csv"))
            if not all_files:
                return None
            
            dfs = []
            for f in all_files:
                try:
                    df_temp = pd.read_csv(f)
                    if not df_temp.empty and not df_temp.isna().all().all():
                        dfs.append(df_temp)
                except Exception:
                    continue
            
            if not dfs:
                return None
            
            df = pd.concat(dfs, ignore_index=True)
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            
            # 1. Filtrar por rango de FECHAS (del día X al día Y)
            # Convertimos fechas a datetime para comparar con timestamp
            dt_inicio_dia = datetime.combine(fecha_inicio, datetime.min.time())
            dt_fin_dia = datetime.combine(fecha_fin, datetime.max.time())
            
            df = df[(df['timestamp'] >= dt_inicio_dia) & (df['timestamp'] <= dt_fin_dia)].copy()
            
            # 2. Filtrar por rango de HORAS (dentro de cada día)
            if hora_inicio <= hora_fin:
                # Caso normal (ej: 19:00 a 22:00)
                df = df[(df['timestamp'].dt.time >= hora_inicio) & (df['timestamp'].dt.time <= hora_fin)]
            else:
                # Caso cruza medianoche (ej: 22:00 a 02:00)
                # Selecciona trades >= 22:00 OR <= 02:00
                df = df[(df['timestamp'].dt.time >= hora_inicio) | (df['timestamp'].dt.time <= hora_fin)]
            
            # Filtrar completados
            df = df[df['result'].isin(['WIN', 'LOSS'])]
            
             # Filtrar trades de DEMO
            if 'trade_id' in df.columns:
                df = df[~df['trade_id'].astype(str).str.startswith('DEMO')]
            
            if len(df) == 0:
                return None
            
            # Calcular estadísticas
            stats = {
                'total_trades': len(df),
                'wins': len(df[df['result'] == 'WIN']),
                'losses': len(df[df['result'] == 'LOSS']),
                'winrate': (len(df[df['result'] == 'WIN']) / len(df)) * 100,
                'pnl': df['profit_loss'].sum() if 'profit_loss' in df.columns else 0.0,
                'pairs_detail': '',
                'avg_duration': 0
            }
            
            # P&L por par
            if 'pair' in df.columns:
                pair_stats = df.groupby('pair').agg({
                    'result': lambda x: (x == 'WIN').sum(),
                    'profit_loss': 'sum' if 'profit_loss' in df.columns else lambda x: 0
                }).rename(columns={'result': 'wins'})
                
                pairs_detail = []
                for pair, row in pair_stats.iterrows():
                    wins = row['wins']
                    total_in_pair = len(df[df['pair'] == pair])
                    wr = (wins / total_in_pair) * 100 if total_in_pair > 0 else 0
                    pnl = row['profit_loss'] if 'profit_loss' in df.columns else 0
                    pairs_detail.append(f"  • <b>{pair}:</b> {total_in_pair} op | {wr:.1f}% WR | {pnl:+.2f} P&L")
                
                stats['pairs_detail'] = '\n'.join(pairs_detail)
            
            # Duración promedio
            if 'duration' in df.columns:
                stats['avg_duration'] = df['duration'].astype(float).mean()
            
            return stats
            
        except Exception as e:
            print(f"⚠️ Error en _get_range_stats: {e}")
            return None

    def _handle_range_detailed(self, chat_id, args):
        """Manejar comando /range_detailed para ver detalles de cada operación."""
        self._send_message(chat_id, "⏳ Generando informe detallado de operaciones...")
        
        try:
            # Parsear argumentos (mismo formato que /range_stats)
            parts = args.split()
            
            if len(parts) < 4:
                self._send_message(
                    chat_id, 
                    """❌ Formato incorrecto.
                    
<b>Uso:</b> /range_detailed FECHA_INICIO HORA_INICIO FECHA_FIN HORA_FIN

<b>Ejemplo:</b> /range_detailed 2025-12-01 09:00 2025-12-02 18:00
                    """
                )
                return
            
            fecha_inicio_str = parts[0]
            hora_inicio_str = parts[1]
            fecha_fin_str = parts[2]
            hora_fin_str = parts[3]
            
            # Parsear fechas
            fecha_inicio = None
            fecha_fin = None
            
            for fmt in ['%Y-%m-%d', '%d/%m/%Y']:
                try:
                    fecha_inicio = datetime.strptime(fecha_inicio_str, fmt).date()
                    break
                except ValueError:
                    continue
            
            for fmt in ['%Y-%m-%d', '%d/%m/%Y']:
                try:
                    fecha_fin = datetime.strptime(fecha_fin_str, fmt).date()
                    break
                except ValueError:
                    continue
            
            if not fecha_inicio or not fecha_fin:
                self._send_message(chat_id, "❌ Formato de fecha no reconocido.")
                return
            
            # Parsear horas
            try:
                hora_inicio = datetime.strptime(hora_inicio_str, '%H:%M').time()
                hora_fin = datetime.strptime(hora_fin_str, '%H:%M').time()
            except ValueError:
                self._send_message(chat_id, "❌ Formato de hora no válido.")
                return
            
            # Cargar datos detallados
            detailed_list = self._get_detailed_trades(fecha_inicio, fecha_fin, hora_inicio, hora_fin)
            
            if not detailed_list or len(detailed_list) == 0:
                self._send_message(
                    chat_id, 
                    f"❌ No hay datos entre {fecha_inicio.strftime('%d/%m')} y {fecha_fin.strftime('%d/%m')} en el horario {hora_inicio.strftime('%H:%M')}-{hora_fin.strftime('%H:%M')}"
                )
                return
            
            # Dividir en múltiples mensajes si es muy largo
            self._send_detailed_report(chat_id, detailed_list, fecha_inicio, fecha_fin, hora_inicio, hora_fin)
            
        except Exception as e:
            print(f"⚠️ Error en _handle_range_detailed: {e}")
            self._send_message(chat_id, f"❌ Error: {str(e)}")

    def _get_detailed_trades(self, fecha_inicio, fecha_fin, hora_inicio, hora_fin):
        """Obtener lista detallada de trades FILTRANDO por horario diario."""
        try:
            all_files = glob.glob(os.path.join(self.logs_dir, "trades_*.csv"))
            if not all_files:
                return None
            
            dfs = []
            for f in all_files:
                try:
                    df_temp = pd.read_csv(f)
                    if not df_temp.empty and not df_temp.isna().all().all():
                        dfs.append(df_temp)
                except Exception:
                    continue
            
            if not dfs:
                return None
            
            df = pd.concat(dfs, ignore_index=True)
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            
            # 1. Filtrar por rango de FECHAS
            dt_inicio_dia = datetime.combine(fecha_inicio, datetime.min.time())
            dt_fin_dia = datetime.combine(fecha_fin, datetime.max.time())
            
            df = df[(df['timestamp'] >= dt_inicio_dia) & (df['timestamp'] <= dt_fin_dia)].copy()
            
            # 2. Filtrar por rango de HORAS (dentro de cada día)
            if hora_inicio <= hora_fin:
                # Caso normal (ej: 19:00 a 22:00)
                df = df[(df['timestamp'].dt.time >= hora_inicio) & (df['timestamp'].dt.time <= hora_fin)]
            else:
                # Caso cruza medianoche (ej: 22:00 a 02:00)
                # Selecciona trades >= 22:00 OR <= 02:00
                df = df[(df['timestamp'].dt.time >= hora_inicio) | (df['timestamp'].dt.time <= hora_fin)]
            
            # Filtrar completados y NO DEMO
            df = df[df['result'].isin(['WIN', 'LOSS'])]
            if 'trade_id' in df.columns:
                df = df[~df['trade_id'].astype(str).str.startswith('DEMO')]
            
            if len(df) == 0:
                return None
            
            # Ordenar por timestamp
            df = df.sort_values('timestamp')
            
            # Convertir a lista de diccionarios
            trades_list = []
            for idx, row in df.iterrows():
                trade = {
                    'timestamp': row['timestamp'],
                    'pair': row.get('pair', 'N/A'),
                    'decision': row.get('decision', 'N/A'),
                    'result': row.get('result', 'N/A'),
                    'duration': row.get('duration', 0),
                    'profit_loss': row.get('profit_loss', 0),
                    'amount': row.get('amount', 0)
                }
                trades_list.append(trade)
            
            return trades_list
            
        except Exception as e:
            print(f"⚠️ Error en _get_detailed_trades: {e}")
            return None

    def _send_detailed_report(self, chat_id, trades_list, fecha_inicio, fecha_fin, hora_inicio, hora_fin):
        """Enviar informe detallado agrupado por pares."""
        try:
            from collections import defaultdict
            
            # Encabezado
            header = f"""<b>📋 INFORME DETALLADO POR PARES</b>
<i>Rango: {fecha_inicio.strftime('%d/%m')} al {fecha_fin.strftime('%d/%m')}</i>
<i>Horario: {hora_inicio.strftime('%H:%M')} - {hora_fin.strftime('%H:%M')}</i>

<b>Total de trades: {len(trades_list)}</b>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
            
            # Agrupar por par
            trades_by_pair = defaultdict(list)
            for trade in trades_list:
                trades_by_pair[trade['pair']].append(trade)
            
            # Construir mensaje agrupado por pares
            full_message = header
            
            for pair in sorted(trades_by_pair.keys()):
                pair_trades = trades_by_pair[pair]
                
                # Encabezado del par
                pair_wins = len([t for t in pair_trades if t['result'] == 'WIN'])
                pair_losses = len([t for t in pair_trades if t['result'] == 'LOSS'])
                pair_winrate = (pair_wins / len(pair_trades) * 100) if len(pair_trades) > 0 else 0
                pair_pnl = sum([t['profit_loss'] for t in pair_trades])
                
                pair_header = f"\n<b>{pair}</b> ({len(pair_trades)} ops | {pair_winrate:.1f}% WR | {pair_pnl:+.2f})\n"
                
                # Agregar operaciones del par
                pair_content = ""
                for trade in pair_trades:
                    ts = trade['timestamp']
                    emoji = "✅" if trade['result'] == 'WIN' else "❌"
                    duration_str = f"{int(trade['duration'])}s" if trade['duration'] > 0 else "N/A"
                    pnl_str = f"{trade['profit_loss']:+.2f}"
                    
                    trade_line = f"{emoji} {ts.strftime('%H:%M:%S')} {trade['decision']} | {duration_str} | {pnl_str}\n"
                    pair_content += trade_line
                
                # Si agregar este par haría el mensaje muy largo, enviar lo actual
                if len(full_message) + len(pair_header) + len(pair_content) > 3800 and len(full_message) > len(header):
                    # Enviar mensaje actual
                    self._send_message(chat_id, full_message)
                    # Comenzar nuevo mensaje con este par
                    full_message = header + pair_header + pair_content
                else:
                    full_message += pair_header + pair_content
            
            # Resumen final
            wins = len([t for t in trades_list if t['result'] == 'WIN'])
            losses = len([t for t in trades_list if t['result'] == 'LOSS'])
            total_pnl = sum([t['profit_loss'] for t in trades_list])
            winrate = (wins / len(trades_list) * 100) if len(trades_list) > 0 else 0
            
            footer = f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
<b>📊 RESUMEN FINAL</b>
✅ Wins: {wins}
❌ Losses: {losses}
📈 Winrate: {winrate:.1f}%
💰 P&L Total: {total_pnl:+.2f}
            """
            
            full_message += footer
            
            # Enviar mensaje final
            self._send_message(chat_id, full_message)
            
        except Exception as e:
            print(f"⚠️ Error en _send_detailed_report: {e}")
            self._send_message(chat_id, f"❌ Error enviando reporte: {e}")

    def _send_detailed_report_chunked(self, chat_id, trades_list, dt_inicio, dt_fin, header, footer):
        """Enviar informe dividido por pares si es muy largo."""
        try:
            # Agrupar por par
            from collections import defaultdict
            trades_by_pair = defaultdict(list)
            
            for trade in trades_list:
                trades_by_pair[trade['pair']].append(trade)
            
            # Primer mensaje: encabezado y primer par
            message = header
            pairs_processed = 0
            
            for pair, pair_trades in trades_by_pair.items():
                pair_section = f"\n<b>{pair}</b>\n"
                
                for trade in pair_trades:
                    ts = trade['timestamp']
                    emoji = "✅" if trade['result'] == 'WIN' else "❌"
                    duration_str = f"{int(trade['duration'])}s" if trade['duration'] > 0 else "N/A"
                    pnl_str = f"{trade['profit_loss']:+.2f}"
                    trade_line = f"{emoji} {ts.strftime('%H:%M:%S')} {trade['decision']} | {duration_str} | {pnl_str}\n"
                    
                    pair_section += trade_line
                
                # Si agregar este par haría el mensaje muy largo, enviar lo actual
                if len(message) + len(pair_section) > 3800 and pairs_processed > 0:
                    self._send_message(chat_id, message)
                    message = pair_section
                else:
                    message += pair_section
                
                pairs_processed += 1
            
            # Enviar último mensaje con footer
            message += footer
            self._send_message(chat_id, message)
            
        except Exception as e:
            print(f"⚠️ Error en _send_detailed_report_chunked: {e}")

# Instancia global (se inicializará desde el bot)
telegram_listener = None

