# concentrador.py - Micro:bit Concentrador con polling secuencial corregido

from microbit import *
import radio

# === CONFIGURACION RADIO ===
radio.config(channel=7, power=6, length=64, queue=10)
radio.on()

# === CONFIGURACION UART ===
uart.init(baudrate=115200)

# === ALMACENAMIENTO ===
dispositivos_registrados = set()
polling_activo = False
CONFIG_FILE = 'devices.cfg'


def enviar_por_usb(mensaje):
    """Envia mensaje JSON por puerto serie USB"""
    print(mensaje)
    uart.write(mensaje + "\n")


def cargar_dispositivos():
    """Carga lista de dispositivos desde archivo"""
    global dispositivos_registrados
    try:
        with open(CONFIG_FILE, 'r') as f:
            dispositivos_registrados = set(eval(f.read()))
        print("Dispositivos cargados:", len(dispositivos_registrados))
    except:
        dispositivos_registrados = set()


def guardar_dispositivos():
    """Guarda lista de dispositivos en archivo"""
    try:
        with open(CONFIG_FILE, 'w') as f:
            f.write(repr(list(dispositivos_registrados)))
    except Exception as e:
        print("Error guardando:", e)


def descubrimiento():
    """Proceso de descubrimiento de dispositivos"""
    display.show(Image.HEART)
    dispositivos_registrados.clear()
    
    enviar_por_usb('{"type":"discovery_start"}')
    
    # 6 rondas de REPORT en 12 segundos
    for ronda in range(6):
        radio.send("REPORT")
        enviar_por_usb('{{"type":"debug","msg":"REPORT_ENVIADO:ronda_{}"}}'.format(ronda + 1))
        
        # Procesar respuestas durante 2 segundos
        tiempo_inicio = running_time()
        while running_time() - tiempo_inicio < 2000:
            mensaje = radio.receive()
            if mensaje and mensaje.startswith("ID:"):
                procesar_id_dispositivo(mensaje)
            sleep(10)
    
    # Enviar lista completa por USB (JSON válido con comillas dobles)
    lista_ids = list(dispositivos_registrados)
    json_devices = '{"type":"device_list","devices":['
    for i, dev_id in enumerate(lista_ids):
        json_devices += '"{}"'.format(dev_id)
        if i < len(lista_ids) - 1:
            json_devices += ','
    json_devices += ']}'
    enviar_por_usb(json_devices)
    
    # Guardar en archivo
    guardar_dispositivos()
    
    # Enviar mensaje de fin
    enviar_por_usb('{{"type":"discovery_end","total":{}}}'.format(len(dispositivos_registrados)))
    
    display.show(len(dispositivos_registrados))
    sleep(2000)
    display.clear()


def procesar_id_dispositivo(mensaje):
    """Procesa mensaje ID de estudiante"""
    device_id = mensaje[3:]
    
    if device_id not in dispositivos_registrados:
        dispositivos_registrados.add(device_id)
        radio.send("ACK:" + device_id)
        
        # Notificar por USB (JSON corregido)
        enviar_por_usb('{{"type":"new_device","device_id":"{}"}}'.format(device_id))
        display.scroll(len(dispositivos_registrados), delay=60)


def broadcast_qparams(tipo_pregunta, num_opciones):
    """Envia parametros de pregunta por radio"""
    mensaje = "QPARAMS:{}:{}".format(tipo_pregunta, num_opciones)
    
    # Enviar por radio
    radio.send(mensaje)
    
    # Notificar al proxy
    enviar_por_usb('{{"type":"qparams_sent","q_type":"{}","num_options":{}}}'.format(
        tipo_pregunta, num_opciones
    ))
    
    # Dar tiempo para procesamiento
    sleep(500)
    
    display.show(Image.ARROW_E)
    sleep(200)
    display.clear()


def hacer_polling():
    """Polling secuencial de todos los dispositivos"""
    global polling_activo
    polling_activo = True
    
    display.show(Image.ASLEEP)
    
    lista_dispositivos = list(dispositivos_registrados)
    
    for idx, device_id in enumerate(lista_dispositivos):
        # Mostrar progreso
        display.show(str(idx + 1))
        
        respuesta_recibida = None
        intentos = 0
        
        # Hasta 2 intentos
        while intentos < 2 and respuesta_recibida is None:
            radio.send("POLL:" + device_id)
            
            # Esperar respuesta 500ms
            tiempo_inicio = running_time()
            while running_time() - tiempo_inicio < 500:
                mensaje = radio.receive()
                if mensaje and mensaje.startswith("ANSWER:"):
                    partes = mensaje.split(':', 2)
                    if len(partes) >= 2 and partes[1] == device_id:
                        respuesta_recibida = partes[2] if len(partes) == 3 else ""
                        break
                sleep(10)
            
            intentos += 1
        
        # Si no hubo respuesta, enviar vacio
        if respuesta_recibida is None:
            respuesta_recibida = ""
        
        # Enviar por USB (JSON válido)
        json_str = '{{"type":"answer","device_id":"{}","answer":"{}"}}'.format(
            device_id, respuesta_recibida
        )
        enviar_por_usb(json_str)
    
    # Polling completo
    enviar_por_usb('{"type":"polling_complete"}')
    
    polling_activo = False
    
    display.show(Image.HAPPY)
    sleep(1000)
    display.clear()


def verificar_estado():
    """Verifica estado de dispositivos con PING"""
    display.show(Image.GHOST)
    
    for device_id in list(dispositivos_registrados):
        radio.send("PING:" + device_id)
        
        # Esperar PONG 1 segundo
        tiempo_inicio = running_time()
        recibio_pong = False
        
        while running_time() - tiempo_inicio < 1000:
            mensaje = radio.receive()
            if mensaje and mensaje == "PONG:" + device_id:
                recibio_pong = True
                break
            sleep(10)
        
        # Enviar estado por USB
        estado = "online" if recibio_pong else "offline"
        json_str = '{{"type":"ping_result","device_id":"{}","status":"{}"}}'.format(
            device_id, estado
        )
        enviar_por_usb(json_str)
    
    display.clear()


def procesar_comando_usb(linea):
    """Procesa comandos JSON desde USB"""
    try:
        linea = linea.strip()
        if not linea:
            return
        
        # Parse manual de JSON
        if '"type":"question_params"' in linea:
            # Extraer tipo
            tipo = "unica"
            if '"q_type":"multiple"' in linea:
                tipo = "multiple"
            
            # Extraer num_opciones
            num = 4
            if '"num_options":2' in linea:
                num = 2
            elif '"num_options":3' in linea:
                num = 3
            
            broadcast_qparams(tipo, num)
        
        elif '"type":"start_poll"' in linea:
            hacer_polling()
    
    except Exception as e:
        enviar_por_usb('{{"type":"error","msg":"{}"}}'.format(str(e)))


def leer_usb():
    """Lee lineas desde USB si hay datos disponibles"""
    if uart.any():
        try:
            linea = uart.readline()
            if linea:
                linea = linea.decode('utf-8').strip()
                if linea:
                    procesar_comando_usb(linea)
        except Exception as e:
            print("Error leyendo USB:", e)


# === INICIO ===
display.show(Image.HAPPY)
sleep(1000)
display.clear()

cargar_dispositivos()

# === LOOP PRINCIPAL ===
while True:
    # Solo procesar botones si NO estamos en polling
    if not polling_activo:
        # Boton A: Descubrimiento
        if button_a.was_pressed():
            descubrimiento()
        
        # Boton B: Verificar estado (opcional)
        if button_b.was_pressed():
            verificar_estado()
    
    # Leer comandos USB
    leer_usb()
    
    sleep(50)