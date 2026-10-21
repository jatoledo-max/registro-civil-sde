/**
 * admin.js — Panel Administrativo | Registro Civil Santiago del Estero
 * Maneja turnos, usuarios, noticias, sedes, trámites y actividad vía API Django.
 * El inicio de sesión lo resuelve Django (login.html); acá no hay credenciales.
 */

'use strict';

/* ════════════════════════════════════════════════
   5. TOAST NOTIFICATIONS
   ════════════════════════════════════════════════ */

const Toast = {
  show(msg, type = 'success') {
    const icons = { success: 'bi-check-circle-fill', error: 'bi-x-circle-fill', warning: 'bi-exclamation-triangle-fill', info: 'bi-info-circle-fill' };
    const container = document.getElementById('adm-toast-container');
    if (!container) return;

    const el = document.createElement('div');
    el.className = `adm-toast ${type}`;
    el.innerHTML = `<i class="bi ${icons[type] || icons.info}"></i><span></span>`;
    el.querySelector('span').textContent = msg;
    container.appendChild(el);

    setTimeout(() => {
      el.style.animation = 'none';
      el.style.opacity   = '0';
      el.style.transform = 'translateX(20px)';
      el.style.transition = 'all .3s ease';
      setTimeout(() => el.remove(), 300);
    }, 3000);
  }
};

/* ── Validaciones comunes de formularios (mismas reglas que el backend) ── */
const Validar = {
  email:  v => /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(v),
  dni:    v => /^\d{7,8}$/.test(v),
  nombre: v => v.length >= 3 && v.length <= 100 && /^[A-Za-zÁÉÍÓÚÜÑáéíóúüñ' .-]+$/.test(v),
  telefono: v => /^\+?[\d\s()-]+$/.test(v) && v.replace(/\D/g, '').length >= 10 && v.replace(/\D/g, '').length <= 13,
  slug:   v => /^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(v),
};

/* ════════════════════════════════════════════════
  6. NAVEGACIÓN (sidebar)
   ════════════════════════════════════════════════ */

function initNav() {
  document.querySelectorAll('.adm-nav-item[data-section]').forEach(item => {
    item.addEventListener('click', () => {
      const target = item.dataset.section;

      // Activar ítem del sidebar
      document.querySelectorAll('.adm-nav-item').forEach(i => i.classList.remove('active'));
      item.classList.add('active');

      // Mostrar sección correspondiente
      document.querySelectorAll('.adm-section').forEach(s => s.classList.remove('active'));
      const sec = document.getElementById(`sec-${target}`);
      if (sec) sec.classList.add('active');

      // Inicializar módulo al activar sección
      if (target === 'tramites-panel') ModTramites.init();
      if (target === 'sedes')          ModSedes.init();
      if (target === 'usuarios')       ModUsuarios.init();
      if (target === 'noticias')       ModNoticias.init();
      if (target === 'actividad')      ModActividad.init();

      // Cerrar sidebar y overlay en mobile — delegado a cerrarSidebar()
      if (typeof cerrarSidebar === 'function') cerrarSidebar();
    });
  });
  // El toggle del hamburguesa lo maneja toggleAdmSidebar() desde el HTML
}

/* ════════════════════════════════════════════════
  7. MÓDULO TURNOS
   ════════════════════════════════════════════════ */
const ModTurnos = {

  async cargar() {
    const r    = await fetch(RC.url('/api/turnos/'));
    const data = await r.json();
    return data.turnos || [];
  },

  estadoBadge(estado) {
    const map = {
      'pendiente':  'badge-pendiente',
      'asistio':    'badge-asistio',
      'no_asistio': 'badge-noasistio',
      'cancelado':  'badge-cancelado',
    };
    const labels = {
      'pendiente':  'Pendiente',
      'asistio':    'Asistió',
      'no_asistio': 'No asistió',
      'cancelado':  'Cancelado',
    };
    return `<span class="badge-estado ${map[estado] || ''}">${labels[estado] || estado}</span>`;
  },

  origenBadge(origen) {
    if (origen === 'manual') {
      return `<span class="badge-estado badge-admin" title="Cargado por empleado">
                <i class="bi bi-person-fill me-1"></i>Manual
              </span>`;
    }
    return `<span class="badge-estado badge-operador" title="Solicitado por el ciudadano">
              <i class="bi bi-globe me-1"></i>Sistema
            </span>`;
  },

render(turnos) {
  const tbody = document.getElementById('turnos-tbody');
  if (!tbody) return;

  // Stats — IDs que coinciden con el HTML
  const statTotal   = document.getElementById('stat-total-turnos');
  const statPend    = document.getElementById('stat-pendientes');
  const statAsistio = document.getElementById('stat-asistio');
  const statCancel  = document.getElementById('stat-cancelado');
  const badge       = document.getElementById('nav-badge-turnos');

  if (statTotal)   statTotal.innerText   = turnos.length;
  if (statPend)    statPend.innerText    = turnos.filter(t => t.estado === 'pendiente').length;
  if (statAsistio) statAsistio.innerText = turnos.filter(t => t.estado === 'asistio').length;
  if (statCancel)  statCancel.innerText  = turnos.filter(t => t.estado === 'no_asistio' || t.estado === 'cancelado').length;
  if (badge)       badge.textContent     = turnos.filter(t => t.estado === 'pendiente').length;

  this.renderTabla(turnos, tbody);
  this.aplicarFiltros(turnos);
},

  renderTabla(turnos, tbody) {
    if (turnos.length === 0) {
      tbody.innerHTML = `<tr><td colspan="9" class="text-center py-4 text-muted">No hay turnos registrados.</td></tr>`;
      return;
    }

    tbody.innerHTML = turnos.map(t => `
      <tr>
        <td><strong>${t.numero_turno}</strong></td>
        <td>${t.fecha}</td>
        <td>${t.hora}</td>
        <td>${t.nombre}<br/><small style="color:#888;">${t.dni}</small></td>
        <td><small>${t.tramite}</small>${t.sede ? `<br/><small style="color:#888;"><i class="bi bi-geo-alt"></i> ${t.sede}</small>` : ''}</td>
        <td>${this.origenBadge(t.origen)}</td>
        <td>${this.estadoBadge(t.estado)}</td>
        <td>
          <select class="estado-select" onchange="ModTurnos.cambiarEstado(${t.id}, this.value)">
            <option value="pendiente"  ${t.estado === 'pendiente'  ? 'selected' : ''}>Pendiente</option>
            <option value="asistio"    ${t.estado === 'asistio'    ? 'selected' : ''}>Asistió</option>
            <option value="no_asistio" ${t.estado === 'no_asistio' ? 'selected' : ''}>No asistió</option>
            <option value="cancelado"  ${t.estado === 'cancelado'  ? 'selected' : ''}>Cancelado</option>
          </select>
        </td>
        <td style="text-align:center;">
          <button
            class="btn-adm-icon edit"
            title="Reprogramar turno"
            onclick="ModTurnos.openModalReprogramar(${JSON.stringify(t).replace(/"/g, '&quot;')})"
            style="padding:4px 8px;">
            <i class="bi bi-calendar2-week"></i>
          </button>
        </td>
      </tr>
    `).join('');
  },

aplicarFiltros(turnos) {
  const filtroNombre  = document.getElementById('filtro-turno');
  const filtroTramite = document.getElementById('filtro-tramite');
  const tbody         = document.getElementById('turnos-tbody');

  const filtrar = () => {
    const texto   = filtroNombre?.value.toLowerCase() || '';
    const tramite = filtroTramite?.value || '';

    const filtrados = turnos.filter(t => {
      const coincideTexto   = !texto ||
        t.nombre.toLowerCase().includes(texto) ||
        t.dni.includes(texto) ||
        t.numero_turno.toLowerCase().includes(texto);
      const coincideTramite = !tramite || t.tramite_slug === tramite;
      return coincideTexto && coincideTramite;
    });

    this.renderTabla(filtrados, tbody);
  };

  filtroNombre?.addEventListener('input',  filtrar);
  filtroTramite?.addEventListener('change', filtrar);
},

  async cambiarEstado(id, estado) {
    try {
      const r    = await fetch(RC.url(`/api/turnos/${id}/estado/`), {
        method:  'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken':  this.getCookie(RC.csrfCookie),
        },
        body: JSON.stringify({ estado }),
      });
      const data = await r.json();

      if (data.error) { Toast.show(data.error, 'error'); return; }
      Toast.show('Estado actualizado.', 'success');
      await this.init();

    } catch { Toast.show('Error al cambiar estado.', 'error'); }
  },

  getCookie(name) {
    const value = `; ${document.cookie}`;
    const parts = value.split(`; ${name}=`);
    if (parts.length === 2) return parts.pop().split(';').shift();
  },

async init() {
  const btnNuevo = document.getElementById('btn-nuevo-turno');
  if (btnNuevo) btnNuevo.onclick = () => this.openModal();

  const turnos = await this.cargar();
  this.render(turnos);
},

openModal(turno = null) {
  const modal = document.getElementById('modal-turno');
  if (!modal) return;
  // Resetear form si existe
  const form = document.getElementById('form-turno');
  if (form) form.reset();
  new bootstrap.Modal(modal).show();
},

openModal(turno = null) {
  const form  = document.getElementById('form-turno');
  const titulo = document.getElementById('modal-turno-titulo');
  if (!form) return;

  form.reset();
  form['turno-id'].value = '';
  titulo.textContent = 'Nuevo Turno Manual';

  // Fecha mínima = hoy
  const fechaInput = document.getElementById('adm-turno-fecha');
  if (fechaInput) {
    const hoy = new Date().toISOString().split('T')[0];
    fechaInput.min = hoy;
    fechaInput.onchange = () => ModTurnos.cargarHorarios();
  }

  // Al cambiar de sede se recalculan los horarios disponibles
  const selectSede = document.getElementById('adm-turno-sede');
  if (selectSede) selectSede.onchange = () => ModTurnos.cargarHorarios();

  // Reset horarios
  const selectHora = document.getElementById('adm-turno-hora');
  if (selectHora) selectHora.innerHTML = '<option value="">Seleccioná una fecha primero</option>';

  new bootstrap.Modal(document.getElementById('modal-turno')).show();
},

async cargarHorarios() {
  const fecha     = document.getElementById('adm-turno-fecha').value;
  const selectH   = document.getElementById('adm-turno-hora');
  const aviso     = document.getElementById('adm-fecha-aviso');
  const avisoMsg  = document.getElementById('adm-fecha-aviso-msg');
  if (!fecha || !selectH) return;

  selectH.innerHTML = '<option value="">Cargando...</option>';
  aviso.style.display = 'none';

  const sedeId = document.getElementById('adm-turno-sede')?.value || '';

  try {
    const r    = await fetch(RC.url(`/api/turnos/disponibilidad/?fecha=${encodeURIComponent(fecha)}&sede=${encodeURIComponent(sedeId)}`));
    const data = await r.json();

    selectH.innerHTML = '<option value="">Seleccioná un horario</option>';

    if (!data.habil) {
      aviso.style.display = 'block';
      avisoMsg.textContent = 'Este día no es hábil (feriado o fin de semana).';
      selectH.innerHTML = '<option value="">No hay turnos este día</option>';
      return;
    }

    if (!data.habil_dia) {
      aviso.style.display = 'block';
      avisoMsg.textContent = 'Este día ya no tiene más turnos disponibles (máximo 20).';
      return;
    }

    data.slots.forEach(slot => {
      const opt = document.createElement('option');
      opt.value = slot.hora;
      opt.textContent = slot.lleno
        ? `${slot.hora} hs. — Sin disponibilidad`
        : `${slot.hora} hs.`;
      opt.disabled = slot.lleno;
      selectH.appendChild(opt);
    });

  } catch {
    selectH.innerHTML = '<option value="">Error al cargar horarios</option>';
  }
},

openModalReprogramar(turno) {
  const form = document.getElementById('form-reprogramar');
  if (!form) return;

  form.reset();
  form['reprog-turno-id'].value = turno.id;
  this.reprogSedeId = turno.sede_id || '';

  // Info del turno actual
  document.getElementById('reprog-info-nombre').textContent  = turno.nombre;
  document.getElementById('reprog-info-tramite').textContent = turno.tramite;
  document.querySelector('#reprog-info-actual span').textContent =
    `${turno.fecha} a las ${turno.hora} hs.`;

  // Fecha mínima = hoy
  const fechaInput = document.getElementById('reprog-fecha');
  if (fechaInput) {
    const hoy = new Date().toISOString().split('T')[0];
    fechaInput.min = hoy;
    fechaInput.onchange = () => ModTurnos.cargarHorariosReprogramar();
  }

  // Reset hora select y aviso
  const selectH = document.getElementById('reprog-hora');
  if (selectH) selectH.innerHTML = '<option value="">Seleccioná una fecha primero</option>';
  const aviso = document.getElementById('reprog-fecha-aviso');
  if (aviso) aviso.style.display = 'none';

  // Botón confirmar
  const btnConfirmar = document.getElementById('btn-confirmar-reprogramar');
  if (btnConfirmar) btnConfirmar.onclick = () => ModTurnos.handleReprogramarSave();

  new bootstrap.Modal(document.getElementById('modal-reprogramar')).show();
},

async cargarHorariosReprogramar() {
  const fecha   = document.getElementById('reprog-fecha').value;
  const selectH = document.getElementById('reprog-hora');
  const aviso   = document.getElementById('reprog-fecha-aviso');
  if (!fecha || !selectH) return;

  selectH.innerHTML = '<option value="">Cargando...</option>';
  if (aviso) aviso.style.display = 'none';

  try {
    const sede = this.reprogSedeId ? `&sede=${encodeURIComponent(this.reprogSedeId)}` : '';
    const r    = await fetch(RC.url(`/api/turnos/disponibilidad/?fecha=${encodeURIComponent(fecha)}${sede}`));
    const data = await r.json();

    selectH.innerHTML = '<option value="">Seleccioná un horario</option>';

    if (!data.habil) {
      if (aviso) {
        aviso.style.display = 'block';
        aviso.textContent = 'Este día no es hábil (feriado o fin de semana).';
      }
      selectH.innerHTML = '<option value="">No hay turnos este día</option>';
      return;
    }

    data.slots.forEach(slot => {
      const opt = document.createElement('option');
      opt.value = slot.hora;
      opt.textContent = slot.lleno
        ? `${slot.hora} hs. — Sin disponibilidad`
        : `${slot.hora} hs.`;
      opt.disabled = slot.lleno;
      selectH.appendChild(opt);
    });

  } catch {
    selectH.innerHTML = '<option value="">Error al cargar horarios</option>';
  }
},

async handleReprogramarSave() {
  const form = document.getElementById('form-reprogramar');
  if (!form) return;

  const id    = form['reprog-turno-id'].value;
  const fecha = document.getElementById('reprog-fecha').value;
  const hora  = document.getElementById('reprog-hora').value;

  if (!fecha || !hora) {
    Toast.show('Seleccioná fecha y horario.', 'error');
    return;
  }

  try {
    const r = await fetch(RC.url(`/api/turnos/${id}/reprogramar/`), {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken':  this.getCookie(RC.csrfCookie),
      },
      body: JSON.stringify({ fecha, hora }),
    });
    const data = await r.json();

    if (data.error) { Toast.show(data.error, 'error'); return; }

    bootstrap.Modal.getInstance(document.getElementById('modal-reprogramar'))?.hide();
    Toast.show('Turno reprogramado. Se notificó al ciudadano por correo.', 'success');
    await this.init();

  } catch { Toast.show('Error al reprogramar turno.', 'error'); }
},

async handleFormSave() {
  const form = document.getElementById('form-turno');
  if (!form) return;

  const tramite   = form['turno-tramite'].value;
  const fecha     = form['turno-fecha'].value;
  const hora      = form['turno-hora'].value;
  const nombre    = form['turno-nombre'].value.trim();
  const dni       = form['turno-dni'].value.trim();
  const email     = form['turno-email'].value.trim();
  const telefono  = form['turno-telefono']?.value.trim() || '';
  const estado    = form['turno-estado'].value;
  const sedeId    = form['turno-sede']?.value || '';

  if (!sedeId) { Toast.show('Seleccioná la sede de atención.', 'error'); return; }
  if (!tramite || !fecha || !hora || !nombre || !dni || !email) {
    Toast.show('Completá todos los campos obligatorios.', 'error');
    return;
  }
  if (!Validar.nombre(nombre) || nombre.split(/\s+/).length < 2) { Toast.show('Ingresá nombre y apellido válidos (solo letras).', 'error'); return; }
  if (!Validar.dni(dni.replace(/\./g, ''))) { Toast.show('El DNI debe tener 7 u 8 dígitos.', 'error'); return; }
  if (!Validar.email(email)) { Toast.show('Ingresá un email válido.', 'error'); return; }
  if (telefono && !Validar.telefono(telefono)) { Toast.show('El teléfono debe incluir código de área (10 dígitos).', 'error'); return; }

  try {
    const r    = await fetch(RC.url('/api/turnos/crear/'), {
      method:  'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken':  this.getCookie(RC.csrfCookie),
      },
      body: JSON.stringify({
        tramite, fecha, hora, nombre, dni, email,
        telefono,
        origen: 'manual',
        estado,
        sede_id: sedeId,
      }),
    });
    const data = await r.json();

    if (data.error) { Toast.show(data.error, 'error'); return; }

    bootstrap.Modal.getInstance(document.getElementById('modal-turno'))?.hide();
    Toast.show(`Turno ${data.numero_turno} creado correctamente.`, 'success');
    await this.init();

  } catch { Toast.show('Error al guardar turno.', 'error'); }
},

};

/* ════════════════════════════════════════════════
  8. MÓDULO USUARIOS
   ════════════════════════════════════════════════ */

const ModUsuarios = {
  async cargar() {
    const r = await fetch(RC.url('/api/usuarios/'));
    const data = await r.json();
    return data.usuarios || [];
  },

  render(usuarios) {
    const tbody = document.getElementById('usuarios-tbody');
    if (!tbody) return;

    const stat = document.getElementById('stat-total-usuarios');
    if (stat) stat.innerText = usuarios.length;

    if (usuarios.length === 0) {
      tbody.innerHTML = `<tr><td colspan="5" class="text-center py-4 text-muted">No hay usuarios registrados.</td></tr>`;
      return;
    }

    tbody.innerHTML = usuarios.map(u => `
      <tr data-uid="${u.id}">
        <td><strong>${u.nombre}</strong></td>
        <td>${u.email}</td>
        <td><span class="badge-estado ${u.rol === 'super_admin' ? 'badge-admin' : 'badge-operador'}">
          ${u.rol === 'super_admin' ? 'Super Admin' : 'Operador'}
        </span></td>
        <td><span class="badge-estado ${u.activo ? 'badge-asistio' : 'badge-noasistio'}">
          ${u.activo ? 'Activo' : 'Inactivo'}
        </span></td>
        <td>
          <button class="btn-adm-icon edit" data-edit-user="${u.id}"
            data-nombre="${u.nombre}" data-email="${u.email}" data-rol="${u.rol}" title="Editar">
            <i class="bi bi-pencil-square"></i>
          </button>
          <button class="btn-adm-icon trash" data-toggle-user="${u.id}" data-activo="${u.activo}" title="${u.activo ? 'Desactivar' : 'Activar'}">
            <i class="bi bi-${u.activo ? 'person-slash' : 'person-check'}"></i>
          </button>
        </td>
      </tr>`).join('');

    // Botón editar
    tbody.querySelectorAll('[data-edit-user]').forEach(btn => {
      btn.addEventListener('click', () => {
        this.openModal({
          id:btn.dataset.editUser,
          nombre:btn.dataset.nombre,
          email:btn.dataset.email,
          rol:btn.dataset.rol,
        });
      });
    });

    // Botón activar/desactivar
    tbody.querySelectorAll('[data-toggle-user]').forEach(btn => {
      btn.addEventListener('click', () => {
        const id = btn.dataset.toggleUser;
        const activo = btn.dataset.activo === 'true';
        this.toggleEstado(id, activo);
      });
    });
  },

  openModal(usuario = null) {
    const titulo = document.getElementById('modal-user-titulo');
    const form = document.getElementById('form-usuario');
    const passHelp = document.getElementById('pass-help');
    if (!form) return;

    if (usuario) {
      titulo.textContent  ='Editar Usuario';
      form['user-id'].value =usuario.id;
      form['user-nombre'].value =usuario.nombre;
      form['user-email'].value =usuario.email;
      form['user-rol'].value =usuario.rol;
      form['user-pass'].value = '';
      form['user-pass'].placeholder = 'Dejar vacío para no cambiar';
      if (passHelp) passHelp.textContent = 'Dejá vacío para mantener la contraseña actual.';
    } else {
      titulo.textContent = 'Nuevo Usuario';
      form.reset();
      form['user-id'].value = '';
      form['user-pass'].placeholder = 'Contraseña';
      if (passHelp) passHelp.textContent = 'Requerida para nuevos usuarios.';
    }

    new bootstrap.Modal(document.getElementById('modal-usuario')).show();
  },

  async handleFormSave() {
    const form   = document.getElementById('form-usuario');
    if (!form) return;

    const id = form['user-id'].value;
    const nombre = form['user-nombre'].value.trim();
    const email = form['user-email'].value.trim();
    const rol = form['user-rol'].value;
    const password = form['user-pass'].value.trim();

    if (!nombre || !email) { Toast.show('Nombre y email son requeridos', 'error'); return; }
    if (!Validar.nombre(nombre)) { Toast.show('El nombre solo puede contener letras (3 a 100 caracteres).', 'error'); return; }
    if (!Validar.email(email))   { Toast.show('Ingresá un email válido.', 'error'); return; }
    if (!id && !password)  { Toast.show('La contraseña es requerida para nuevos usuarios', 'error'); return; }
    if (password && (password.length < 8 || /^\d+$/.test(password))) {
      Toast.show('La contraseña debe tener al menos 8 caracteres y no ser solo números.', 'error'); return;
    }

    const url = RC.url(id ? `/api/usuarios/${id}/editar/` : '/api/usuarios/crear/');
    const body = { nombre, email, rol };
    if (password) body.password = password;

    try {
      const r = await fetch(url, {
        method:'POST',
        headers: {
          'Content-Type':'application/json',
          'X-CSRFToken':this.getCookie(RC.csrfCookie),
        },
        body:JSON.stringify(body),
      });
      const data = await r.json();

      if (data.error) { Toast.show(data.error, 'error'); return; }

      bootstrap.Modal.getInstance(document.getElementById('modal-usuario'))?.hide();
      Toast.show(id ? 'Usuario actualizado correctamente' : 'Usuario creado correctamente', 'success');
      await this.init();

    } catch { Toast.show('Error al guardar usuario.', 'error'); }
  },

  async toggleEstado(id, activo) {
    const accion = activo ? 'desactivar' : 'reactivar';
    if (!confirm(`¿Querés ${accion} este usuario?`)) return;

    try {
      const r = await fetch(RC.url(`/api/usuarios/${id}/desactivar/`), {
        method:'POST',
        headers: { 'X-CSRFToken': this.getCookie(RC.csrfCookie) },
      });
      const data = await r.json();

      if (data.error) { Toast.show(data.error, 'error'); return; }
      Toast.show(`Usuario ${data.estado} correctamente.`, 'success');
      await this.init();

    } catch { Toast.show('Error al cambiar estado.', 'error'); }
  },

  getCookie(name) {
    const value = `; ${document.cookie}`;
    const parts = value.split(`; ${name}=`);
    if (parts.length === 2) return parts.pop().split(';').shift();
  },

async init() {
    const btnNuevo   = document.getElementById('btn-nuevo-usuario');
    const btnGuardar = document.getElementById('btn-guardar-usuario');

    // onclick reemplaza el handler anterior, no lo acumula
    if (btnNuevo)   btnNuevo.onclick   = () => this.openModal();
    if (btnGuardar) btnGuardar.onclick = () => this.handleFormSave();

    const usuarios = await this.cargar();
    this.render(usuarios);

    const badge = document.getElementById('nav-badge-usuarios');
    if (badge) badge.textContent = usuarios.length;
  }
};

/* ════════════════════════════════════════════════
  9. MÓDULO NOTICIAS
   ════════════════════════════════════════════════ */

const ModNoticias = {
  _cache: [],

  async cargar() {
    const r    = await fetch(RC.url('/api/noticias/'));
    const data = await r.json();
    if (!r.ok) throw new Error(data.error || 'Error al cargar noticias');
    return data.noticias || [];
  },

  estadoBadge(estado) {
    const map = {
      borrador:  { cls: 'badge-pendiente',  label: 'Borrador' },
      revision:  { cls: 'badge-operador',   label: 'En revisión' },
      publicada: { cls: 'badge-asistio',    label: 'Publicada' },
      archivada: { cls: 'badge-noasistio',  label: 'Archivada' },
    };
    const e = map[estado] || { cls: '', label: estado };
    return `<span class="badge-estado ${e.cls}">${e.label}</span>`;
  },

  render(noticias) {
    this._cache = noticias;
    const grid = document.getElementById('noticias-admin-grid');
    if (!grid) return;

    const stat = document.getElementById('stat-total-noticias');
    const badge = document.getElementById('nav-badge-noticias');
    const publicadas = noticias.filter(n => n.estado === 'publicada').length;

    if (stat) stat.innerText = publicadas;
    if (badge) badge.textContent = noticias.length;

    if (noticias.length === 0) {
      grid.innerHTML = `<div class="col-12"><div class="adm-empty"><i class="bi bi-newspaper"></i><p>No hay noticias. Creá una nueva.</p></div></div>`;
      return;
    }

    grid.innerHTML = noticias.map(n => {
      const preview = n.cuerpo.length > 90 ? `${n.cuerpo.substring(0, 90)}…` : n.cuerpo;
      const thumb = n.imagen
        ? `<img src="${n.imagen}" alt="">`
        : `<i class="bi bi-newspaper"></i>`;

      return `
      <div class="col-12 col-md-6 col-lg-4">
        <div class="adm-noticia-card">
          <div class="adm-noticia-thumb">${thumb}</div>
          <div class="adm-noticia-body">
            <span class="adm-noticia-tag">${n.tag || 'General'}</span>
            <div class="adm-noticia-titulo">${n.titulo}</div>
            <div class="adm-noticia-fecha"><i class="bi bi-calendar3"></i> ${n.fecha}</div>
            <div class="mb-2">${this.estadoBadge(n.estado)}</div>
            <div class="adm-noticia-cuerpo-preview">${preview}</div>
            <div class="adm-noticia-actions">
              <button class="btn-adm-icon edit" data-edit-noticia="${n.id}" title="Editar">
                <i class="bi bi-pencil-square"></i>
              </button>
              <button class="btn-adm-icon trash" data-delete-noticia="${n.id}" title="Eliminar">
                <i class="bi bi-trash3"></i>
              </button>
            </div>
          </div>
        </div>
      </div>`;
    }).join('');

    grid.querySelectorAll('[data-edit-noticia]').forEach(btn => {
      btn.addEventListener('click', () => {
        const n = this._cache.find(x => x.id === parseInt(btn.dataset.editNoticia, 10));
        if (n) this.openModal(n);
      });
    });

    grid.querySelectorAll('[data-delete-noticia]').forEach(btn => {
      btn.addEventListener('click', () => this.eliminar(parseInt(btn.dataset.deleteNoticia, 10)));
    });
  },

  openModal(noticia = null) {
    const titulo  = document.getElementById('modal-noticia-titulo');
    const form    = document.getElementById('form-noticia');
    const preview = document.getElementById('noticia-imagen-preview');
    if (!form) return;

    form.reset();
    if (preview) preview.style.display = 'none';

    if (noticia) {
      titulo.textContent = 'Editar Noticia';
      form['noticia-id'].value     = noticia.id;
      form['noticia-titulo'].value = noticia.titulo;
      form['noticia-tag'].value    = noticia.tag || 'General';
      form['noticia-estado'].value = noticia.estado || 'borrador';
      form['noticia-cuerpo'].value = noticia.cuerpo;

      if (noticia.imagen && preview) {
        preview.querySelector('img').src = noticia.imagen;
        preview.style.display = 'block';
      }
    } else {
      titulo.textContent = 'Nueva Noticia';
      form['noticia-id'].value       = '';
      form['noticia-estado'].value   = 'borrador';
    }

    new bootstrap.Modal(document.getElementById('modal-noticia-form')).show();
  },

  async handleFormSave() {
    const form = document.getElementById('form-noticia');
    if (!form) return;

    const id     = form['noticia-id'].value;
    const titulo = form['noticia-titulo'].value.trim();
    const cuerpo = form['noticia-cuerpo'].value.trim();
    const tag    = form['noticia-tag'].value;
    const estado = form['noticia-estado'].value;
    const imagen = form['noticia-imagen']?.files?.[0];

    if (!titulo || !cuerpo) {
      Toast.show('Título y contenido son requeridos', 'error');
      return;
    }
    if (titulo.length > 200) { Toast.show('El título no puede superar los 200 caracteres.', 'error'); return; }
    if (imagen) {
      if (!['image/jpeg', 'image/png', 'image/webp', 'image/gif'].includes(imagen.type)) {
        Toast.show('La imagen debe ser JPG, PNG, WEBP o GIF.', 'error'); return;
      }
      if (imagen.size > 5 * 1024 * 1024) { Toast.show('La imagen no puede superar los 5 MB.', 'error'); return; }
    }

    const formData = new FormData();
    formData.append('titulo', titulo);
    formData.append('cuerpo', cuerpo);
    formData.append('tag', tag);
    formData.append('estado', estado);
    if (imagen) formData.append('imagen', imagen);

    const url = RC.url(id ? `/api/noticias/${id}/editar/` : '/api/noticias/crear/');

    try {
      const r = await fetch(url, {
        method: 'POST',
        headers: { 'X-CSRFToken': this.getCookie(RC.csrfCookie) },
        body: formData,
      });
      const data = await r.json();

      if (data.error) { Toast.show(data.error, 'error'); return; }

      bootstrap.Modal.getInstance(document.getElementById('modal-noticia-form'))?.hide();
      Toast.show(id ? 'Noticia actualizada correctamente' : 'Noticia creada correctamente', 'success');
      await this.init();
    } catch {
      Toast.show('Error al guardar noticia.', 'error');
    }
  },

  async eliminar(id) {
    if (!confirm('¿Eliminar esta noticia? Esta acción no se puede deshacer.')) return;

    try {
      const r = await fetch(RC.url(`/api/noticias/${id}/eliminar/`), {
        method: 'POST',
        headers: { 'X-CSRFToken': this.getCookie(RC.csrfCookie) },
      });
      const data = await r.json();

      if (data.error) { Toast.show(data.error, 'error'); return; }
      Toast.show('Noticia eliminada', 'warning');
      await this.init();
    } catch {
      Toast.show('Error al eliminar noticia.', 'error');
    }
  },

  getCookie(name) {
    const value = `; ${document.cookie}`;
    const parts = value.split(`; ${name}=`);
    if (parts.length === 2) return parts.pop().split(';').shift();
  },

  async init() {
    const btnNueva   = document.getElementById('btn-nueva-noticia');
    const btnGuardar = document.getElementById('btn-guardar-noticia');

    if (btnNueva)   btnNueva.onclick   = () => this.openModal();
    if (btnGuardar) btnGuardar.onclick = () => this.handleFormSave();

    const inputImagen = document.querySelector('[name="noticia-imagen"]');
    if (inputImagen && !inputImagen.dataset.bound) {
      inputImagen.dataset.bound = '1';
      inputImagen.addEventListener('change', () => {
        const preview = document.getElementById('noticia-imagen-preview');
        if (!preview || !inputImagen.files?.[0]) return;
        preview.querySelector('img').src = URL.createObjectURL(inputImagen.files[0]);
        preview.style.display = 'block';
      });
    }

    try {
      const noticias = await this.cargar();
      this.render(noticias);
    } catch {
      Toast.show('Error al cargar noticias.', 'error');
    }
  }
};

/* ════════════════════════════════════════════════
  10. MÓDULO TRÁMITES
   ════════════════════════════════════════════════ */
const ModTramites = {

  async cargar() {
    const r    = await fetch(RC.url('/api/tramites/'));
    const data = await r.json();
    return data.tramites || [];
  },

  async cargarCategorias() {
    const r    = await fetch(RC.url('/api/categorias/'));
    const data = await r.json();
    return data.categorias || [];
  },

  estadoBadge(estado) {
    const map = {
      'borrador':  'badge-cancelado',
      'revision':  'badge-pendiente',
      'publicado': 'badge-asistio',
      'archivado': 'badge-noasistio',
    };
    const labels = {
      'borrador':  'Borrador',
      'revision':  'En revisión',
      'publicado': 'Publicado',
      'archivado': 'Archivado',
    };
    return `<span class="badge-estado ${map[estado] || ''}">${labels[estado] || estado}</span>`;
  },

  render(tramites) {
    const tbody = document.getElementById('tbody-tramites-panel');
    if (!tbody) return;

    const statTotal      = document.getElementById('stat-total-tramites-panel');
    const statPublicados = document.getElementById('stat-tramites-publicados');
    const statPendientes = document.getElementById('stat-tramites-pendientes');
    const badge          = document.getElementById('nav-badge-tramites-panel');

    if (statTotal)      statTotal.innerText      = tramites.length;
    if (statPublicados) statPublicados.innerText  = tramites.filter(t => t.estado === 'publicado').length;
    if (statPendientes) statPendientes.innerText  = tramites.filter(t => t.estado === 'revision').length;
    if (badge)          badge.textContent         = tramites.length;

    this.renderTabla(tramites, tbody);
    this.aplicarFiltros(tramites);
  },

  renderTabla(tramites, tbody) {
    if (tramites.length === 0) {
      tbody.innerHTML = `<tr><td colspan="6" class="text-center py-4 text-muted">No hay trámites registrados.</td></tr>`;
      return;
    }

    tbody.innerHTML = tramites.map(t => `
      <tr>
        <td><strong>${t.nombre}</strong></td>
        <td>${t.categoria}</td>
        <td><code style="font-size:12px;">${t.slug}</code></td>
        <td>${this.estadoBadge(t.estado)}</td>
        <td>${t.creado_por}</td>
        <td>
          <button class="btn-adm-icon edit btn-editar-tramite"
            data-id="${t.id}" data-nombre="${t.nombre}"
            data-categoria="${t.categoria_id || ''}"
            data-slug="${t.slug}" data-icono="${t.icono}"
            data-descripcion="${t.descripcion || ''}"
            data-estado="${t.estado}"
            title="Editar">
            <i class="bi bi-pencil-square"></i>
          </button>
          <button class="btn-adm-icon trash btn-eliminar-tramite"
            data-id="${t.id}" title="Eliminar">
            <i class="bi bi-trash3"></i>
          </button>
        </td>
      </tr>
    `).join('');

    tbody.querySelectorAll('.btn-editar-tramite').forEach(btn => {
      btn.onclick = () => this.openModal({
        id:          btn.dataset.id,
        nombre:      btn.dataset.nombre,
        categoria:   btn.dataset.categoria,
        slug:        btn.dataset.slug,
        icono:       btn.dataset.icono,
        descripcion: btn.dataset.descripcion,
        estado:      btn.dataset.estado,
      });
    });

    tbody.querySelectorAll('.btn-eliminar-tramite').forEach(btn => {
      btn.onclick = () => this.eliminar(btn.dataset.id);
    });
  },

  aplicarFiltros(tramites) {
    const filtroNombre = document.getElementById('filtro-tramite-panel');
    const filtroEstado = document.getElementById('filtro-tramite-estado');
    const tbody        = document.getElementById('tbody-tramites-panel');

    const filtrar = () => {
      const texto  = filtroNombre?.value.toLowerCase() || '';
      const estado = filtroEstado?.value;

      const filtrados = tramites.filter(t => {
        const coincideTexto  = !texto || t.nombre.toLowerCase().includes(texto);
        const coincideEstado = !estado || t.estado === estado;
        return coincideTexto && coincideEstado;
      });

      this.renderTabla(filtrados, tbody);
    };

    filtroNombre?.addEventListener('input',  filtrar);
    filtroEstado?.addEventListener('change', filtrar);
  },

  async openModal(tramite = null) {
    const form   = document.getElementById('form-tramite-panel');
    const titulo = document.getElementById('modal-tramite-panel-titulo');
    if (!form) return;

    // Cargar categorías en el select
    const categorias = await this.cargarCategorias();
    const select     = document.getElementById('select-categoria-tramite');
    select.innerHTML = '<option value="">Seleccionar categoría</option>';
    categorias.forEach(c => {
      const opt      = document.createElement('option');
      opt.value      = c.id;
      opt.textContent = c.nombre;
      select.appendChild(opt);
    });

    if (tramite) {
      titulo.textContent                              = 'Editar Trámite';
      form['tramite-id'].value                        = tramite.id;
      form['tramite-nombre'].value                    = tramite.nombre;
      form['tramite-slug'].value                      = tramite.slug;
      // form['tramite-icono'].value                     = tramite.icono;
      form['tramite-descripcion'].value               = tramite.descripcion || '';
      form['tramite-requisitos'].value                = tramite.requisitos || '';
      form['tramite-como-se-inicia'].value            = tramite.como_se_inicia || '';
      form['tramite-estado'].value                    = tramite.estado;
      if (tramite.categoria) select.value             = tramite.categoria;
      // Deshabilitar slug en edición para no romper URLs
      form['tramite-slug'].disabled = true;
      const gratuito = tramite.es_gratuito;
      document.getElementById('tramite-gratuito').checked = gratuito;
      document.getElementById('precio-wrap').style.display = gratuito ? 'none' : 'block';
      if (!gratuito && tramite.precio) form['tramite-precio'].value = tramite.precio;
      const chkTurno = document.getElementById('tramite-requiere-turno');
      if (chkTurno) chkTurno.checked = !!tramite.requiere_turno;
      const chkPresencial = document.getElementById('tramite-modalidad-presencial');
      const chkDigital    = document.getElementById('tramite-modalidad-digital');
      if (chkPresencial) chkPresencial.checked = !!tramite.modalidad_presencial;
      if (chkDigital)    chkDigital.checked    = !!tramite.modalidad_digital;
    } else {
      titulo.textContent = 'Nuevo Trámite';
      form.reset();
      form['tramite-id'].value      = '';
      form['tramite-slug'].disabled = false;
      // form['tramite-icono'].value   = 'bi-file-earmark-text';
    }

    new bootstrap.Modal(document.getElementById('modal-tramite-panel')).show();
  },

async handleFormSave() {
    const form = document.getElementById('form-tramite-panel');
    if (!form) return;

    const id              = form['tramite-id'].value;
    const nombre          = form['tramite-nombre'].value.trim();
    const slug            = form['tramite-slug'].value.trim();
    const descripcion     = form['tramite-descripcion'].value.trim();
    const requisitos      = form['tramite-requisitos'].value.trim();
    const comoSeInicia    = form['tramite-como-se-inicia'].value.trim();
    const estado          = form['tramite-estado'].value;
    const categoriaId     = document.getElementById('select-categoria-tramite').value;
    const gratuito        = document.getElementById('tramite-gratuito').checked;
    const requiereTurno   = document.getElementById('tramite-requiere-turno')?.checked || false;
    const modPresencial   = document.getElementById('tramite-modalidad-presencial')?.checked || false;
    const modDigital      = document.getElementById('tramite-modalidad-digital')?.checked || false;
    const precio          = gratuito ? null : (form['tramite-precio'].value || null);

    if (!nombre) { Toast.show('El nombre es obligatorio.', 'error'); return; }
    if (nombre.length > 200) { Toast.show('El nombre no puede superar los 200 caracteres.', 'error'); return; }
    if (!id && !slug) { Toast.show('El identificador de URL es obligatorio.', 'error'); return; }
    if (!id && !Validar.slug(slug)) {
      Toast.show('El identificador de URL solo puede tener minúsculas, números y guiones (ej: partida-nacimiento).', 'error'); return;
    }
    if (precio !== null && (isNaN(Number(precio)) || Number(precio) < 0)) {
      Toast.show('El precio debe ser un número mayor o igual a 0.', 'error'); return;
    }

    const url  = RC.url(id ? `/api/tramites/${id}/editar/` : '/api/tramites/crear/');
    const body = {
      nombre, descripcion, estado,
      requisitos,
      como_se_inicia:      comoSeInicia,
      categoria_id:        categoriaId || null,
      es_gratuito:         gratuito,
      requiere_turno:      requiereTurno,
      modalidad_presencial: modPresencial,
      modalidad_digital:    modDigital,
      precio,
    };
    if (!id) body.slug = slug;

    try {
      const r    = await fetch(url, {
        method:  'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken':  this.getCookie(RC.csrfCookie),
        },
        body: JSON.stringify(body),
      });
      const data = await r.json();

      if (data.error) { Toast.show(data.error, 'error'); return; }

      bootstrap.Modal.getInstance(document.getElementById('modal-tramite-panel'))?.hide();
      Toast.show(id ? 'Trámite actualizado.' : 'Trámite creado correctamente.', 'success');
      await this.init();

    } catch { Toast.show('Error al guardar trámite.', 'error'); }
},

  async eliminar(id) {
    if (!confirm('¿Eliminar este trámite? Esta acción no se puede deshacer.')) return;

    try {
      const r    = await fetch(RC.url(`/api/tramites/${id}/eliminar/`), {
        method:  'POST',
        headers: { 'X-CSRFToken': this.getCookie(RC.csrfCookie) },
      });
      const data = await r.json();

      if (data.error) { Toast.show(data.error, 'error'); return; }
      Toast.show('Trámite eliminado.', 'warning');
      await this.init();

    } catch { Toast.show('Error al eliminar trámite.', 'error'); }
  },

  getCookie(name) {
    const value = `; ${document.cookie}`;
    const parts = value.split(`; ${name}=`);
    if (parts.length === 2) return parts.pop().split(';').shift();
  },

  async init() {
    const btnNuevo = document.getElementById('btn-nuevo-tramite-panel');
    if (btnNuevo) btnNuevo.onclick = () => this.openModal();

    const tramites = await this.cargar();
    this.render(tramites);
  }
};

// Botón nueva categoría
const btnNuevaCat     = document.getElementById('btn-nueva-categoria');
const btnConfirmarCat = document.getElementById('btn-confirmar-categoria');
const btnCancelarCat  = document.getElementById('btn-cancelar-categoria');
const wrapNuevaCat    = document.getElementById('nueva-categoria-wrap');

if (btnNuevaCat) btnNuevaCat.onclick = () => {
  wrapNuevaCat.style.display = 'block';
  document.getElementById('nueva-categoria-nombre').focus();
};

if (btnCancelarCat) btnCancelarCat.onclick = () => {
  wrapNuevaCat.style.display = 'none';
  document.getElementById('nueva-categoria-nombre').value = '';
};

if (btnConfirmarCat) btnConfirmarCat.onclick = async () => {
  const nombre = document.getElementById('nueva-categoria-nombre').value.trim();
  const icono  = document.getElementById('nueva-categoria-icono').value;

  if (!nombre) { Toast.show('Escribí el nombre de la categoría.', 'warning'); return; }

  try {
    const r    = await fetch(RC.url('/api/categorias/crear/'), {
      method:  'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken':  ModTramites.getCookie(RC.csrfCookie),
      },
      body: JSON.stringify({ nombre, icono }),
    });
    const data = await r.json();

    if (data.error) { Toast.show(data.error, 'error'); return; }

    // Agregar la nueva categoría al select y seleccionarla
    const opt       = document.createElement('option');
    opt.value       = data.id;
    opt.textContent = data.nombre;
    select.appendChild(opt);
    select.value = data.id;

    // Ocultar el campo
    wrapNuevaCat.style.display = 'none';
    document.getElementById('nueva-categoria-nombre').value = '';
    Toast.show(`Categoría "${data.nombre}" creada.`, 'success');

  } catch { Toast.show('Error al crear categoría.', 'error'); }
};


/* ════════════════════════════════════════════════
  12. MÓDULO SEDES
   ════════════════════════════════════════════════ */
const ModSedes = {

  _cache: [],

  // Límites aproximados de Santiago del Estero (mismos que en sedes/views.py)
  LIMITES: { latMin: -30.5, latMax: -25.0, lngMin: -65.8, lngMax: -61.0 },
  CENTRO_SDE: [-27.7834, -64.2642],

  esc(t) {
    return String(t ?? '').replace(/[&<>"']/g, c =>
      ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  },

  abrirEdicion(id) {
    const sede = this._cache.find(s => s.id === id);
    if (sede) this.openModal(sede);
  },

  async cargar() {
    const r    = await fetch(RC.url('/api/sedes/'));
    const data = await r.json();
    return data.sedes || [];
  },

  fila(s) {
    const mapa = (s.lat != null && s.lng != null)
      ? `<a href="https://www.google.com/maps/search/?api=1&query=${s.lat},${s.lng}" target="_blank" rel="noopener"
            class="badge-estado badge-operador" title="Ver ubicación en Google Maps">
           <i class="bi bi-geo-alt-fill me-1"></i>Ver
         </a>`
      : `<span class="badge-estado badge-pendiente" title="Editá la sede y marcala en el mapa">
           <i class="bi bi-exclamation-triangle me-1"></i>Sin ubicación
         </span>`;
    return `
      <tr data-id="${s.id}">
        <td>
          <strong>${this.esc(s.nombre)}</strong>
          ${s.recibe_turnos_online ? '<span class="badge-turnos-online" title="Recibe los turnos online del sitio"><i class="bi bi-calendar-check"></i>Turnos online</span>' : ''}
        </td>
        <td>${this.esc(s.direccion)}${s.referencia ? `<br/><small style="color:#888;">${this.esc(s.referencia)}</small>` : ''}</td>
        <td>${this.esc(s.departamento)}</td>
        <td>${this.esc(s.horario)}</td>
        <td>
          <span class="badge-estado ${s.activo ? 'badge-asistio' : 'badge-pendiente'}">
            ${s.activo ? 'Activa' : 'Pendiente'}
          </span>
        </td>
        <td>${mapa}</td>
        <td>
          <button class="btn-adm-icon edit" title="Editar" onclick="ModSedes.abrirEdicion(${s.id})">
            <i class="bi bi-pencil-square"></i>
          </button>
          <button class="btn-adm-icon trash" title="Eliminar" onclick="ModSedes.eliminar(${s.id})">
            <i class="bi bi-trash3"></i>
          </button>
        </td>
      </tr>`;
  },

  pintarTabla(sedes, vacio = 'No hay sedes registradas.') {
    const tbody = document.getElementById('tbody-sedes');
    if (!tbody) return;
    tbody.innerHTML = sedes.length
      ? sedes.map(s => this.fila(s)).join('')
      : `<tr><td colspan="7" class="text-center py-4 text-muted">${vacio}</td></tr>`;
  },

  render(sedes) {
    this._cache = sedes;

    const statTotal      = document.getElementById('stat-total-sedes');
    const statActivas    = document.getElementById('stat-sedes-activas');
    const statPendientes = document.getElementById('stat-sedes-pendientes');
    const badge          = document.getElementById('nav-badge-sedes');

    if (statTotal)      statTotal.innerText      = sedes.length;
    if (statActivas)    statActivas.innerText    = sedes.filter(s => s.activo).length;
    if (statPendientes) statPendientes.innerText = sedes.filter(s => !s.activo).length;
    if (badge)          badge.textContent        = sedes.length;

    this.pintarTabla(sedes);
    this.aplicarFiltros();
  },

  aplicarFiltros() {
    const filtroNombre = document.getElementById('filtro-sede');
    const filtroEstado = document.getElementById('filtro-sede-estado');

    const filtrar = () => {
      const texto  = filtroNombre?.value.toLowerCase() || '';
      const estado = filtroEstado?.value || '';
      const filtradas = this._cache.filter(s => {
        const coincideTexto  = !texto || s.nombre.toLowerCase().includes(texto) || s.direccion.toLowerCase().includes(texto);
        const coincideEstado = estado === '' || s.activo.toString() === estado;
        return coincideTexto && coincideEstado;
      });
      this.pintarTabla(filtradas, 'No hay resultados.');
    };

    if (filtroNombre) filtroNombre.oninput  = filtrar;
    if (filtroEstado) filtroEstado.onchange = filtrar;
  },

  openModal(sede = null) {
    const form   = document.getElementById('form-sede');
    const titulo = document.getElementById('modal-sede-titulo');
    if (!form) return;

    form.reset();
    form['sede-provincia'].value = 'Santiago del Estero';
    document.getElementById('sede-map-q').value = '';
    document.getElementById('sede-map-pegar').value = '';
    document.getElementById('sede-map-resultados').classList.remove('show');

    if (sede) {
      titulo.textContent              = 'Editar Sede';
      form['sede-id'].value           = sede.id;
      form['sede-nombre'].value       = sede.nombre;
      form['sede-direccion'].value    = sede.direccion;
      form['sede-referencia'].value   = sede.referencia || '';
      form['sede-departamento'].value = sede.departamento;
      form['sede-horario'].value      = sede.horario;
      if (form['sede-activo'])        form['sede-activo'].value = sede.activo.toString();
      if (form['sede-turnos-online']) form['sede-turnos-online'].checked = !!sede.recibe_turnos_online;
    } else {
      titulo.textContent    = 'Nueva Sede';
      form['sede-id'].value = '';
    }

    const modalEl = document.getElementById('modal-sede');
    // Leaflet necesita que el contenedor sea visible para calcular su tamaño
    modalEl.addEventListener('shown.bs.modal', () => {
      MapaSede.abrir(sede && sede.lat != null ? [sede.lat, sede.lng] : null);
    }, { once: true });

    bootstrap.Modal.getOrCreateInstance(modalEl).show();
  },

  async handleFormSave() {
    const form = document.getElementById('form-sede');
    if (!form) return;

    const id           = form['sede-id'].value;
    const nombre       = form['sede-nombre'].value.trim();
    const direccion    = form['sede-direccion'].value.trim();
    const referencia   = form['sede-referencia'].value.trim();
    const departamento = form['sede-departamento'].value.trim();
    const provincia    = form['sede-provincia'].value.trim();
    const horario      = form['sede-horario'].value.trim();
    const lat          = form['sede-lat'].value;
    const lng          = form['sede-lng'].value;

    if (!nombre || !direccion || !departamento || !horario) {
      Toast.show('Completá los campos obligatorios.', 'error');
      return;
    }
    if (!lat || !lng) {
      MapaSede.estado('Marcá la ubicación de la sede en el mapa antes de guardar.', 'error');
      Toast.show('Marcá la ubicación de la sede en el mapa.', 'error');
      return;
    }

    const body = { nombre, direccion, referencia, departamento, provincia, horario, lat, lng };
    if (form['sede-activo'])        body.activo = form['sede-activo'].value === 'true';
    if (form['sede-turnos-online']) body.recibe_turnos_online = form['sede-turnos-online'].checked;

    const url = RC.url(id ? `/api/sedes/${id}/editar/` : '/api/sedes/crear/');

    try {
      const r = await fetch(url, {
        method:  'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken':  this.getCookie(RC.csrfCookie),
        },
        body: JSON.stringify(body),
      });
      const data = await r.json();

      if (data.error) { Toast.show(data.error, 'error'); return; }

      bootstrap.Modal.getInstance(document.getElementById('modal-sede'))?.hide();
      Toast.show(id ? 'Sede actualizada.' : 'Sede creada correctamente.', 'success');
      await this.init();

    } catch { Toast.show('Error al guardar sede.', 'error'); }
  },

  async eliminar(id) {
    if (!confirm('¿Eliminar esta sede? Esta acción no se puede deshacer.')) return;

    try {
      const r    = await fetch(RC.url(`/api/sedes/${id}/eliminar/`), {
        method:  'POST',
        headers: { 'X-CSRFToken': this.getCookie(RC.csrfCookie) },
      });
      const data = await r.json();

      if (data.error) { Toast.show(data.error, 'error'); return; }
      Toast.show('Sede eliminada.', 'warning');
      await this.init();

    } catch { Toast.show('Error al eliminar sede.', 'error'); }
  },

  getCookie(name) {
    const value = `; ${document.cookie}`;
    const parts = value.split(`; ${name}=`);
    if (parts.length === 2) return parts.pop().split(';').shift();
  },

  async init() {
    const btnNueva = document.getElementById('btn-nueva-sede');
    if (btnNueva) btnNueva.onclick = () => this.openModal();

    MapaSede.conectarControles();
    const sedes = await this.cargar();
    this.render(sedes);
  }
};

/* ── Selector de ubicación de la sede (Leaflet + OpenStreetMap) ──
   El punto se marca con un clic, arrastrando el marcador, buscando una dirección,
   con la ubicación del dispositivo o pegando coordenadas / un link de Google Maps. */
const MapaSede = {
  mapa: null,
  marcador: null,
  controlesListos: false,
  // OpenStreetMap pide recibir el origen del sitio en cada petición
  REFERRER: 'strict-origin-when-cross-origin',

  abrir(punto) {
    if (typeof L === 'undefined') {
      this.estado('No se pudo cargar el mapa. Revisá tu conexión.', 'error');
      return;
    }
    if (!this.mapa) {
      this.mapa = L.map('sede-map').setView(ModSedes.CENTRO_SDE, 13);
      L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
        maxZoom: 19,
        referrerPolicy: this.REFERRER,
        attribution: '© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
      }).addTo(this.mapa);
      this.mapa.on('click', e => this.marcar(e.latlng.lat, e.latlng.lng, { completarDireccion: true }));
    }
    this.mapa.invalidateSize();

    if (this.marcador) { this.mapa.removeLayer(this.marcador); this.marcador = null; }
    this.guardar(null, null);

    if (punto) {
      this.marcar(punto[0], punto[1], { zoom: 17 });
    } else {
      this.mapa.setView(ModSedes.CENTRO_SDE, 13);
      this.estado('Todavía no marcaste la ubicación: buscá la dirección o hacé clic en el mapa sobre el edificio.', 'aviso');
    }
  },

  dentroDeSDE(lat, lng) {
    const l = ModSedes.LIMITES;
    return lat >= l.latMin && lat <= l.latMax && lng >= l.lngMin && lng <= l.lngMax;
  },

  marcar(lat, lng, { zoom = null, completarDireccion = false } = {}) {
    lat = Number(lat); lng = Number(lng);
    if (!isFinite(lat) || !isFinite(lng)) return;
    if (!this.dentroDeSDE(lat, lng)) {
      this.estado('Ese punto está fuera de Santiago del Estero. Revisá la ubicación.', 'error');
      return;
    }

    if (!this.marcador) {
      this.marcador = L.marker([lat, lng], { draggable: true }).addTo(this.mapa);
      this.marcador.on('dragend', () => {
        const p = this.marcador.getLatLng();
        this.marcar(p.lat, p.lng, { completarDireccion: true });
      });
    } else {
      this.marcador.setLatLng([lat, lng]);
    }
    if (zoom) this.mapa.setView([lat, lng], zoom);
    else this.mapa.panTo([lat, lng]);

    this.guardar(lat, lng);
    this.estado(`Ubicación marcada (${lat.toFixed(5)}, ${lng.toFixed(5)}). Podés arrastrar el marcador para ajustarla.`, 'ok');
    if (completarDireccion) this.completarDireccion(lat, lng);
  },

  guardar(lat, lng) {
    const form = document.getElementById('form-sede');
    form['sede-lat'].value = lat == null ? '' : lat.toFixed(6);
    form['sede-lng'].value = lng == null ? '' : lng.toFixed(6);
    document.getElementById('sede-map').classList.toggle('sin-ubicacion', lat == null);
  },

  estado(msg, tipo = '') {
    const el = document.getElementById('sede-map-estado');
    if (!el) return;
    const icono = { ok: 'bi-check-circle-fill', error: 'bi-exclamation-circle-fill', aviso: 'bi-info-circle' }[tipo] || 'bi-hand-index';
    el.className = `sede-map-estado ${tipo === 'aviso' ? '' : tipo}`;
    el.innerHTML = `<i class="bi ${icono}"></i> `;
    el.appendChild(document.createTextNode(msg));
  },

  // Si dirección o departamento están vacíos, se sugieren a partir del punto marcado
  async completarDireccion(lat, lng) {
    const form = document.getElementById('form-sede');
    if (form['sede-direccion'].value.trim() && form['sede-departamento'].value.trim()) return;
    try {
      const r = await fetch(`https://nominatim.openstreetmap.org/reverse?format=json&zoom=18&addressdetails=1&accept-language=es&lat=${lat}&lon=${lng}`,
        { referrerPolicy: this.REFERRER });
      const a = (await r.json()).address || {};
      if (!form['sede-direccion'].value.trim() && a.road) {
        form['sede-direccion'].value = [a.road, a.house_number].filter(Boolean).join(' ');
      }
      const depto = (a.county || a.state_district || '').replace(/^Departamento\s+/i, '');
      if (!form['sede-departamento'].value.trim() && depto) form['sede-departamento'].value = depto;
    } catch { /* la sugerencia es opcional */ }
  },

  async buscar() {
    const q    = document.getElementById('sede-map-q').value.trim();
    const caja = document.getElementById('sede-map-resultados');
    if (q.length < 3) { this.estado('Escribí al menos 3 letras para buscar.', 'error'); return; }

    caja.innerHTML = '<div class="vacio">Buscando…</div>';
    caja.classList.add('show');
    const l = ModSedes.LIMITES;
    const url = 'https://nominatim.openstreetmap.org/search?format=json&limit=6&countrycodes=ar&accept-language=es'
      + `&bounded=1&viewbox=${l.lngMin},${l.latMax},${l.lngMax},${l.latMin}`
      + `&q=${encodeURIComponent(q + ', Santiago del Estero')}`;
    try {
      const r = await fetch(url, { referrerPolicy: this.REFERRER });
      const resultados = await r.json();
      if (!resultados.length) {
        caja.innerHTML = '<div class="vacio">No encontramos esa dirección. Probá con el nombre de una sola calle o hacé clic directamente en el mapa.</div>';
        return;
      }
      caja.innerHTML = '';
      resultados.forEach(res => {
        const b = document.createElement('button');
        b.type = 'button';
        b.textContent = res.display_name;
        b.onclick = () => {
          caja.classList.remove('show');
          this.marcar(res.lat, res.lon, { zoom: 17 });
          this.estado('Ubicación aproximada: arrastrá el marcador hasta la puerta del edificio si hace falta.', 'ok');
        };
        caja.appendChild(b);
      });
    } catch {
      caja.innerHTML = '<div class="vacio">No se pudo buscar en este momento. Hacé clic directamente en el mapa.</div>';
    }
  },

  usarMiUbicacion() {
    if (!navigator.geolocation) { this.estado('Este navegador no permite obtener la ubicación.', 'error'); return; }
    this.estado('Obteniendo tu ubicación…', 'aviso');
    navigator.geolocation.getCurrentPosition(
      pos => this.marcar(pos.coords.latitude, pos.coords.longitude, { zoom: 18, completarDireccion: true }),
      ()  => this.estado('No se pudo obtener tu ubicación (permiso denegado o sin señal).', 'error'),
      { enableHighAccuracy: true, timeout: 10000 }
    );
  },

  // Acepta "-27.78384, -64.26695" (clic derecho en Google Maps) o links largos de Google Maps
  pegar() {
    const txt = document.getElementById('sede-map-pegar').value.trim();
    if (!txt) return;
    if (/goo\.gl|maps\.app/i.test(txt)) {
      this.estado('Los links cortos no se pueden leer. En Google Maps hacé clic derecho sobre el lugar y copiá las coordenadas.', 'error');
      return;
    }
    const num = '(-?\\d{1,2}\\.\\d+)';
    const patrones = [
      new RegExp(`!3d${num}!4d(-?\\d{1,3}\\.\\d+)`),                  // punto exacto del lugar
      new RegExp(`[?&](?:q|query|ll|destination)=${num},\\s*(-?\\d{1,3}\\.\\d+)`),
      new RegExp(`@${num},(-?\\d{1,3}\\.\\d+)`),                       // centro de la vista
      new RegExp(`^${num}\\s*[,; ]\\s*(-?\\d{1,3}\\.\\d+)$`),           // coordenadas sueltas
    ];
    for (const re of patrones) {
      const m = txt.match(re);
      if (m) { this.marcar(m[1], m[2], { zoom: 18, completarDireccion: true }); return; }
    }
    this.estado('No se reconocieron coordenadas. Pegá algo como "-27.78384, -64.26695".', 'error');
  },

  conectarControles() {
    if (this.controlesListos) return;
    this.controlesListos = true;
    document.getElementById('sede-map-btn-buscar')?.addEventListener('click', () => this.buscar());
    document.getElementById('sede-map-q')?.addEventListener('keydown', e => {
      if (e.key === 'Enter') { e.preventDefault(); this.buscar(); }
    });
    document.getElementById('sede-map-btn-ubicacion')?.addEventListener('click', () => this.usarMiUbicacion());
    document.getElementById('sede-map-btn-pegar')?.addEventListener('click', () => this.pegar());
    document.getElementById('sede-map-pegar')?.addEventListener('keydown', e => {
      if (e.key === 'Enter') { e.preventDefault(); this.pegar(); }
    });
  },
};

/* ════════════════════════════════════════════════
  REGISTRO DE ACTIVIDAD (solo Super Admin)
   ════════════════════════════════════════════════ */
const ModActividad = {
  pagina: 1,
  listo: false,

  ETIQUETAS: {
    titulo: 'Título', cuerpo: 'Contenido', tag: 'Categoría', estado: 'Estado', imagen: 'Imagen',
    nombre: 'Nombre', descripcion: 'Descripción', slug: 'URL', categoria: 'Categoría', precio: 'Precio',
    es_gratuito: 'Gratuito', requiere_turno: 'Requiere turno', requisitos: 'Requisitos',
    como_se_inicia: 'Cómo se inicia', modalidad_presencial: 'Presencial', modalidad_digital: 'Digital',
    icono: 'Ícono', orden: 'Orden', direccion: 'Dirección', referencia: 'Referencia',
    departamento: 'Departamento', provincia: 'Provincia', horario: 'Horario', latitud: 'Latitud',
    longitud: 'Longitud', activo: 'Activo', recibe_turnos_online: 'Turnos online', email: 'Correo',
    rol: 'Rol', 'contraseña': 'Contraseña', tramite: 'Trámite', dni: 'DNI', fecha: 'Fecha', hora: 'Hora', sede: 'Sede',
  },
  COLORES: {
    crear: 'badge-asistio', editar: 'badge-pendiente', eliminar: 'badge-cancelado', estado: 'badge-operador',
    reprogramar: 'badge-operador', activar: 'badge-asistio', desactivar: 'badge-cancelado',
    password: 'badge-admin', login: 'badge-noasistio', logout: 'badge-noasistio',
  },

  esc(t) {
    return String(t ?? '').replace(/[&<>"']/g, c =>
      ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  },

  // Códigos internos → texto legible
  VALORES: {
    pendiente: 'Pendiente', asistio: 'Asistió', no_asistio: 'No asistió', cancelado: 'Cancelado',
    borrador: 'Borrador', revision: 'En revisión', publicada: 'Publicada', publicado: 'Publicado',
    archivada: 'Archivada', archivado: 'Archivado', operador: 'Operador', super_admin: 'Super Admin',
    'dni-5-8': 'DNI 5-8 años', 'dni-14': 'DNI 14 años', 'dni-domicilio': 'DNI cambio de domicilio',
    'dni-nuevo': 'DNI nuevo ejemplar', pasaporte: 'Pasaporte',
  },

  valor(v) {
    if (v === true) return 'Sí';
    if (v === false) return 'No';
    if (v === null || v === undefined || v === '') return '—';
    return this.esc(this.VALORES[v] || v);
  },

  // {campo: [antes, después]} → "Campo: antes → después"; {campo: valor} → "Campo: valor"
  detalle(cambios) {
    const filas = Object.entries(cambios || {}).map(([k, v]) => {
      const nombre = this.ETIQUETAS[k] || k;
      if (Array.isArray(v) && v.length === 2) {
        return `<div><strong>${this.esc(nombre)}:</strong> <span class="act-antes">${this.valor(v[0])}</span> → ${this.valor(v[1])}</div>`;
      }
      return `<div><strong>${this.esc(nombre)}:</strong> ${this.valor(v)}</div>`;
    });
    return filas.length ? `<div class="act-detalle">${filas.join('')}</div>` : '<span class="text-muted">—</span>';
  },

  llenarSelect(id, opciones) {
    const sel = document.getElementById(id);
    if (!sel || sel.options.length > 1) return;
    opciones.forEach(([valor, texto]) => {
      const o = document.createElement('option');
      o.value = valor;
      o.textContent = texto;
      sel.appendChild(o);
    });
  },

  async cargar() {
    const tbody = document.getElementById('actividad-tbody');
    const p = new URLSearchParams({ pagina: this.pagina });
    [['q', 'act-q'], ['usuario', 'act-usuario'], ['modulo', 'act-modulo'], ['accion', 'act-accion'],
     ['desde', 'act-desde'], ['hasta', 'act-hasta']].forEach(([k, id]) => {
      const v = document.getElementById(id)?.value;
      if (v) p.set(k, v);
    });

    try {
      const r = await fetch(RC.url(`/api/actividad/?${p}`));
      const data = await r.json();
      if (data.error) {
        tbody.innerHTML = `<tr><td colspan="6" class="text-center py-4 text-muted">${this.esc(data.error)}</td></tr>`;
        return;
      }

      this.llenarSelect('act-usuario', data.usuarios.map(u => [u, u]));
      this.llenarSelect('act-modulo', data.modulos);
      this.llenarSelect('act-accion', data.acciones);

      document.getElementById('actividad-total').textContent = data.total;
      document.getElementById('act-pagina').textContent = `Página ${data.pagina} de ${data.paginas}`;
      document.getElementById('act-anterior').disabled = data.pagina <= 1;
      document.getElementById('act-siguiente').disabled = data.pagina >= data.paginas;
      this.pagina = data.pagina;

      tbody.innerHTML = data.registros.length ? data.registros.map(x => `
        <tr>
          <td style="white-space:nowrap;"><small>${this.esc(x.fecha)}</small></td>
          <td>${this.esc(x.usuario)}${x.ip ? `<br/><small style="color:#888;">${this.esc(x.ip)}</small>` : ''}</td>
          <td><span class="badge-estado ${this.COLORES[x.accion] || ''}">${this.esc(x.accion_texto)}</span></td>
          <td>${this.esc(x.modulo)}</td>
          <td>${this.esc(x.objeto)}</td>
          <td>${this.detalle(x.cambios)}</td>
        </tr>`).join('')
        : '<tr><td colspan="6" class="text-center py-4 text-muted">No hay actividad con esos filtros.</td></tr>';
    } catch {
      tbody.innerHTML = '<tr><td colspan="6" class="text-center py-4 text-muted">No se pudo cargar el registro.</td></tr>';
    }
  },

  init() {
    if (!this.listo) {
      this.listo = true;
      let espera;
      const recargar = () => { this.pagina = 1; this.cargar(); };
      document.getElementById('act-q')?.addEventListener('input', () => {
        clearTimeout(espera);
        espera = setTimeout(recargar, 300);
      });
      ['act-usuario', 'act-modulo', 'act-accion', 'act-desde', 'act-hasta'].forEach(id =>
        document.getElementById(id)?.addEventListener('change', recargar));
      document.getElementById('act-anterior')?.addEventListener('click', () => { this.pagina--; this.cargar(); });
      document.getElementById('act-siguiente')?.addEventListener('click', () => { this.pagina++; this.cargar(); });
    }
    this.cargar();
  },
};

/* ════════════════════════════════════════════════
  12. MÓDULO ESTADÍSTICAS
   ════════════════════════════════════════════════ */
const ModEstadisticas = {

  async cargar() {
    const r    = await fetch(RC.url('/api/turnos/estadisticas/'));
    const data = await r.json();
    return data;
  },

  barras(containerId, items, colorFn) {
    const container = document.getElementById(containerId);
    if (!container) return;
    const max = Math.max(...items.map(i => i.valor), 1);

    container.innerHTML = items.map(item => `
      <div style="margin-bottom:12px;">
        <div style="display:flex;justify-content:space-between;font-size:13px;margin-bottom:4px;">
          <span style="font-weight:600;color:#2d3748;">${item.label}</span>
          <span style="font-weight:700;color:#2d3748;">${item.valor}</span>
        </div>
        <div style="background:#f0f2f5;border-radius:20px;height:10px;overflow:hidden;">
          <div style="
            width:${Math.round(item.valor / max * 100)}%;
            height:100%;
            background:${colorFn(item)};
            border-radius:20px;
            transition:width .6s ease;
          "></div>
        </div>
      </div>
    `).join('');
  },

  render(data) {
    // Cards resumen
    document.getElementById('est-hoy-total').textContent     = data.hoy_total;
    document.getElementById('est-hoy-pendientes').textContent = data.hoy_pendientes;
    document.getElementById('est-tasa').textContent           = `${data.tasa_asistencia}%`;
    document.getElementById('est-total').textContent          = data.total;

    // Por estado
    this.barras('est-por-estado', [
      { label: 'Pendientes',   valor: data.pendientes,    color: '#b8860b' },
      { label: 'Asistieron',   valor: data.asistieron,    color: '#1e7e34' },
      { label: 'No asistieron',valor: data.no_asistieron, color: '#c8102e' },
      { label: 'Cancelados',   valor: data.cancelados,    color: '#6c757d' },
    ], item => item.color);

    // Por origen
    const totalOrigen = (data.sistema + data.manual) || 1;
    this.barras('est-por-origen', [
      { label: `Sistema (ciudadanos) — ${Math.round(data.sistema/totalOrigen*100)}%`,
        valor: data.sistema, color: '#0066cc' },
      { label: `Manual (empleados) — ${Math.round(data.manual/totalOrigen*100)}%`,
        valor: data.manual,  color: '#c8102e' },
    ], item => item.color);

    // Por trámite
    const tramiteLabels = {
      'dni-5-8':       'DNI 5-8 años',
      'dni-14':        'DNI 14 años',
      'dni-domicilio': 'Cambio domicilio',
      'dni-nuevo':     'Nuevo ejemplar',
      'pasaporte':     'Pasaporte',
    };
    this.barras('est-por-tramite',
      data.por_tramite.map(t => ({
        label: tramiteLabels[t.tramite] || t.tramite,
        valor: t.total
      })),
      () => '#c8102e'
    );

    // Últimos 7 días
    const contenedor7 = document.getElementById('est-ultimos-7');
    if (contenedor7) {
      if (data.ultimos_7.length === 0) {
        contenedor7.innerHTML = '<p style="color:#888;font-size:13px;text-align:center;padding:20px 0;">Sin datos en los últimos 7 días.</p>';
      } else {
        const max7 = Math.max(...data.ultimos_7.map(d => d.total), 1);
        contenedor7.innerHTML = data.ultimos_7.map(d => {
          const [y, m, dia] = d.dia.split('-');
          const fecha = `${dia}/${m}`;
          const pct   = Math.round(d.total / max7 * 100);
          return `
            <div style="margin-bottom:10px;">
              <div style="display:flex;justify-content:space-between;font-size:12px;margin-bottom:3px;">
                <span style="font-weight:600;color:#2d3748;">${fecha}</span>
                <span style="font-weight:700;color:#2d3748;">${d.total}</span>
              </div>
              <div style="background:#f0f2f5;border-radius:20px;height:8px;overflow:hidden;">
                <div style="width:${pct}%;height:100%;background:#c8102e;border-radius:20px;transition:width .6s ease;"></div>
              </div>
            </div>`;
        }).join('');
      }
    }
  },

  async init() {
    try {
      const data = await this.cargar();
      this.render(data);
    } catch (e) {
      console.error('[ModEstadisticas]', e);
    }
  }
};

/* ════════════════════════════════════════════════
  13. INIT GENERAL ADMIN
   ════════════════════════════════════════════════ */

function initAdmin() {
  if (!document.querySelector('.admin-body')) return;
  if (document.getElementById('sec-sedes')) ModSedes.init();
  if (document.getElementById('sec-tramites-panel')) ModTramites.init();
  if (document.getElementById('sec-estadisticas')) ModEstadisticas.init();

  // Mostrar usuario actual
const userDisplay = document.getElementById('adm-current-user');
if (userDisplay) {
    fetch(RC.url('/api/usuario-actual/'))
        .then(r => r.json())
        .then(data => { userDisplay.textContent = data.nombre || data.username; })
        .catch(() => { userDisplay.textContent = 'Admin'; });
}

  // Inicializar navegación y módulos
  initNav();
  ModTurnos.init();
  ModUsuarios.init();
  ModNoticias.init();
}

/* ════════════════════════════════════════════════
  14. BOOTSTRAP
   ════════════════════════════════════════════════ */

   // Limpiar backdrop de modales al cerrar
document.addEventListener('hidden.bs.modal', () => {
  document.querySelectorAll('.modal-backdrop').forEach(b => b.remove());
  document.body.classList.remove('modal-open');
  document.body.style.overflow   = '';
  document.body.style.paddingRight = '';
});

document.addEventListener('DOMContentLoaded', () => {
  // Aviso tras cambiar la contraseña
  if (new URLSearchParams(location.search).get('password') === 'actualizada') {
    setTimeout(() => Toast.show('Tu contraseña se actualizó correctamente.', 'success'), 300);
    history.replaceState(null, '', location.pathname);
  }
  initAdmin();
});
