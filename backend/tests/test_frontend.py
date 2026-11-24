"""El frontend se sirve desde la misma aplicación y es compatible con la política de seguridad
del contenido (CSP): sin scripts ni manejadores en línea y sin insertar HTML sin escapar."""
import re

from app import config

PAGINAS = ["index.html", "evento.html", "login.html", "panel.html", "asistencia.html", "consolidado.html"]


def leer(ruta):
    return ruta.read_text(encoding="utf-8")


def test_las_paginas_y_los_recursos_se_sirven(cliente):
    for ruta in ["/"] + [f"/{p}" for p in PAGINAS]:
        r = cliente.get(ruta)
        assert r.status_code == 200 and "text/html" in r.headers["content-type"], ruta
    for recurso in ("/css/estilos.css", "/js/api.js", "/js/comun.js", "/js/sesion.js"):
        assert cliente.get(recurso).status_code == 200, recurso
    assert "Eventos académicos" in cliente.get("/").text


def test_las_paginas_llevan_las_cabeceras_de_seguridad(cliente):
    r = cliente.get("/")
    assert "default-src 'self'" in r.headers["content-security-policy"] and "frame-ancestors 'none'" in r.headers["content-security-policy"]
    assert r.headers["x-frame-options"] == "DENY" and r.headers["x-content-type-options"] == "nosniff"


def test_el_navegador_revalida_las_paginas_y_scripts_en_cada_carga(cliente):
    """Sin esto el navegador conserva copias viejas de los scripts y no se ven los cambios."""
    for ruta in ("/", "/index.html", "/js/evento.js", "/css/estilos.css"):
        r = cliente.get(ruta)
        assert r.headers["cache-control"] == "no-cache" and r.headers.get("etag"), ruta
    assert cliente.get("/api/salud").headers["cache-control"] == "no-store"      # la API nunca se guarda


def test_la_api_no_queda_tapada_por_el_frontend(cliente):
    assert cliente.get("/api/salud").json() == {"estado": "ok"}
    assert cliente.get("/api/no-existe").json()["error"]["codigo"] == "RECURSO_NO_ENCONTRADO"


def test_las_paginas_no_tienen_scripts_ni_manejadores_en_linea():
    for pagina in PAGINAS:
        html = leer(config.FRONTEND_DIR / pagina)
        assert not re.search(r"<script(?![^>]*\bsrc=)", html), f"{pagina}: script en línea"
        assert not re.search(r"\son[a-z]+\s*=", html, re.I), f"{pagina}: manejador en línea (onclick=...)"
        assert "javascript:" not in html.lower(), pagina


def test_todos_los_archivos_referenciados_existen():
    for pagina in PAGINAS:
        html = leer(config.FRONTEND_DIR / pagina)
        for ruta in re.findall(r'(?:src|href)="((?:js|css)/[^"]+)"', html):
            assert (config.FRONTEND_DIR / ruta).exists(), f"{pagina} -> {ruta}"
        for destino in re.findall(r'href="([a-z]+\.html)', html):
            assert (config.FRONTEND_DIR / destino).exists(), f"{pagina} -> {destino}"
    for js in (config.FRONTEND_DIR / "js").glob("*.js"):
        for modulo in re.findall(r"from '\./([\w-]+\.js)'", leer(js)):
            assert (js.parent / modulo).exists(), f"{js.name} -> {modulo}"


def test_el_javascript_no_inserta_html_sin_escapar():
    prohibido = re.compile(r"innerHTML|outerHTML|insertAdjacentHTML|document\.write|\beval\(|new Function\(")
    for js in (config.FRONTEND_DIR / "js").glob("*.js"):
        assert not prohibido.search(leer(js)), f"{js.name} usa una forma de insertar HTML o ejecutar texto"


def test_los_formularios_de_fecha_del_historial_no_tienen_limite_minimo():
    for pagina in ("index.html", "consolidado.html"):
        html = leer(config.FRONTEND_DIR / pagina)
        assert not re.search(r'type="date"[^>]*\bmin=', html), pagina      # fechas pasadas: solo consulta de historial
    panel = leer(config.FRONTEND_DIR / "js" / "panel.js")
    assert "f.inicio.min = ahoraBogota()" in panel                          # al crear eventos sí se bloquea el pasado
