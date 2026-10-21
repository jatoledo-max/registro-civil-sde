/* ════════════════════════════════════════════
   Módulo de Turnos — Registro Civil
   ════════════════════════════════════════════ */

const ModTurnos = {

  pasoActual: 1,
  enviando: false,

  tramiteLabels: {
    'dni-5-8':      'DNI – Actualización 5-8 años',
    'dni-14':       'DNI – Actualización 14 años',
    'dni-domicilio':'DNI – Cambio de domicilio',
    'dni-nuevo':    'DNI – Nuevo ejemplar',
  },

  // Reglas de validación — mismas que en el backend (turnos/views.py)
  reglas: {
    'turno-nombre': v => {
      if (!v) return 'Ingresá tu nombre y apellido.';
      if (v.length < 3 || v.length > 100 || !/^[A-Za-zÁÉÍÓÚÜÑáéíóúüñ' .-]+$/.test(v))
        return 'Usá solo letras (entre 3 y 100 caracteres).';
      if (v.split(/\s+/).length < 2) return 'Ingresá nombre y apellido.';
      return '';
    },
    'turno-dni': v => {
      if (!v) return 'Ingresá tu DNI.';
      if (!/^\d{7,8}$/.test(v)) return 'El DNI debe tener 7 u 8 dígitos, sin puntos.';
      return '';
    },
    'turno-email': v => {
      if (!v) return 'Ingresá tu correo electrónico.';
      if (!/^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(v)) return 'Ingresá un correo válido (ej: nombre@gmail.com).';
      return '';
    },
    'turno-telefono': v => {
      if (!v) return 'Ingresá tu teléfono.';
      const digitos = v.replace(/\D/g, '');
      if (!/^\+?[\d\s()-]+$/.test(v) || digitos.length < 10 || digitos.length > 13)
        return 'Ingresá el número con código de área (ej: 3854123456).';
      return '';
    },
    'turno-direccion': v => {
      if (!v) return 'Ingresá tu dirección.';
      if (v.length < 5) return 'La dirección es demasiado corta.';
      return '';
    },
  },

  // ── Inicializar ──
  init() {
    const inputFecha = document.getElementById('turno-fecha');
    if (inputFecha) {
      inputFecha.min = this.hoyLocal();
      inputFecha.addEventListener('change', () => this.generarHorarios());
    }

    document.getElementById('turno-horario')?.addEventListener('change', () => {
      this.ocultarError('error-fecha');
      this.actualizarResumen();
    });

    // El DNI solo acepta números (se quitan puntos y espacios al tipear)
    document.getElementById('turno-dni')?.addEventListener('input', e => {
      e.target.value = e.target.value.replace(/\D/g, '').slice(0, 8);
    });

    // Al corregir un campo, se limpia su error
    Object.keys(this.reglas).forEach(id => {
      const el = document.getElementById(id);
      el?.addEventListener('input', () => this.marcarCampo(id, ''));
      el?.addEventListener('blur', () => {
        if (el.value.trim()) this.marcarCampo(id, this.reglas[id](this.valor(id)));
      });
    });

    document.querySelectorAll('input[name="turno-tramite"]').forEach(r =>
      r.addEventListener('change', () => this.ocultarError('error-tramite'))
    );

    // Preseleccionar el trámite si el modal se abre desde la página de un trámite
    document.getElementById('modalTurno')?.addEventListener('show.bs.modal', e => {
      const tramite = e.relatedTarget?.dataset?.tramite;
      const radio = tramite && document.querySelector(`input[name="turno-tramite"][value="${tramite}"]`);
      if (radio) radio.checked = true;
    });

    // Limpiar al cerrar el modal
    document.getElementById('modalTurno')?.addEventListener('hidden.bs.modal', () => {
      this.resetear();
    });
  },

  // Fecha de hoy en hora local (toISOString usa UTC y después de las 21 hs daría "mañana")
  hoyLocal() {
    const d = new Date();
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
  },

  valor(id) {
    const el = document.getElementById(id);
    return el ? el.value.trim().replace(/\s+/g, ' ') : '';
  },

  marcarCampo(id, mensaje) {
    const el  = document.getElementById(id);
    const err = document.getElementById(`${id}-error`);
    el?.classList.toggle('error', !!mensaje);
    el?.setAttribute('aria-invalid', mensaje ? 'true' : 'false');
    if (err) {
      err.textContent = mensaje;
      err.classList.toggle('show', !!mensaje);
    }
  },

  mostrarError(id, mensaje) {
    const el = document.getElementById(id);
    if (!el) return;
    el.innerHTML = '<i class="bi bi-exclamation-circle-fill me-1"></i>';
    el.appendChild(document.createTextNode(mensaje));
    el.style.display = 'flex';
  },

  ocultarError(id) {
    const el = document.getElementById(id);
    if (el) el.style.display = 'none';
  },

  // ── Generar horarios consultando disponibilidad real en Django ──
  async generarHorarios() {
    const fecha   = document.getElementById('turno-fecha').value;
    const select  = document.getElementById('turno-horario');
    const resumen = document.getElementById('turno-resumen');
    this.ocultarError('error-fecha');
    if (resumen) resumen.style.display = 'none';

    if (!fecha) {
      select.innerHTML = '<option value="">Seleccioná un horario</option>';
      return;
    }

    if (fecha < this.hoyLocal()) {
      select.innerHTML = '<option value="">Seleccioná un horario</option>';
      this.mostrarError('error-fecha', 'No podés elegir una fecha pasada.');
      return;
    }

    select.disabled  = true;
    select.innerHTML = '<option value="">Cargando horarios...</option>';

    try {
      const r    = await fetch(RC.url(`/api/turnos/disponibilidad/?fecha=${encodeURIComponent(fecha)}`));
      const data = await r.json();

      if (!r.ok || data.error) {
        select.innerHTML = '<option value="">Seleccioná un horario</option>';
        this.mostrarError('error-fecha', data.error || 'Fecha inválida.');
        return;
      }

      if (!data.habil) {
        select.innerHTML = '<option value="">Sin turnos este día</option>';
        this.mostrarError('error-fecha', 'No hay atención ese día (fin de semana o feriado). Elegí otra fecha.');
        return;
      }

      if (!data.habil_dia) {
        select.innerHTML = '<option value="">Sin turnos disponibles</option>';
        this.mostrarError('error-fecha', 'No quedan turnos disponibles para ese día. Elegí otra fecha.');
        return;
      }

      select.innerHTML = '<option value="">Seleccioná un horario</option>';
      data.slots.forEach(slot => {
        const opt = document.createElement('option');
        opt.value = slot.hora;
        opt.textContent = slot.lleno
          ? `${slot.hora} hs. — Sin disponibilidad`
          : `${slot.hora} hs.`;
        opt.disabled = slot.lleno;
        select.appendChild(opt);
      });

    } catch (e) {
      select.innerHTML = '<option value="">Seleccioná un horario</option>';
      this.mostrarError('error-fecha', 'Error al cargar los horarios. Revisá tu conexión y reintentá.');
    } finally {
      select.disabled = false;
    }
  },

  // ── Actualizar resumen ──
  actualizarResumen() {
    const fecha   = document.getElementById('turno-fecha').value;
    const horario = document.getElementById('turno-horario').value;
    const tramite = document.querySelector('input[name="turno-tramite"]:checked')?.value;
    const resumen = document.getElementById('turno-resumen');

    if (!fecha || !horario || !tramite) {
      if (resumen) resumen.style.display = 'none';
      return;
    }

    document.getElementById('res-tramite').textContent = this.tramiteLabels[tramite] || tramite;
    document.getElementById('res-nombre').textContent  = this.valor('turno-nombre');
    document.getElementById('res-dni').textContent     = this.valor('turno-dni');
    document.getElementById('res-fecha').textContent   = this.formatearFecha(fecha);
    document.getElementById('res-horario').textContent = `${horario} hs.`;

    resumen.style.display = 'block';
  },

  formatearFecha(fecha) {
    const [y, m, d] = fecha.split('-');
    const dias = ['Domingo','Lunes','Martes','Miércoles','Jueves','Viernes','Sábado'];
    return `${dias[new Date(fecha + 'T00:00:00').getDay()]} ${d}/${m}/${y}`;
  },

  // ── Validar paso actual ──
  validarPaso() {
    if (this.pasoActual === 1) {
      if (!document.querySelector('input[name="turno-tramite"]:checked')) {
        this.mostrarError('error-tramite', 'Seleccioná un trámite para continuar.');
        return false;
      }
      this.ocultarError('error-tramite');
      return true;
    }

    if (this.pasoActual === 2) {
      let primero = null;
      Object.keys(this.reglas).forEach(id => {
        const msg = this.reglas[id](this.valor(id));
        this.marcarCampo(id, msg);
        if (msg && !primero) primero = id;
      });
      if (primero) {
        this.mostrarError('error-datos', 'Revisá los campos marcados en rojo.');
        document.getElementById(primero)?.focus();
        return false;
      }
      this.ocultarError('error-datos');
      return true;
    }

    if (this.pasoActual === 3) {
      const fecha   = document.getElementById('turno-fecha').value;
      const horario = document.getElementById('turno-horario').value;
      const dia     = fecha ? new Date(fecha + 'T00:00:00').getDay() : -1;

      if (!fecha) {
        this.mostrarError('error-fecha', 'Seleccioná una fecha.');
        return false;
      }
      if (fecha < this.hoyLocal()) {
        this.mostrarError('error-fecha', 'No podés elegir una fecha pasada.');
        return false;
      }
      if (dia === 0 || dia === 6) {
        this.mostrarError('error-fecha', 'Los turnos son de lunes a viernes. Elegí otra fecha.');
        return false;
      }
      if (!horario) {
        this.mostrarError('error-fecha', 'Seleccioná un horario disponible.');
        return false;
      }
      this.ocultarError('error-fecha');
      this.actualizarResumen();
      return true;
    }

    return true;
  },

  // ── Avanzar paso ──
  siguiente() {
    if (this.enviando || !this.validarPaso()) return;

    if (this.pasoActual === 3) {
      this.confirmar();
      return;
    }

    this.pasoActual++;
    this.mostrarPaso();
  },

  // ── Retroceder paso ──
  anterior() {
    if (this.enviando) return;
    if (this.pasoActual > 1) {
      this.pasoActual--;
      this.mostrarPaso();
    }
  },

  // ── Mostrar paso actual ──
  mostrarPaso() {
    for (let i = 1; i <= 3; i++) {
      const paso = document.getElementById(`turno-paso-${i}`);
      if (paso) paso.style.display = i === this.pasoActual ? 'block' : 'none';

      // Indicadores
      const ind = document.getElementById(`step-ind-${i}`);
      if (ind) {
        const circle = ind.querySelector('.step-circle');
        if (i < this.pasoActual)       circle.className = 'step-circle done';
        else if (i === this.pasoActual) circle.className = 'step-circle active';
        else                            circle.className = 'step-circle';
      }
    }

    // Botones
    const btnAnterior  = document.getElementById('btn-turno-anterior');
    const btnSiguiente = document.getElementById('btn-turno-siguiente');

    btnAnterior.style.display  = this.pasoActual > 1 ? 'inline-flex' : 'none';
    btnSiguiente.innerHTML     = this.pasoActual === 3
      ? '<i class="bi bi-check-circle-fill me-1"></i> Confirmar turno'
      : 'Siguiente <i class="bi bi-arrow-right ms-1"></i>';

    if (this.pasoActual === 3) this.actualizarResumen();
  },

  // ── Confirmar turno — envía a Django ──
  async confirmar() {
    const tramite   = document.querySelector('input[name="turno-tramite"]:checked')?.value;
    const nombre    = this.valor('turno-nombre');
    const dni       = this.valor('turno-dni');
    const email     = this.valor('turno-email');
    const telefono  = this.valor('turno-telefono');
    const direccion = this.valor('turno-direccion');
    const fecha     = document.getElementById('turno-fecha').value;
    const horario   = document.getElementById('turno-horario').value;

    const btnConfirmar = document.getElementById('btn-turno-siguiente');
    const btnAnterior  = document.getElementById('btn-turno-anterior');
    const restaurarBoton = () => {
      this.enviando = false;
      btnConfirmar.disabled = false;
      btnAnterior.disabled  = false;
      btnConfirmar.innerHTML = '<i class="bi bi-check-circle-fill me-1"></i> Confirmar turno';
    };

    this.enviando = true;
    btnConfirmar.disabled = true;
    btnAnterior.disabled  = true;
    btnConfirmar.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span> Enviando...';

    try {
      const r = await fetch(RC.url('/api/turnos/crear/'), {
        method:  'POST',
        headers: { 'Content-Type': 'application/json' },
        body:    JSON.stringify({
          tramite, nombre, dni, email, telefono, direccion,
          fecha, hora: horario,
        }),
      });
      const data = await r.json().catch(() => ({ error: 'Error del servidor. Intentá de nuevo.' }));

      if (!r.ok || data.error) {
        this.mostrarError('error-fecha', data.error || 'No se pudo registrar el turno.');
        restaurarBoton();
        // Si el horario se ocupó mientras tanto, refrescamos la lista
        if (/horario/i.test(data.error || '')) this.generarHorarios();
        return;
      }

      // Mostrar confirmación
      document.getElementById('conf-email').textContent      = email;
      document.getElementById('conf-tramite').textContent    = this.tramiteLabels[tramite] || tramite;
      document.getElementById('conf-fecha-hora').textContent =
        `${this.formatearFecha(fecha)} – ${horario} hs. · Nº ${data.numero_turno}`;

      for (let i = 1; i <= 3; i++) {
        const p = document.getElementById(`turno-paso-${i}`);
        if (p) p.style.display = 'none';
      }
      document.getElementById('turno-paso-4').style.display = 'block';
      document.getElementById('turno-footer').style.display = 'none';

      for (let i = 1; i <= 3; i++) {
        const circle = document.querySelector(`#step-ind-${i} .step-circle`);
        if (circle) circle.className = 'step-circle done';
      }
      restaurarBoton();

    } catch (e) {
      this.mostrarError('error-fecha', 'Error de conexión. Reintentá.');
      restaurarBoton();
    }
  },

  // ── Resetear modal ──
  resetear() {
    this.pasoActual = 1;
    this.enviando   = false;
    document.querySelectorAll('input[name="turno-tramite"]').forEach(r => r.checked = false);
    ['turno-nombre','turno-dni','turno-email','turno-telefono','turno-direccion','turno-fecha'].forEach(id => {
      const el = document.getElementById(id);
      if (el) el.value = '';
    });
    Object.keys(this.reglas).forEach(id => this.marcarCampo(id, ''));
    ['error-tramite','error-datos','error-fecha'].forEach(id => this.ocultarError(id));

    const inputFecha = document.getElementById('turno-fecha');
    if (inputFecha) inputFecha.min = this.hoyLocal();
    const selectH = document.getElementById('turno-horario');
    if (selectH) selectH.innerHTML = '<option value="">Seleccioná un horario</option>';
    document.getElementById('turno-resumen').style.display  = 'none';
    document.getElementById('turno-paso-4').style.display   = 'none';
    document.getElementById('turno-footer').style.display   = 'flex';

    for (let i = 1; i <= 4; i++) {
      const p = document.getElementById(`turno-paso-${i}`);
      if (p) p.style.display = i === 1 ? 'block' : 'none';
    }
    this.mostrarPaso();
  }
};

// Funciones globales para los onclick del HTML
function turnoSiguiente() { ModTurnos.siguiente(); }
function turnoAnterior()  { ModTurnos.anterior();  }

// Inicializar cuando carga la página
document.addEventListener('DOMContentLoaded', () => ModTurnos.init());
