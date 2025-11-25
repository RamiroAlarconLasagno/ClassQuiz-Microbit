# concentrador.py - Micro:bit Concentrador (FIXED DEBUG)

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
        enviar_por_usb('{{"type":"debug","msg":"Dispositivos_cargados:{}"}}'.format(len(dispositivos_registrados)))
    except:
        dispositivos_registrados = set()
        enviar_por_usb('{"type":"debug","msg":"Sin_dispositivos_previos"}')


def guardar_dispositivos():
    """Guarda lista de dispositivos en archivo"""
    try:
        with open(CONFIG_FILE, 'w') as f:
            f.write(repr(list(dispositivos_registrados)))
        enviar_por_usb('{"type":"debug","msg":"Dispositivos_guardados_OK"}')
    except Exception as e:
        enviar_por_usb('{{"type":"debug","msg":"Error_guardando:{}"}}'.format(str(e)))


def descubrimiento():
    """Proceso de descubrimiento de dispositivos"""
    enviar_por_usb('{"type":"debug","msg":"=== INICIO_DESCUBRIMIENTO ==="}')
    display.show(Image.HEART)
    dispositivos_registrados.clear()
    
    enviar_por_usb('{"type":"discovery_start"}')
    
    # 6 rondas de REPORT en 12 segundos
    for ronda in range(6):
        enviar_por_usb('{{"type":"debug","msg":"Enviando_REPORT_ronda_{}"}}'.format(ronda + 1))
        radio.send("REPORT")
        enviar_por_usb('{{"type":"debug","msg":"REPORT_enviado_ronda_{}"}}'.format(ronda + 1))
        
        # Procesar respuestas durante 2 segundos
        tiempo_inicio = running_time()
        enviar_por_usb('{{"type":"debug","msg":"Escuchando_2s_ronda_{}"}}'.format(ronda + 1))
        
        while running_time() - tiempo_inicio < 2000:
            mensaje = radio.receive()
            if mensaje:
                enviar_por_usb('{{"type":"debug","msg":"RX_radio:{}"}}'.format(mensaje))
                if mensaje.startswith("ID:"):
                    procesar_id_dispositivo(mensaje)
            sleep(10)
        
        enviar_por_usb('{{"type":"debug","msg":"Fin_escucha_ronda_{}"}}'.format(ronda + 1))
    
    # Enviar lista completa por USB
    lista_ids = list(dispositivos_registrados)
    enviar_por_usb('{{"type":"debug","msg":"Preparando_device_list:{}_dispositivos"}}'.format(len(lista_ids)))
    
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
    
    enviar_por_usb('{"type":"debug","msg":"=== FIN_DESCUBRIMIENTO ==="}')
    display.show(len(dispositivos_registrados))
    sleep(2000)
    display.clear()


def procesar_id_dispositivo(mensaje):
    """Procesa mensaje ID de estudiante"""
    device_id = mensaje[3:]
    enviar_por_usb('{{"type":"debug","msg":"Procesando_ID:{}"}}'.format(device_id[:8]))
    
    if device_id not in dispositivos_registrados:
        enviar_por_usb('{{"type":"debug","msg":"Nuevo_dispositivo:{}"}}'.format(device_id[:8]))
        dispositivos_registrados.add(device_id)
        
        enviar_por_usb('{{"type":"debug","msg":"Enviando_ACK_a:{}"}}'.format(device_id[:8]))
        radio.send("ACK:" + device_id)
        
        # Notificar por USB
        enviar_por_usb('{{"type":"new_device","device_id":"{}"}}'.format(device_id))
        display.scroll(len(dispositivos_registrados), delay=60)
    else:
        enviar_por_usb('{{"type":"debug","msg":"Dispositivo_ya_registrado:{}"}}'.format(device_id[:8]))


def broadcast_qparams(tipo_pregunta, num_opciones):
    """Envia parametros de pregunta por radio"""
    enviar_por_usb('{"type":"debug","msg":"=== BROADCAST_QPARAMS ==="}')
    
    mensaje = "QPARAMS:{}:{}".format(tipo_pregunta, num_opciones)
    enviar_por_usb('{{"type":"debug","msg":"TX_radio:{}"}}'.format(mensaje))
    
    # Enviar por radio
    radio.send(mensaje)
    enviar_por_usb('{"type":"debug","msg":"QPARAMS_enviado_por_radio"}')
    
    # Notificar al proxy
    enviar_por_usb('{{"type":"qparams_sent","q_type":"{}","num_options":{}}}'.format(
        tipo_pregunta, num_opciones
    ))
    
    # Dar tiempo para procesamiento
    sleep(500)
    
    display.show(Image.ARROW_E)
    sleep(200)
    display.clear()
    enviar_por_usb('{"type":"debug","msg":"=== FIN_BROADCAST_QPARAMS ==="}')


def hacer_polling():
    """Polling secuencial de todos los dispositivos"""
    global polling_activo
    polling_activo = True
    
    enviar_por_usb('{"type":"debug","msg":"=== INICIO_POLLING ==="}')
    display.show(Image.ASLEEP)
    
    lista_dispositivos = list(dispositivos_registrados)
    enviar_por_usb('{{"type":"debug","msg":"Polling_de_{}_dispositivos"}}'.format(len(lista_dispositivos)))
    
    for idx, device_id in enumerate(lista_dispositivos):
        enviar_por_usb('{{"type":"debug","msg":"Polling_dispositivo_{}_de_{}"}}'.format(
            idx + 1, len(lista_dispositivos)
        ))
        
        # Mostrar progreso
        display.show(str(idx + 1))
        
        respuesta_recibida = None
        intentos = 0
        
        # Hasta 2 intentos
        while intentos < 2 and respuesta_recibida is None:
            enviar_por_usb('{{"type":"debug","msg":"TX_POLL_intento_{}"}}'.format(intentos + 1))
            
            radio.send("POLL:" + device_id)
            enviar_por_usb('{{"type":"debug","msg":"POLL_enviado"}}'.format(device_id[:8]))
            
            # Esperar respuesta 500ms
            tiempo_inicio = running_time()
            while running_time() - tiempo_inicio < 500:
                mensaje = radio.receive()
                if mensaje:
                    enviar_por_usb('{{"type":"debug","msg":"RX_radio:{}"}}'.format(mensaje))
                    
                    if mensaje.startswith("ANSWER:"):
                        partes = mensaje.split(':', 2)
                        if len(partes) >= 2 and partes[1] == device_id:
                            respuesta_recibida = partes[2] if len(partes) == 3 else ""
                            enviar_por_usb('{{"type":"debug","msg":"ANSWER_OK:{}"}}'.format(respuesta_recibida))
                            break
                sleep(10)
            
            if respuesta_recibida is None:
                enviar_por_usb('{{"type":"debug","msg":"Sin_respuesta_intento_{}"}}'.format(intentos + 1))
            
            intentos += 1
        
        # Si no hubo respuesta, enviar vacio
        if respuesta_recibida is None:
            respuesta_recibida = ""
            enviar_por_usb('{"type":"debug","msg":"Enviando_respuesta_vacia"}')
        
        # Enviar por USB
        json_str = '{{"type":"answer","device_id":"{}","answer":"{}"}}'.format(
            device_id, respuesta_recibida
        )
        enviar_por_usb(json_str)
    
    # Polling completo
    enviar_por_usb('{"type":"polling_complete"}')
    enviar_por_usb('{"type":"debug","msg":"=== FIN_POLLING ==="}')
    
    polling_activo = False
    
    display.show(Image.HAPPY)
    sleep(1000)
    display.clear()


def verificar_estado():
    """Verifica estado de dispositivos con PING"""
    enviar_por_usb('{"type":"debug","msg":"=== VERIFICACION_ESTADO ==="}')
    display.show(Image.GHOST)
    
    for device_id in list(dispositivos_registrados):
        enviar_por_usb('{{"type":"debug","msg":"TX_PING"}')
        radio.send("PING:" + device_id)
        
        # Esperar PONG 1 segundo
        tiempo_inicio = running_time()
        recibio_pong = False
        
        while running_time() - tiempo_inicio < 1000:
            mensaje = radio.receive()
            if mensaje:
                enviar_por_usb('{{"type":"debug","msg":"RX_radio:{}"}}'.format(mensaje))
                if mensaje == "PONG:" + device_id:
                    recibio_pong = True
                    break
            sleep(10)
        
        # Enviar estado por USB
        estado = "online" if recibio_pong else "offline"
        json_str = '{{"type":"ping_result","device_id":"{}","status":"{}"}}'.format(
            device_id, estado
        )
        enviar_por_usb(json_str)
    
    enviar_por_usb('{"type":"debug","msg":"=== FIN_VERIFICACION ==="}')
    display.clear()


def procesar_comando_usb(linea):
    """Procesa comandos JSON desde USB"""
    # NO meter el JSON recibido dentro de otro JSON - causa problemas de parsing
    enviar_por_usb('{"type":"debug","msg":"CMD_USB_recibido"}')
    
    try:
        linea = linea.strip()
        if not linea:
            enviar_por_usb('{"type":"debug","msg":"Linea_vacia_ignorada"}')
            return
        
        # Parse manual de JSON - buscar patrones (con o sin espacios)
        if 'question_params' in linea:
            enviar_por_usb('{"type":"debug","msg":"Detectado:question_params"}')
            
            # Extraer tipo
            tipo = "unica"
            if 'multiple' in linea:
                tipo = "multiple"
            
            # Extraer num_opciones
            num = 4
            if '2' in linea:
                num = 2
            elif '3' in linea:
                num = 3
            elif '4' in linea:
                num = 4
            
            enviar_por_usb('{{"type":"debug","msg":"Parseado_tipo:{}_opciones:{}"}}'.format(tipo, num))
            broadcast_qparams(tipo, num)
        
        elif 'start_poll' in linea:
            enviar_por_usb('{"type":"debug","msg":"Detectado:start_poll"}')
            hacer_polling()
        
        else:
            enviar_por_usb('{"type":"debug","msg":"Comando_no_reconocido"}')
    
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
            enviar_por_usb('{{"type":"debug","msg":"Error_leyendo_USB:{}"}}'.format(str(e)))


# === INICIO ===
enviar_por_usb('{"type":"debug","msg":"=== CONCENTRADOR_INICIADO ==="}')
display.show(Image.HAPPY)
sleep(1000)
display.clear()

cargar_dispositivos()
enviar_por_usb('{"type":"debug","msg":"Sistema_listo"}')

# === LOOP PRINCIPAL ===
while True:
    # Solo procesar botones si NO estamos en polling
    if not polling_activo:
        # Boton A: Descubrimiento
        if button_a.was_pressed():
            enviar_por_usb('{"type":"debug","msg":"Boton_A_presionado"}')
            descubrimiento()
        
        # Boton B: Verificar estado
        if button_b.was_pressed():
            enviar_por_usb('{"type":"debug","msg":"Boton_B_presionado"}')
            verificar_estado()
    
    # Leer comandos USB
    leer_usb()
    
    sleep(50)