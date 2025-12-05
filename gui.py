import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
from PIL import Image, ImageTk
import threading
import asyncio
import sys
import os
import subprocess
import matplotlib
import seaborn

# Importar ambos bots
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'bots'))

# Configuración de colores (Tema Dark/Demon)
COLOR_BG = "#1a0b0b"       # Fondo oscuro rojizo
COLOR_FG = "#ff4d4d"       # Texto rojo brillante
COLOR_ENTRY_BG = "#2d1f1f" # Fondo de inputs
COLOR_BTN_BG = "#800000"   # Botón rojo oscuro
COLOR_BTN_FG = "#ffffff"   # Texto botón blanco
COLOR_LOG_BG = "#000000"   # Fondo log negro
COLOR_LOG_FG = "#00ff00"   # Texto log verde terminal

class TradingBotGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("👹 DEMON TRADING BOT 👹")
        self.root.geometry("1000x700")
        self.root.configure(bg=COLOR_BG)

        # Variables de control
        self.bot_thread = None
        self.stop_event = threading.Event()
        self.is_running = False

        # Cargar imagen de fondo
        self.load_background()

        # Frame principal (transparente visualmente)
        main_frame = tk.Frame(root, bg=COLOR_BG)
        main_frame.place(relx=0.5, rely=0.5, anchor="center", relwidth=0.9, relheight=0.9)

        # --- Título ---
        title_lbl = tk.Label(main_frame, text="DEMON TRADING SYSTEM", font=("Impact", 24), bg=COLOR_BG, fg=COLOR_FG)
        title_lbl.pack(pady=10)

        # --- Inputs ---
        input_frame = tk.Frame(main_frame, bg=COLOR_BG)
        input_frame.pack(pady=10, fill="x")

        self.ssid_var = tk.StringVar()
        self.token_var = tk.StringVar()
        self.chat_id_var = tk.StringVar()

        # Cargar valores guardados (simple archivo de texto)
        self.load_config()

        self.create_input(input_frame, "PocketOption SSID:", self.ssid_var)
        self.create_input(input_frame, "Telegram Token:", self.token_var)
        self.create_input(input_frame, "Telegram Chat ID:", self.chat_id_var)

        # --- Botones ---
        btn_frame = tk.Frame(main_frame, bg=COLOR_BG)
        btn_frame.pack(pady=20)

        self.start_btn = tk.Button(btn_frame, text="🔥 INICIAR BOTS 🔥", font=("Arial", 14, "bold"),
                                   bg=COLOR_BTN_BG, fg=COLOR_BTN_FG, activebackground="#ff0000",
                                   command=self.start_bot, width=20)
        self.start_btn.pack(side="left", padx=10)

        self.stop_btn = tk.Button(btn_frame, text="🛑 DETENER", font=("Arial", 14, "bold"),
                                  bg="#333333", fg="white", state="disabled",
                                  command=self.stop_bot, width=15)
        self.stop_btn.pack(side="left", padx=10)

        # --- Log Area ---
        log_frame = tk.Frame(main_frame, bg=COLOR_BG)
        log_frame.pack(fill="both", expand=True)

        log_lbl = tk.Label(log_frame, text="SYSTEM LOGS:", font=("Consolas", 10), bg=COLOR_BG, fg="#aaaaaa")
        log_lbl.pack(anchor="w")

        self.log_area = scrolledtext.ScrolledText(log_frame, bg=COLOR_LOG_BG, fg=COLOR_LOG_FG,
                                                  font=("Consolas", 9), state="disabled")
        self.log_area.pack(fill="both", expand=True)

    def load_background(self):
        try:
            # Buscar la imagen subida por el usuario
            image_path = "C:/Users/Guille/.gemini/antigravity/brain/daa40e73-8a30-4c9e-89ac-ae53da07de3f/uploaded_image_1764215039988.jpg"
            if not os.path.exists(image_path):
                # Fallback si no encuentra la ruta exacta, buscar en directorio actual
                image_path = "uploaded_image_1764215039988.jpg"
            
            if os.path.exists(image_path):
                pil_image = Image.open(image_path)
                # Redimensionar para ajustar a la ventana (opcional)
                pil_image = pil_image.resize((1000, 700), Image.Resampling.LANCZOS)
                self.bg_image = ImageTk.PhotoImage(pil_image)
                
                bg_label = tk.Label(self.root, image=self.bg_image)
                bg_label.place(x=0, y=0, relwidth=1, relheight=1)
            else:
                print("Imagen de fondo no encontrada.")
        except Exception as e:
            print(f"Error cargando imagen: {e}")

    def create_input(self, parent, label_text, variable):
        frame = tk.Frame(parent, bg=COLOR_BG)
        frame.pack(fill="x", pady=5)
        
        lbl = tk.Label(frame, text=label_text, width=20, anchor="e", bg=COLOR_BG, fg="#ffffff", font=("Arial", 10, "bold"))
        lbl.pack(side="left", padx=5)
        
        entry = tk.Entry(frame, textvariable=variable, bg=COLOR_ENTRY_BG, fg="white", insertbackground="white", font=("Consolas", 10))
        entry.pack(side="left", fill="x", expand=True, padx=5)

    def log_message(self, message):
        self.log_area.config(state="normal")
        self.log_area.insert("end", message + "\n")
        self.log_area.see("end")
        self.log_area.config(state="disabled")

    def start_bot(self):
        ssid = self.ssid_var.get().strip()
        token = self.token_var.get().strip()
        chat_id = self.chat_id_var.get().strip()

        if not ssid:
            messagebox.showerror("Error", "El SSID es obligatorio")
            return

        self.save_config()
        self.stop_event.clear()
        self.is_running = True
        
        # UI Updates
        self.start_btn.config(state="disabled", bg="#333333")
        self.stop_btn.config(state="normal", bg="#ff0000")
        self.log_message("🔥 INICIANDO SISTEMA...")
        self.log_message("🤖 Bot EMA Pullback: Activado")
        self.log_message("🎯 Bot Round Levels: Activado")
        self.log_message(f"🐍 Python: {sys.executable}")

        # Run in thread
        self.bot_thread = threading.Thread(target=self.run_async_bots, args=(ssid,))
        self.bot_thread.daemon = True
        self.bot_thread.start()

    def stop_bot(self):
        if self.is_running:
            self.log_message("🛑 ENVIANDO SEÑAL DE DETENCIÓN...")
            self.stop_event.set()
            self.is_running = False
            self.start_btn.config(state="normal", bg=COLOR_BTN_BG)
            self.stop_btn.config(state="disabled", bg="#333333")

    def run_async_bots(self, ssid):
        """Ejecuta ambos bots en paralelo"""
        try:
            # Guardar SSID en variable de entorno para que los bots lo usen
            os.environ["POCKETOPTION_SSID"] = ssid
            
            # Ejecutar el loop de asyncio con ambos bots
            asyncio.run(self.run_both_bots())
        except Exception as e:
            self.safe_log(f"❌ ERROR FATAL EN BOTS: {e}")
        finally:
            self.safe_log("ℹ️ Bots detenidos.")
            # Reset UI safely
            self.root.after(0, lambda: self.start_btn.config(state="normal", bg=COLOR_BTN_BG))
            self.root.after(0, lambda: self.stop_btn.config(state="disabled", bg="#333333"))

    async def run_both_bots(self):
        """Ejecuta ambos bots simultáneamente"""
        # Importar las funciones main de cada bot
        from bots.bot_ema_pullback import main as ema_main
        from bots.bot_round_levels import main as round_main
        
        # Crear tareas para ambos bots
        task1 = asyncio.create_task(self.run_bot_with_logging(ema_main(), "EMA"))
        task2 = asyncio.create_task(self.run_bot_with_logging(round_main(), "ROUND"))
        
        # Esperar a que ambos terminen (o hasta que se detenga)
        await asyncio.gather(task1, task2, return_exceptions=True)

    async def run_bot_with_logging(self, bot_coro, bot_name):
        """Wrapper para agregar logging específico por bot"""
        try:
            self.safe_log(f"[{bot_name}] Iniciado")
            await bot_coro
        except Exception as e:
            self.safe_log(f"[{bot_name}] Error: {e}")
        finally:
            self.safe_log(f"[{bot_name}] Detenido")

    def safe_log(self, msg):
        # Thread-safe logging update
        self.root.after(0, lambda: self.log_message(msg))

    def load_config(self):
        if os.path.exists("bot_config.txt"):
            try:
                with open("bot_config.txt", "r") as f:
                    lines = f.readlines()
                    if len(lines) >= 3:
                        self.ssid_var.set(lines[0].strip())
                        self.token_var.set(lines[1].strip())
                        self.chat_id_var.set(lines[2].strip())
            except:
                pass

    def save_config(self):
        try:
            with open("bot_config.txt", "w") as f:
                f.write(f"{self.ssid_var.get()}\n")
                f.write(f"{self.token_var.get()}\n")
                f.write(f"{self.chat_id_var.get()}\n")
        except:
            pass

if __name__ == "__main__":
    root = tk.Tk()
    app = TradingBotGUI(root)
    root.mainloop()
