// app.js - Lógica frontend del sistema
// Sistema Proxy Microbit-ClassQuiz

// ============================================================================
// CONEXIÓN SOCKET.IO
// ============================================================================

const socket = io('http://localhost:5000');

// ============================================================================
// ESTADO GLOBAL
// ============================================================================

const state = {
    dispositivos: {},
    logs: [],
    debugVisible: true,
    autoScroll: true,
    preguntaActiva: null,
    countdownInterval: null
};

// ============================================================================
// EVENTOS SOCKET.IO
// ============================================================================

socket.on('connect', () => {
    console.log('[Socket.IO] Conectado al servidor');
    actualizarEstadoConexion(true);
    agregarLog('INFO', 'Conectado al servidor Flask');
});

socket.on('disconnect', () => {
    console.log('[Socket.IO] Desconectado del servidor');
    actualizarEstadoConexion(false);
    agregarLog('WARNING', 'Desconectado del servidor Flask');
});

socket.on('log', (data) => {
    agregarLog(data.nivel, data.msg, data.timestamp);
});

socket.on('dispositivos_actualizados', (data) => {
    state.dispositivos = data.dispositivos;
    actualizarTablaDispositivos();
    actualizarEstadisticas();
});

socket.on('respuesta_recibida', (data) => {
    agregarLog('INFO', `Respuesta recibida: ${data.nombre} → ${data.respuesta}`);
    actualizarRespuestaEnLista(data.device_id, data.nombre, data.respuesta);
});

socket.on('countdown', (data) => {
    actualizarCountdown(data.segundos);
});

socket.on('pregunta_nueva', (data) => {
    state.preguntaActiva = data;
    mostrarPanelPregunta(data);
    agregarLog('INFO', `Nueva pregunta: ${data.tipo} con ${data.num_opciones} opciones`);
});

socket.on('config_cargada', (data) => {
    agregarLog('INFO', 'Configuración cargada desde archivo CSV');

    // Actualizar inputs
    if (data.url) document.getElementById('url-input').value = data.url;
    if (data.pin) document.getElementById('pin-input').value = data.pin;
    if (data.timeout) document.getElementById('timeout-input').value = data.timeout;

    // Actualizar dispositivos desde alumnos
    if (data.alumnos && Array.isArray(data.alumnos)) {
        // Convertir array de alumnos a objeto de dispositivos
        const nuevosDispositivos = {};
        data.alumnos.forEach(alumno => {
            if (alumno.id) {
                nuevosDispositivos[alumno.id] = {
                    id: alumno.id,
                    nombre: alumno.nombre,
                    estado: alumno.estado || 'offline'
                };
            }
        });

        state.dispositivos = nuevosDispositivos;
        actualizarTablaDispositivos();
        actualizarEstadisticas();

        agregarLog('INFO', `${data.alumnos.length} alumnos cargados en tabla`);
    }
});

// ============================================================================
// FUNCIONES UI - ESTADO CONEXIÓN
// ============================================================================

function actualizarEstadoConexion(conectado) {
    const badge = document.getElementById('status-badge');
    
    if (conectado) {
        badge.textContent = '🟢 Conectado';
        badge.className = 'badge bg-success';
    } else {
        badge.textContent = '🔴 Desconectado';
        badge.className = 'badge bg-danger';
    }
}

// ============================================================================
// FUNCIONES UI - LOGS
// ============================================================================

function agregarLog(nivel, mensaje, timestamp) {
    const log = {
        nivel: nivel,
        msg: mensaje,
        timestamp: timestamp || new Date().toLocaleTimeString()
    };
    
    state.logs.push(log);
    
    // Limitar a últimos 500 logs
    if (state.logs.length > 500) {
        state.logs.shift();
    }
    
    // Renderizar solo si es visible o no es DEBUG
    if (state.debugVisible || nivel !== 'DEBUG') {
        renderizarLog(log);
    }
}

function renderizarLog(log) {
    const logList = document.getElementById('log-list');
    
    const li = document.createElement('li');
    li.className = `list-group-item log-item ${log.nivel}`;
    li.textContent = `[${log.timestamp}] ${log.msg}`;
    
    logList.appendChild(li);
    
    // Auto-scroll si está habilitado
    if (state.autoScroll) {
        const container = document.getElementById('log-container');
        container.scrollTop = container.scrollHeight;
    }
}

function limpiarLogs() {
    document.getElementById('log-list').innerHTML = '';
}

function refrescarLogs() {
    limpiarLogs();
    
    state.logs.forEach(log => {
        if (state.debugVisible || log.nivel !== 'DEBUG') {
            renderizarLog(log);
        }
    });
}

// ============================================================================
// FUNCIONES UI - DISPOSITIVOS
// ============================================================================

function actualizarTablaDispositivos() {
    const tbody = document.getElementById('dispositivos-tbody');
    tbody.innerHTML = '';
    
    const dispositivos = Object.entries(state.dispositivos);
    
    if (dispositivos.length === 0) {
        const tr = document.createElement('tr');
        tr.innerHTML = '<td colspan="3" class="text-center text-muted">No hay dispositivos registrados</td>';
        tbody.appendChild(tr);
        return;
    }
    
    dispositivos.forEach(([device_id, info]) => {
        const tr = document.createElement('tr');
        
        // Device ID
        const tdId = document.createElement('td');
        tdId.className = 'text-monospace';
        tdId.textContent = device_id;
        
        // Nombre (editable)
        const tdNombre = document.createElement('td');
        const inputNombre = document.createElement('input');
        inputNombre.type = 'text';
        inputNombre.className = 'nombre-input';
        inputNombre.value = info.nombre || '';
        inputNombre.placeholder = 'Nombre del alumno';
        inputNombre.dataset.deviceId = device_id;
        
        inputNombre.addEventListener('change', (e) => {
            const nuevoNombre = e.target.value.trim();
            if (nuevoNombre) {
                state.dispositivos[device_id].nombre = nuevoNombre;
            }
        });
        
        tdNombre.appendChild(inputNombre);
        
        // Estado
        const tdEstado = document.createElement('td');
        const estado = info.estado || 'offline';
        
        let estadoTexto, estadoClase;
        switch(estado) {
            case 'online':
                estadoTexto = '🟢 Online';
                estadoClase = 'estado-online';
                break;
            case 'registrado':
                estadoTexto = '🟡 Registrado';
                estadoClase = 'estado-registrado';
                break;
            case 'desconectado':
                estadoTexto = '🔴 Desconectado';
                estadoClase = 'estado-desconectado';
                break;
            default:
                estadoTexto = '⚪ Offline';
                estadoClase = 'estado-offline';
        }
        
        tdEstado.innerHTML = `<span class="${estadoClase}">${estadoTexto}</span>`;
        
        tr.appendChild(tdId);
        tr.appendChild(tdNombre);
        tr.appendChild(tdEstado);
        
        tbody.appendChild(tr);
    });
}

function actualizarEstadisticas() {
    const total = Object.keys(state.dispositivos).length;
    const conectados = Object.values(state.dispositivos).filter(d => d.estado === 'online').length;
    
    const statsText = document.getElementById('stats-text');
    statsText.textContent = `Total: ${total} alumnos / ${conectados} conectados`;
}

// ============================================================================
// FUNCIONES UI - PANEL PREGUNTA
// ============================================================================

function mostrarPanelPregunta(pregunta) {
    const panel = document.getElementById('pregunta-panel');
    panel.classList.remove('d-none');
    
    // Actualizar info
    const infoEl = document.getElementById('pregunta-info');
    infoEl.innerHTML = `<strong>Pregunta #${pregunta.index}:</strong> ${pregunta.tipo} con ${pregunta.num_opciones} opciones`;
    
    // Limpiar lista de respuestas
    const lista = document.getElementById('respuestas-list');
    lista.innerHTML = '';
    
    // Crear items para cada alumno
    Object.entries(state.dispositivos).forEach(([device_id, info]) => {
        const li = document.createElement('li');
        li.className = 'list-group-item d-flex justify-content-between align-items-center';
        li.id = `respuesta-${device_id}`;
        
        const nombre = info.nombre || device_id.substring(0, 8);
        li.innerHTML = `
            <span>${nombre}</span>
            <span class="badge bg-secondary">Esperando...</span>
        `;
        
        lista.appendChild(li);
    });
    
    // Iniciar countdown
    actualizarCountdown(pregunta.timeout || 30);
}

function actualizarCountdown(segundos) {
    const countdownEl = document.getElementById('countdown-info');
    
    if (segundos > 0) {
        countdownEl.innerHTML = `<strong>Tiempo restante:</strong> <span class="badge bg-warning text-dark">${segundos}s</span>`;
    } else {
        countdownEl.innerHTML = `<strong>Tiempo restante:</strong> <span class="badge bg-danger">Completo</span>`;
    }
}

function actualizarRespuestaEnLista(device_id, nombre, respuesta) {
    const li = document.getElementById(`respuesta-${device_id}`);
    
    if (li) {
        const nombreSpan = li.querySelector('span:first-child');
        const badgeSpan = li.querySelector('.badge');
        
        nombreSpan.textContent = nombre;
        badgeSpan.textContent = respuesta || '(vacía)';
        badgeSpan.className = 'badge bg-success';
    }
}

function ocultarPanelPregunta() {
    const panel = document.getElementById('pregunta-panel');
    panel.classList.add('d-none');
    
    state.preguntaActiva = null;
}

// ============================================================================
// EVENT LISTENERS - BOTONES
// ============================================================================

// Guardar TODO (configuración + alumnos)
document.getElementById('guardar-todo-btn').addEventListener('click', async () => {
    const url = document.getElementById('url-input').value.trim();
    const pin = document.getElementById('pin-input').value.trim();
    const timeout = parseInt(document.getElementById('timeout-input').value);
    const nombreArchivo = document.getElementById('nombre-archivo-input').value.trim();

    if (!url || !pin) {
        alert('Por favor completa URL y PIN');
        return;
    }

    if (!nombreArchivo) {
        alert('Por favor ingresa un nombre para el archivo');
        return;
    }

    try {
        agregarLog('INFO', `Guardando en archivo: ${nombreArchivo}.csv`);

        const response = await fetch('/api/guardar_todo', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                url,
                pin,
                timeout,
                nombre_archivo: nombreArchivo,
                alumnos: Object.entries(state.dispositivos).map(([id, info]) => ({
                    id: id,
                    nombre: info.nombre || ''
                }))
            })
        });

        const data = await response.json();

        if (data.status === 'ok') {
            agregarLog('INFO', `✅ Guardado en: ${data.archivo}`);
            alert(`✅ Guardado exitoso en:\n${data.archivo}\n\nConfig + ${data.alumnos_guardados || 0} alumnos`);
        } else {
            throw new Error(data.error || 'Error desconocido');
        }
    } catch (error) {
        console.error('Error guardando:', error);
        agregarLog('ERROR', `Error guardando: ${error.message}`);
        alert('❌ Error guardando archivo');
    }
});

// Conectar a ClassQuiz
document.getElementById('conectar-classquiz-btn').addEventListener('click', async () => {
    agregarLog('INFO', 'Conectando dispositivos a ClassQuiz...');

    // Mostrar estado
    const statusAlert = document.getElementById('status-conexion-alert');
    const statusTexto = document.getElementById('status-conexion-texto');
    statusAlert.classList.remove('d-none');
    statusTexto.textContent = 'Conectando...';

    try {
        const response = await fetch('/api/conectar_classquiz', {
            method: 'POST'
        });

        const data = await response.json();

        if (response.ok && data.status === 'ok') {
            agregarLog('INFO', `Conexión iniciada para ${data.count} dispositivo(s)`);
            statusTexto.textContent = `✅ ${data.count} dispositivo(s) conectándose...`;
            statusAlert.className = 'alert alert-success mt-3';

            // Ocultar después de 5 segundos
            setTimeout(() => {
                statusAlert.classList.add('d-none');
            }, 5000);
        } else {
            throw new Error(data.error || 'Error desconocido');
        }
    } catch (error) {
        console.error('Error conectando a ClassQuiz:', error);
        agregarLog('ERROR', `Error conectando a ClassQuiz: ${error.message}`);
        statusTexto.textContent = `❌ ${error.message}`;
        statusAlert.className = 'alert alert-danger mt-3';
    }
});

// Descubrir dispositivos
document.getElementById('descubrir-btn').addEventListener('click', async () => {
    agregarLog('INFO', 'Iniciando descubrimiento de dispositivos...');
    
    try {
        const response = await fetch('/api/descubrir', {
            method: 'POST'
        });
        
        const data = await response.json();
        
        if (data.status === 'ok') {
            agregarLog('INFO', 'Comando de descubrimiento enviado');
        } else {
            throw new Error(data.error || 'Error desconocido');
        }
    } catch (error) {
        console.error('Error en descubrimiento:', error);
        agregarLog('ERROR', `Error en descubrimiento: ${error.message}`);
    }
});

// Cargar configuración
document.getElementById('cargar-config-btn').addEventListener('click', async () => {
    const nombreArchivo = document.getElementById('nombre-archivo-input').value.trim();

    if (!nombreArchivo) {
        alert('Por favor ingresa el nombre del archivo a cargar');
        return;
    }

    agregarLog('INFO', `Cargando desde archivo: ${nombreArchivo}.csv`);

    try {
        const response = await fetch('/api/cargar_config', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                nombre_archivo: nombreArchivo
            })
        });

        const data = await response.json();

        if (data.status === 'ok') {
            agregarLog('INFO', `✅ Cargado desde: ${data.archivo}`);
            agregarLog('INFO', `Config cargada + ${data.alumnos_cargados || 0} alumnos`);
            alert(`✅ Archivo cargado:\n${data.archivo}\n\nConfig + ${data.alumnos_cargados || 0} alumnos`);
        } else {
            throw new Error(data.error || 'Error desconocido');
        }
    } catch (error) {
        console.error('Error cargando config:', error);
        agregarLog('ERROR', `Error cargando: ${error.message}`);
        alert(`❌ Error cargando archivo:\n${error.message}`);
    }
});

// Finalizar votación
document.getElementById('finalizar-btn').addEventListener('click', () => {
    if (confirm('¿Finalizar votación ahora?')) {
        socket.emit('finalizar_votacion');
        agregarLog('INFO', 'Votación finalizada manualmente');
        ocultarPanelPregunta();
    }
});

// Toggle DEBUG
document.getElementById('debug-checkbox').addEventListener('change', (e) => {
    state.debugVisible = e.target.checked;
    refrescarLogs();
    agregarLog('INFO', `Logs DEBUG ${state.debugVisible ? 'activados' : 'desactivados'}`);
});

// Exportar logs
document.getElementById('exportar-btn').addEventListener('click', () => {
    const texto = state.logs.map(log => `[${log.timestamp}] [${log.nivel}] ${log.msg}`).join('\n');
    
    const blob = new Blob([texto], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    
    const a = document.createElement('a');
    a.href = url;
    a.download = `logs_${new Date().toISOString().replace(/:/g, '-')}.txt`;
    a.click();
    
    URL.revokeObjectURL(url);
    
    agregarLog('INFO', 'Logs exportados a archivo');
});

// ============================================================================
// AUTO-SCROLL PAUSABLE
// ============================================================================

let pauseTimeout = null;

document.getElementById('log-container').addEventListener('click', () => {
    const container = document.getElementById('log-container');
    
    // Pausar auto-scroll por 5 segundos
    state.autoScroll = false;
    container.classList.add('paused');
    
    // Limpiar timeout previo
    if (pauseTimeout) {
        clearTimeout(pauseTimeout);
    }
    
    // Restaurar después de 5s
    pauseTimeout = setTimeout(() => {
        state.autoScroll = true;
        container.classList.remove('paused');
    }, 5000);
});

// ============================================================================
// INICIALIZACIÓN
// ============================================================================

window.addEventListener('load', async () => {
    agregarLog('INFO', 'Interface web cargada');
    
    // Cargar configuración inicial
    try {
        const response = await fetch('/api/config');
        const data = await response.json();
        
        if (data.url) document.getElementById('url-input').value = data.url;
        if (data.pin) document.getElementById('pin-input').value = data.pin;
        if (data.timeout) document.getElementById('timeout-input').value = data.timeout;
        
    } catch (error) {
        console.error('Error cargando config inicial:', error);
    }
});

// ============================================================================
// BÚSQUEDA EN LOGS
// ============================================================================

document.getElementById('buscar-input').addEventListener('input', (e) => {
    const busqueda = e.target.value.toLowerCase();
    const items = document.querySelectorAll('.log-item');
    
    items.forEach(item => {
        const texto = item.textContent.toLowerCase();
        item.style.display = texto.includes(busqueda) ? 'block' : 'none';
    });
});