import { cerrarSesion, obtenerSesion } from './sesion.js';

const ZONA = 'America/Bogota';
export const MENSAJE_RANGO = 'La fecha «desde» no puede ser posterior a la fecha «hasta».';
export const TIPOS = { conferencia: 'Conferencia', taller: 'Taller', seminario: 'Seminario', capacitacion: 'Capacitación' };
const ESTADOS = { borrador: ['gris', 'Borrador'], publicado: ['ok', 'Publicado'], cancelado: ['error', 'Cancelado'], finalizado: ['gris', 'Finalizado'] };

// ------------------------------------------------------------------ DOM seguro
/** Crea un elemento. Los hijos de tipo texto se insertan como TEXTO, nunca como HTML (evita XSS). */
export function el(etiqueta, props = {}, ...hijos) {
  const nodo = document.createElement(etiqueta);
  for (const [clave, valor] of Object.entries(props)) {
    if (valor === null || valor === undefined || valor === false) continue;
    if (clave === 'class') nodo.className = valor;
    else if (clave.startsWith('on')) nodo.addEventListener(clave.slice(2), valor);
    else nodo.setAttribute(clave, valor === true ? '' : valor);
  }
  for (const hijo of hijos.flat(Infinity)) {
    if (hijo === null || hijo === undefined || hijo === false) continue;
    nodo.append(hijo instanceof Node ? hijo : String(hijo));
  }
  return nodo;
}

// ---------------------------------------------------------------------- fechas
const formato = (opciones) => new Intl.DateTimeFormat('es-CO', { timeZone: ZONA, ...opciones });
const fFecha = formato({ weekday: 'short', day: 'numeric', month: 'short', year: 'numeric' });
const fHora = formato({ hour: 'numeric', minute: '2-digit', hour12: true });

export const fechaLarga = (iso) => fFecha.format(new Date(iso));
export const hora = (iso) => fHora.format(new Date(iso));
export const fechaHora = (iso) => `${fechaLarga(iso)}, ${hora(iso)}`;
export const rangoHorario = (inicio, fin) => `${fechaLarga(inicio)} · ${hora(inicio)} – ${hora(fin)}`;

/** Fecha y hora de Colombia como 'AAAA-MM-DDTHH:mm' (formato de <input type="datetime-local">). */
export const aLocalBogota = (fecha) => fecha.toLocaleString('sv-SE', { timeZone: ZONA }).replace(' ', 'T').slice(0, 16);
export const ahoraBogota = () => aLocalBogota(new Date());
/** Valor de un <input datetime-local> -> ISO 8601 con el offset de Colombia (UTC-5). */
export const aIsoBogota = (valorLocal) => `${valorLocal.slice(0, 16)}:00-05:00`;
export const desdeLocalBogota = (valorLocal) => new Date(aIsoBogota(valorLocal));

// --------------------------------------------------------------------- piezas
export const chipTipo = (tipo) => el('span', { class: 'chip tipo' }, TIPOS[tipo] || tipo);
export function chipEstado(estado) {
  const [color, texto] = ESTADOS[estado] || ['gris', estado];
  return el('span', { class: `chip ${color}` }, texto);
}
export function barraCupo(inscritos, cupo) {
  const porcentaje = cupo ? Math.min(100, Math.round((inscritos * 100) / cupo)) : 0;
  const clase = porcentaje >= 100 ? ' lleno' : porcentaje >= 90 ? ' casi' : '';
  return el('div', { class: `barra-cupo${clase}` }, el('span', { style: `width:${porcentaje}%` }));
}

/** Muestra un mensaje en un contenedor (tipo: ok | error | aviso). */
export function mostrarMensaje(contenedor, tipo, texto, detalles = []) {
  contenedor.replaceChildren();
  if (!texto) return;
  const caja = el('div', { class: `alerta ${tipo}`, role: tipo === 'error' ? 'alert' : 'status' }, texto);
  if (detalles.length) caja.append(el('ul', {}, detalles.map((d) => el('li', {}, d.campo ? `${d.campo}: ${d.mensaje}` : d.mensaje))));
  contenedor.append(caja);
}
export function mostrarError(contenedor, error) {
  const detalles = (error.detalles || []).filter((d) => d.mensaje !== error.mensaje);
  mostrarMensaje(contenedor, 'error', error.mensaje || String(error), detalles);
}

/** Muestra (una sola vez) el aviso que dejó otra página, por ejemplo "La sesión venció". */
export function avisoPendiente(contenedor) {
  const aviso = sessionStorage.getItem('aviso');
  if (aviso) {
    sessionStorage.removeItem('aviso');
    mostrarMensaje(contenedor, 'aviso', aviso);
  }
}

/** Devuelve el mensaje de error si el rango está invertido (fechas iguales son válidas). */
export const validarRango = (desde, hasta) => (desde && hasta && desde > hasta ? MENSAJE_RANGO : null);

/** Lee ?id= de la URL; devuelve un entero positivo o null. */
export function parametroId() {
  const id = new URLSearchParams(location.search).get('id');
  return /^[1-9]\d{0,9}$/.test(id || '') ? Number(id) : null;
}

// ---------------------------------------------------------- sesión y encabezado
function enlace(href, texto, clave, activo) {
  return el('a', { href, class: clave === activo ? 'activo' : '' }, texto);
}

export function pintarEncabezado(activo) {
  const sesion = obtenerSesion();
  const rol = sesion?.usuario.rol;
  const salir = () => { cerrarSesion(); location.href = 'index.html'; };
  const nav = el('nav', {},
    enlace('index.html', 'Catálogo', 'catalogo', activo),
    rol ? enlace('panel.html', 'Panel', 'panel', activo) : null,
    rol === 'coordinacion' ? enlace('consolidado.html', 'Consolidado', 'consolidado', activo) : null,
    rol ? el('button', { class: 'btn sec peq', type: 'button', onclick: salir }, `Salir (${sesion.usuario.nombre})`)
        : enlace('login.html', 'Ingresar', 'login', activo));
  document.getElementById('encabezado').replaceChildren(
    el('div', { class: 'barra' }, el('a', { class: 'logo', href: 'index.html' }, 'Eventos Académicos'), nav));
}

/** Exige sesión y rol. Si no corresponde, redirige y devuelve null. */
export function requerirSesion(rolesPermitidos) {
  const sesion = obtenerSesion();
  if (!sesion) {
    const pagina = location.pathname.split('/').pop() || 'index.html';
    location.href = `login.html?volver=${encodeURIComponent(pagina + location.search)}`;
    return null;
  }
  if (!rolesPermitidos.includes(sesion.usuario.rol)) {
    sessionStorage.setItem('aviso', 'No tienes permiso para ver esa página.');
    location.href = 'panel.html';
    return null;
  }
  return sesion;
}
