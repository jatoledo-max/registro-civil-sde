/* ════════════════════════════════════════════
  noticias.js — Portal público Registro Civil
  Carga noticias desde Django y maneja el modal
   ════════════════════════════════════════════ */

const IMAGEN_DEFAULT = 'https://i.pinimg.com/1200x/26/63/99/266399e10c027c0a8a106c0cf5f58dba.jpg';

// Escapa texto antes de insertarlo como HTML
function esc(t) {
  return String(t ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
}

async function cargarNoticias() {
  const grid = document.getElementById('noticias-grid');
  if (!grid) return;

  try {
    const r    = await fetch(RC.url('/api/noticias/publicas/'));
    const data = await r.json();

    if (!data.noticias || data.noticias.length === 0) {
      grid.innerHTML = `
        <div class="col-12 text-center text-muted py-4">
          <i class="bi bi-newspaper" style="font-size:32px;opacity:.3;display:block;margin-bottom:8px;"></i>
          No hay noticias publicadas por el momento.
        </div>`;
      return;
    }

    grid.innerHTML = data.noticias.map(n => `
      <div class="col-12 col-sm-6 col-md-4 d-flex">
        <div class="news-card w-100">
          <div class="news-thumb" style="
            height:160px;overflow:hidden;flex-shrink:0;
            background:#f5c6cb;
          ">
            <img src="${esc(n.imagen || IMAGEN_DEFAULT)}"
              alt="${esc(n.titulo)}"
              style="width:100%;height:160px;object-fit:cover;display:block;"
              onerror="this.src='${IMAGEN_DEFAULT}'"
            />
          </div>
          <div class="news-body">
            <span class="news-tag">${esc(n.tag)}</span>
            <div class="news-title">${esc(n.titulo)}</div>
            <div class="news-date">
              <i class="bi bi-calendar3"></i> ${esc(n.fecha)}
            </div>
            <button class="btn-rc" onclick="abrirNoticia(${n.id})">
              Ver noticia
            </button>
          </div>
        </div>
      </div>
    `).join('');

    // Guardar noticias en memoria para el modal
    window._noticiasCache = data.noticias;

  } catch (e) {
    console.error('[noticias.js]', e);
    grid.innerHTML = `
      <div class="col-12 text-center text-muted py-4">
        Error al cargar noticias.
      </div>`;
  }
}

function abrirNoticia(id) {
  const noticias = window._noticiasCache || [];
  const n = noticias.find(x => x.id === id);
  if (!n) return;

  document.getElementById('modalNoticiaTitulo').textContent = n.titulo;
  document.getElementById('modalNoticiaFecha').textContent  = n.fecha;
  document.getElementById('modalNoticiaTag').textContent    = n.tag;
  document.getElementById('modalNoticiaCuerpo').textContent = n.cuerpo;

  const img = document.getElementById('modalNoticiaImg');
  img.src = n.imagen || IMAGEN_DEFAULT;
  img.onerror = () => { img.src = IMAGEN_DEFAULT; };

  new bootstrap.Modal(document.getElementById('modalNoticia')).show();
}

document.addEventListener('DOMContentLoaded', cargarNoticias);
