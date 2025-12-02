# main.py - Punto de entrada principal con GUI Tkinter
# Sistema Proxy Microbit-ClassQuiz

import tkinter as tk
from tkinter import ttk, messagebox
import threading
import webbrowser
import time
import sys

# Importar módulos del proyecto
import flask_server
import serial_manager
import config

class MicrobitProxyGUI:
    """Ventana principal de la aplicación con interfaz Tkinter"""
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Proxy Microbit ClassQuiz v1.0")
        self.root.geometry("450x350")
        self.root.resizable(False, False)
        
        # Variables de estado
        self.puerto_seleccionado = tk.StringVar()
        self.estado_conexion = tk.StringVar(value="🔴 Desconectado")
        
        # Inicializar Flask en thread separado
        self.flask_thread = None
        
        # Crear interface
        self.crear_widgets()
        
        # Iniciar Flask automáticamente
        self.iniciar_flask()
        
    def crear_widgets(self):
        """Crea todos los widgets de la ventana"""
        
        # Frame principal
        main_frame = ttk.Frame(self.root, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Título
        titulo = tk.Label(
            main_frame,
            text="📟 Proxy Microbit ClassQuiz",
            font=("Arial", 16, "bold")
        )
        titulo.pack(pady=(0, 20))
        
        # Sección puerto serie
        puerto_frame = ttk.LabelFrame(main_frame, text="Conexión USB", padding="10")
        puerto_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Label puerto
        ttk.Label(puerto_frame, text="Puerto Serie:").grid(row=0, column=0, sticky=tk.W, pady=5)
        
        # Combobox selector de puerto
        self.puerto_combo = ttk.Combobox(
            puerto_frame,
            textvariable=self.puerto_seleccionado,
            state="readonly",
            width=20
        )
        self.puerto_combo.grid(row=0, column=1, padx=(10, 0), pady=5)
        
        # Botones puerto
        btn_frame = ttk.Frame(puerto_frame)
        btn_frame.grid(row=1, column=0, columnspan=2, pady=(10, 0))
        
        self.btn_detectar = ttk.Button(
            btn_frame,
            text="🔍 Detectar Puertos",
            command=self.detectar_puertos
        )
        self.btn_detectar.pack(side=tk.LEFT, padx=5)
        
        self.btn_conectar = ttk.Button(
            btn_frame,
            text="🔌 Conectar Puerto",
            command=self.conectar_puerto
        )
        self.btn_conectar.pack(side=tk.LEFT, padx=5)
        
        # Estado de conexión
        estado_frame = ttk.Frame(main_frame)
        estado_frame.pack(fill=tk.X, pady=(10, 10))
        
        ttk.Label(estado_frame, text="Estado:").pack(side=tk.LEFT)
        self.estado_label = tk.Label(
            estado_frame,
            textvariable=self.estado_conexion,
            font=("Arial", 12, "bold"),
            fg="red"
        )
        self.estado_label.pack(side=tk.LEFT, padx=(10, 0))
        
        # Botón abrir web
        self.btn_web = ttk.Button(
            main_frame,
            text="🌐 Abrir Interface Web",
            command=self.abrir_interface_web,
            state=tk.NORMAL  # Habilitado desde el inicio
        )
        self.btn_web.pack(pady=20)
        
        # Info Flask
        info_label = tk.Label(
            main_frame,
            text=f"Servidor local: http://localhost:{config.FLASK_PORT}",
            font=("Arial", 9),
            fg="gray"
        )
        info_label.pack()
        
        # Detectar puertos al inicio
        self.root.after(500, self.detectar_puertos)
        
    def iniciar_flask(self):
        """Inicia el servidor Flask en un thread separado"""
        if self.flask_thread is None or not self.flask_thread.is_alive():
            self.flask_thread = threading.Thread(
                target=flask_server.run_server,
                daemon=True
            )
            self.flask_thread.start()
            print("[Main] Servidor Flask iniciado")
    
    def detectar_puertos(self):
        """Detecta y actualiza la lista de puertos COM disponibles"""
        try:
            puertos = serial_manager.detectar_puertos()
            
            if puertos:
                puertos_list = [p['port'] for p in puertos]
                self.puerto_combo['values'] = puertos_list
                
                # Seleccionar primer puerto si no hay selección
                if not self.puerto_seleccionado.get() and puertos_list:
                    self.puerto_combo.current(0)
                
                messagebox.showinfo(
                    "Puertos Detectados",
                    f"Se encontraron {len(puertos)} puerto(s):\n" + 
                    "\n".join([f"• {p['port']}: {p['description']}" for p in puertos])
                )
            else:
                self.puerto_combo['values'] = []
                messagebox.showwarning(
                    "Sin Puertos",
                    "No se detectaron puertos serie.\n\n" +
                    "Verifica que el micro:bit esté conectado."
                )
                
        except Exception as e:
            messagebox.showerror("Error", f"Error detectando puertos:\n{str(e)}")
    
    def conectar_puerto(self):
        """Conecta al puerto serie seleccionado"""
        puerto = self.puerto_seleccionado.get()
        
        if not puerto:
            messagebox.showwarning(
                "Puerto No Seleccionado",
                "Por favor selecciona un puerto de la lista."
            )
            return
        
        try:
            # Intentar conexión
            if serial_manager.conectar(puerto):
                self.estado_conexion.set("🟢 Conectado")
                self.estado_label.config(fg="green")
                
                # Actualizar estado en Flask
                flask_server.estado['puerto_conectado'] = True
                flask_server.estado['puerto_nombre'] = puerto
                
                # Iniciar thread de lectura USB
                threading.Thread(
                    target=self.leer_usb_loop,
                    daemon=True
                ).start()
                
                messagebox.showinfo(
                    "Conexión Exitosa",
                    f"Conectado correctamente a {puerto}"
                )
            else:
                raise Exception("No se pudo abrir el puerto")
                
        except Exception as e:
            self.estado_conexion.set("❌ Error")
            self.estado_label.config(fg="red")
            messagebox.showerror(
                "Error de Conexión",
                f"No se pudo conectar a {puerto}:\n\n{str(e)}"
            )
    
    def leer_usb_loop(self):
        """Loop continuo de lectura del puerto USB"""
        print("[Main] Thread de lectura USB iniciado")
        
        while serial_manager.esta_conectado():
            try:
                mensaje = serial_manager.leer()
                
                if mensaje:
                    # Enviar mensaje a Flask para procesamiento
                    flask_server.procesar_mensaje_usb(mensaje)
                
                time.sleep(config.USB_READ_INTERVAL)
                
            except Exception as e:
                print(f"[Main] Error en lectura USB: {e}")
                time.sleep(1)
        
        print("[Main] Thread de lectura USB finalizado")
    
    def abrir_interface_web(self):
        """Abre el navegador en la interface web"""
        url = f"http://localhost:{config.FLASK_PORT}"
        
        try:
            webbrowser.open(url)
        except Exception as e:
            messagebox.showerror(
                "Error",
                f"No se pudo abrir el navegador:\n{str(e)}\n\n" +
                f"Accede manualmente a: {url}"
            )
    
    def on_closing(self):
        """Maneja el cierre de la aplicación"""
        if messagebox.askokcancel("Salir", "¿Deseas cerrar la aplicación?"):
            # Desconectar puerto
            serial_manager.desconectar()
            
            # Cerrar ventana
            self.root.destroy()
            
            # Forzar salida del programa
            sys.exit(0)
    
    def run(self):
        """Inicia el loop principal de Tkinter"""
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.root.mainloop()


def main():
    """Función principal"""
    print("=" * 60)
    print("PROXY MICROBIT-CLASSQUIZ v1.0")
    print("Fundación Dr. Manuel Sadosky - Proyecto CDIA")
    print("=" * 60)
    print()
    print("Iniciando aplicación...")
    print()
    
    try:
        app = MicrobitProxyGUI()
        app.run()
    except KeyboardInterrupt:
        print("\n[Main] Interrupción por teclado - Saliendo...")
        sys.exit(0)
    except Exception as e:
        print(f"\n[Main] Error fatal: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()