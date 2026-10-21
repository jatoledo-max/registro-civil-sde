"""
Medición de sostenibilidad de una carga de página (Gestión de Proyectos – Sostenibilidad).

Simula la primera visita de un ciudadano (sin caché) a una o más páginas del sitio y mide:
  - Tiempo: respuesta del servidor (mediana de N repeticiones) y descarga total de recursos.
  - Recursos: cantidad de pedidos y bytes transferidos (comprimidos, como los recibe el navegador).
  - Energía y CO2 estimados con el Sustainable Web Design Model v4:
      0,30 kWh por GB transferido y 494 g CO2e por kWh (promedio mundial).

Solo usa la biblioteca estándar de Python. Cada ejecución agrega filas a mediciones.csv.

Uso:
    python herramientas/medir_sostenibilidad.py
    python herramientas/medir_sostenibilidad.py --url http://localhost:8000 --repeticiones 10
"""

import argparse
import csv
import gzip
import os
import re
import statistics
import time
import urllib.parse
import urllib.request
import zlib
from datetime import datetime
from html.parser import HTMLParser

KWH_POR_GB = 0.30          # SWD v4: 0,194 operativa + 0,106 incorporada
G_CO2_POR_KWH = 494        # SWD v4: intensidad de carbono promedio mundial (Ember)
AGENTE = 'MedicionSostenibilidad-RegistroCivil/1.0 (practica academica)'
ARCHIVO_CSV = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'mediciones.csv')


class RecursosHTML(HTMLParser):
    """Junta los recursos que el navegador descarga al abrir la página."""

    def __init__(self):
        super().__init__()
        self.recursos = []
        self._fondo_tomado = False

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == 'img' and a.get('src'):
            self.recursos.append(a['src'])
        elif tag == 'script' and a.get('src'):
            self.recursos.append(a['src'])
        elif tag == 'link' and a.get('href') and a.get('rel', '') in ('stylesheet', 'icon'):
            self.recursos.append(a['href'])
        # Fondo del carrusel: solo se descarga la diapositiva visible (la primera)
        estilo = a.get('style', '')
        if not self._fondo_tomado and 'url(' in estilo:
            m = re.search(r"url\(['\"]?([^'\")]+)", estilo)
            if m:
                self.recursos.append(m.group(1))
                self._fondo_tomado = True


def descargar(url):
    """Devuelve (bytes transferidos, cuerpo descomprimido, segundos)."""
    pedido = urllib.request.Request(url, headers={'User-Agent': AGENTE, 'Accept-Encoding': 'gzip, deflate'})
    inicio = time.perf_counter()
    with urllib.request.urlopen(pedido, timeout=30) as r:
        crudo = r.read()
        codificacion = r.headers.get('Content-Encoding', '')
    segundos = time.perf_counter() - inicio
    if codificacion == 'gzip':
        cuerpo = gzip.decompress(crudo)
    elif codificacion == 'deflate':
        cuerpo = zlib.decompress(crudo)
    else:
        cuerpo = crudo
    return len(crudo), cuerpo, segundos


def medir_pagina(base, ruta, repeticiones):
    url = urllib.parse.urljoin(base, ruta)

    # 1) Tiempo de respuesta del servidor (mediana)
    tiempos, html_bytes, html = [], 0, b''
    for _ in range(repeticiones):
        html_bytes, html, seg = descargar(url)
        tiempos.append(seg * 1000)
    ms_html = statistics.median(tiempos)

    # 2) Recursos de la página (sin caché, sin repetir)
    parser = RecursosHTML()
    parser.feed(html.decode('utf-8', errors='replace'))
    recursos = list(dict.fromkeys(urllib.parse.urljoin(url, r) for r in parser.recursos))

    # Imágenes de noticias, que se cargan por JavaScript en el inicio
    if ruta in ('/', ''):
        try:
            import json
            _, cuerpo, _ = descargar(urllib.parse.urljoin(base, '/api/noticias/publicas/'))
            for n in json.loads(cuerpo).get('noticias', []):
                if n.get('imagen'):
                    recursos.append(urllib.parse.urljoin(base, n['imagen']))
            recursos = list(dict.fromkeys(recursos))
        except Exception:
            pass

    detalle, total_bytes, seg_recursos = [], html_bytes, 0.0
    for r in recursos:
        try:
            b, _, seg = descargar(r)
        except Exception as e:
            print(f'   (no se pudo descargar {r}: {e})')
            continue
        detalle.append((b, r))
        total_bytes += b
        seg_recursos += seg

    gb = total_bytes / 1e9
    kwh = gb * KWH_POR_GB
    g_co2 = kwh * G_CO2_POR_KWH
    detalle.sort(reverse=True)

    return {
        'ruta': ruta,
        'pedidos': len(detalle) + 1,
        'kb_total': total_bytes / 1024,
        'ms_servidor': ms_html,
        'ms_descarga': ms_html + seg_recursos * 1000,
        'wh_visita': kwh * 1000,
        'g_co2_visita': g_co2,
        'mas_pesado': detalle[0] if detalle else (0, '-'),
        'detalle': detalle,
    }


def main():
    p = argparse.ArgumentParser(description='Medición de sostenibilidad de páginas del sitio')
    p.add_argument('--url', default='https://javiertoledo1713.pythonanywhere.com', help='Sitio a medir')
    p.add_argument('--paginas', default='/,/tramites/,/sedes/', help='Rutas separadas por coma')
    p.add_argument('--repeticiones', type=int, default=5, help='Repeticiones para el tiempo del servidor')
    p.add_argument('--etiqueta', default='', help='Nota para el CSV (ej.: "linea de base" o "con mejora")')
    args = p.parse_args()

    ahora = datetime.now().strftime('%Y-%m-%d %H:%M')
    filas = []
    print(f'\nMedición {ahora} · {args.url}\n')
    for ruta in [r.strip() for r in args.paginas.split(',') if r.strip()]:
        m = medir_pagina(args.url, ruta, args.repeticiones)
        filas.append(m)
        print(f"{ruta:<12} {m['pedidos']:>3} pedidos  {m['kb_total']:>7.1f} KB  "
              f"servidor {m['ms_servidor']:>6.0f} ms  descarga {m['ms_descarga']:>6.0f} ms  "
              f"{m['wh_visita']:.4f} Wh  {m['g_co2_visita']:.3f} g CO2e")
        for b, r in m['detalle'][:3]:
            print(f'{"":14}{b / 1024:>7.1f} KB  {r}')

    # Un visitante que recorre las páginas descarga cada recurso compartido una sola vez
    # (el navegador lo guarda en caché): se suman los recursos sin repetir.
    unicos = {}
    for f in filas:
        unicos[f['ruta']] = f['kb_total'] * 1024 - sum(b for b, _ in f['detalle'])   # HTML de la página
        for b, r in f['detalle']:
            unicos[r] = b
    total_kb = sum(unicos.values()) / 1024
    total_g = total_kb * 1024 / 1e9 * KWH_POR_GB * G_CO2_POR_KWH
    print(f'\nRecorrido completo ({len(filas)} páginas, con caché del navegador): '
          f'{total_kb:.1f} KB · {total_g:.3f} g CO2e por visitante nuevo')
    print(f'Cada 10.000 visitantes nuevos: {total_kb * 10000 / 1024 / 1024:.2f} GB · '
          f'{total_g * 10000 / 1000:.2f} kg CO2e\n')

    nuevo = not os.path.exists(ARCHIVO_CSV)
    with open(ARCHIVO_CSV, 'a', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        if nuevo:
            w.writerow(['fecha', 'sitio', 'etiqueta', 'pagina', 'pedidos', 'kb_transferidos',
                        'ms_servidor_mediana', 'ms_descarga_total', 'wh_por_visita', 'g_co2e_por_visita',
                        'recurso_mas_pesado', 'kb_recurso_mas_pesado'])
        for m in filas:
            b, r = m['mas_pesado']
            w.writerow([ahora, args.url, args.etiqueta, m['ruta'], m['pedidos'], f"{m['kb_total']:.1f}",
                        f"{m['ms_servidor']:.0f}", f"{m['ms_descarga']:.0f}", f"{m['wh_visita']:.4f}",
                        f"{m['g_co2_visita']:.4f}", r, f'{b / 1024:.1f}'])
    print(f'Resultados agregados a {ARCHIVO_CSV}')


if __name__ == '__main__':
    main()
