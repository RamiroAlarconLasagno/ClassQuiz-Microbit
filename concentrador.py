# concentrador.py - Micro:bit Hub para descubrimiento de dispositivos

from microbit import *
import radio

# Configuracion radio
radio.config(channel=7, power=6, length=64, queue=10)
radio.on()

# Lista de dispositivos registrados
dispositivos_registrados = set()

def enviar_por_usb(mensaje):
    """Envia mensaje por puerto serie USB"""
    print(mensaje)
    uart.write(mensaje + "\n")

def descubrimiento():
    display.show(Image.HEART)
    dispositivos_registrados.clear()
    
    enviar_por_usb("INICIO_DESCUBRIMIENTO")
    
    # 6 rondas de REPORT en 12 segundos
    for ronda in range(6):
        radio.send("REPORT")
        enviar_por_usb("REPORT_ENVIADO:ronda_" + str(ronda+1))
        
        # Procesar mensajes durante 2 segundos
        tiempo_inicio = running_time()
        while running_time() - tiempo_inicio < 2000:
            mensaje = radio.receive()
            if mensaje:
                procesar_mensaje_radio(mensaje)
            sleep(10)  # Pequeña pausa
    
    enviar_por_usb("FIN_DESCUBRIMIENTO:total_" + str(len(dispositivos_registrados)))
    display.show(len(dispositivos_registrados))
    sleep(2000)
    display.clear()

def procesar_mensaje_radio(msg):
    """Procesa mensajes recibidos por radio"""
    if msg.startswith("ID:"):
        device_id = msg[3:]  # Extrae ID despues de "ID:"
        
        if device_id not in dispositivos_registrados:
            dispositivos_registrados.add(device_id)
            enviar_por_usb("NUEVO_DISPOSITIVO:" + device_id)
            # Envia ACK para confirmar registro
            radio.send("ACK:" + device_id)
            display.scroll(len(dispositivos_registrados), delay=60)

# Indicador de inicio
display.show(Image.HAPPY)
sleep(1000)
display.clear()

# Loop principal
while True:
    # Boton A: Inicia descubrimiento
    if button_a.was_pressed():
        descubrimiento()
    
    # Recibir mensajes radio
    mensaje = radio.receive()
    if mensaje:
        procesar_mensaje_radio(mensaje)
    
    sleep(50)  # Pequeña pausa para no saturar CPU