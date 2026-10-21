const INDICE_BUSQUEDA = [
  { titulo: "Inscripción de nacimiento",     texto: "nacimiento inscripción acta recién nacido registro bebé hijo partida",
    url: RC.url("/nacimiento/"),              icono: "bi-person-fill-add",           cat: "Trámite" },
  { titulo: "Identificación – DNI",          texto: "dni documento nacional identidad primer ejemplar renovación actualización cambio domicilio duplicado extravío",
    url: RC.url("/identificacion/"),          icono: "bi-credit-card-2-front",       cat: "Trámite" },
  { titulo: "DNI – Actualización 5-8 años",  texto: "dni actualización 5 8 años niños chicos renovación",
    url: RC.url("/tramites/dni-5-8/"),        icono: "bi-person-fill",               cat: "Trámite" },
  { titulo: "DNI – Actualización 14 años",   texto: "dni actualización 14 años adolescente renovación",
    url: RC.url("/tramites/dni-14/"),         icono: "bi-person-fill",               cat: "Trámite" },
  { titulo: "DNI – Cambio de domicilio",     texto: "dni cambio de domicilio dirección mudanza",
    url: RC.url("/tramites/dni-domicilio/"),  icono: "bi-house-fill",                cat: "Trámite" },
  { titulo: "DNI – Nuevo ejemplar",          texto: "dni nuevo ejemplar robo extravío deterioro perdí duplicado",
    url: RC.url("/tramites/dni-nuevo/"),      icono: "bi-person-badge-fill",         cat: "Trámite" },
  { titulo: "Pasaporte",                     texto: "pasaporte viaje exterior renaper",
    url: RC.url("/tramites/pasaporte/"),      icono: "bi-passport",                  cat: "Trámite" },
  { titulo: "Solicitar turno para DNI",               texto: "turno solicitar sacar pedir turno dni presencial cita",
    url: "#", modal: "#modalTurno",   icono: "bi-calendar-check-fill",       cat: "Turno" },
  { titulo: "Matrimonio civil",              texto: "matrimonio casamiento civil unión casarse boda",
    url: RC.url("/matrimonio/"),              icono: "bi-people-fill",               cat: "Trámite" },
  { titulo: "Inscripción de defunción",      texto: "defunción fallecimiento muerte acta deceso",
    url: RC.url("/defuncion/"),               icono: "bi-file-earmark-medical-fill", cat: "Trámite" },
  { titulo: "Todos los trámites",            texto: "todos los trámites lista completa",
    url: RC.url("/tramites/"),                icono: "bi-list-ul",                   cat: "Sección" },
  { titulo: "Sedes y oficinas",              texto: "sedes oficinas locales registro civil dirección mapa dónde horario",
    url: RC.url("/sedes/"),                   icono: "bi-geo-alt-fill",              cat: "Sección" },
];

// Minúsculas y sin acentos, para que "defuncion" encuentre "Defunción"
function normalizar(s) {
  return s.toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "");
}

function buscarEnIndice(q) {
  const palabras = normalizar(q.trim()).split(/\s+/).filter(Boolean);
  if (!palabras.length) return [];
  return INDICE_BUSQUEDA
    .map(item => {
      const hay  = normalizar(item.titulo + " " + item.texto);
      const hits = palabras.filter(p => hay.includes(p)).length;
      return { ...item, hits };
    })
    .filter(item => item.hits > 0)
    .sort((a, b) => b.hits - a.hits);
}

function abrirResultado(item) {
  if (item.modal && window.bootstrap) {
    bootstrap.Modal.getOrCreateInstance(document.querySelector(item.modal)).show();
  } else if (item.url && item.url !== "#") {
    window.location.href = item.url;
  }
}

document.addEventListener("DOMContentLoaded", function () {
  const input   = document.getElementById("buscador-input");
  const btnBusc = document.getElementById("buscador-btn");
  const panel   = document.getElementById("buscador-resultados");

  if (!input || !panel) return;

  let resultados = [];

  function buscar(q) {
    if (q.trim().length < 2) { panel.style.display = "none"; return; }

    resultados = buscarEnIndice(q).slice(0, 6);

    if (!resultados.length) {
      panel.innerHTML = `
        <div style="padding:14px 16px;font-family:'Barlow',sans-serif;font-size:14px;color:#666;">
          <i class="bi bi-search me-1"></i> No encontramos resultados.
          Probá con otra palabra o consultá a <strong>RegIna</strong>, nuestra asistente virtual.
        </div>`;
      panel.style.display = "block";
      return;
    }

    panel.innerHTML = resultados.map((m, i) => `
      <a href="${m.url}" data-idx="${i}" style="
        display:flex; align-items:center; gap:12px;
        padding:11px 16px; text-decoration:none; color:#222;
        border-bottom:1px solid #f5f5f5; transition:background .15s;
        font-family:'Barlow',sans-serif; font-size:14px;
      " onmouseover="this.style.background='#fff5f7'" onmouseout="this.style.background=''">
        <i class="bi ${m.icono}" style="font-size:1.2rem;color:#c8102e;flex-shrink:0;"></i>
        <div>
          <div style="font-weight:600;">${m.titulo}</div>
          <div style="font-size:11px;color:#888;">${m.cat}</div>
        </div>
        <i class="bi bi-arrow-right-short" style="margin-left:auto;color:#bbb;font-size:1.1rem;"></i>
      </a>
    `).join("");

    panel.querySelectorAll("a[data-idx]").forEach(a => {
      a.addEventListener("click", e => {
        const item = resultados[Number(a.dataset.idx)];
        if (item.modal) {
          e.preventDefault();
          panel.style.display = "none";
          abrirResultado(item);
        }
      });
    });

    panel.style.display = "block";
  }

  function irPrimerResultado(q) {
    const mejor = buscarEnIndice(q)[0];
    if (mejor) abrirResultado(mejor);
    else buscar(q);   // muestra el mensaje de "sin resultados"
  }

  input.addEventListener("input",   () => buscar(input.value));
  input.addEventListener("keydown",  e => {
    if (e.key === "Enter")  { panel.style.display = "none"; irPrimerResultado(input.value); }
    if (e.key === "Escape") panel.style.display = "none";
  });
  btnBusc?.addEventListener("click", () => { panel.style.display = "none"; irPrimerResultado(input.value); });

  document.addEventListener("click", e => {
    if (!input.contains(e.target) && !panel.contains(e.target) && !btnBusc?.contains(e.target)) {
      panel.style.display = "none";
    }
  });
});
