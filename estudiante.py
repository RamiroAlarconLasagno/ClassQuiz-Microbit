# estudiante.py - Micro:bit Estudiante para sistema de quiz

from microbit import *
import machine
import radio
from random import randint

# Configuracion radio (mismo canal que concentrador)
radio.config(channel=7, power=6, length=64, queue=10)
radio.on()

# Obtener ID unico del dispositivo (conversion manual bytes a hex)
mi_id = ''.join(['{:02x}'.format(b) for b in machine.unique_id()])

# Estado de registro
ack_recibido = False

def mostrar_estado():
    """Muestra estado de registro en display"""
    if ack_recibido:
        display.show(Image.YES)
    else:
        display.show(Image.NO)
    sleep(500)
    display.clear()

def procesar_mensaje(msg):
    """Procesa mensajes recibidos por radio"""
    global ack_recibido
    
    if msg == "REPORT":
        # Solo responde si no ha recibido ACK
        if not ack_recibido:
            # Espera tiempo aleatorio para evitar colisiones
            delay_ms = randint(0, 2000)
            sleep(delay_ms)
            
            # Envia ID
            radio.send("ID:" + mi_id)
            display.show(Image.ARROW_E)  # Indicador de transmision
            sleep(200)
            display.clear()
    
    elif msg.startswith("ACK:"):
        # Verifica si el ACK es para este dispositivo
        ack_id = msg[4:]
        if ack_id == mi_id:
            ack_recibido = True
            display.show(Image.HAPPY)
            sleep(1000)
            display.clear()
    
    else:
        # Cualquier otro mensaje resetea el ACK
        # (preparacion para proximas funcionalidades)
        if msg not in ["REPORT", ""] and not msg.startswith("ACK:"):
            ack_recibido = False

# Indicador de inicio - muestra fragmento del ID
display.scroll(mi_id[-4:], delay=60)
sleep(500)
display.clear()

# Loop principal
while True:
    # Boton A: Muestra estado de registro
    if button_a.was_pressed():
        mostrar_estado()
    
    # Boton B: Muestra ultimos 6 digitos del ID
    if button_b.was_pressed():
        display.scroll(mi_id[-6:], delay=80)
    
    # Recibir mensajes radio
    mensaje = radio.receive()
    if mensaje:
        procesar_mensaje(mensaje)
    
    sleep(50)