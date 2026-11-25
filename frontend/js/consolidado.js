import { api, qs } from './api.js';
import { chipEstado, el, fechaHora, mostrarError, mostrarMensaje, pintarEncabezado, requerirSesion, validarRango } from './comun.js';

const sesion = requerirSesion(['coordinacion']);
if (sesion) iniciar();

function iniciar() {
  pintarEncabezado('consolidado');
  const form = document.getElementById('filtros');
  const mensaje = document.getElementById('mensaje');
  const kpis = document.getElementById('kpis');
  const tabla = document.getElementById('tabla');
  const porcentaje = (valor) => (valor === null || valor === undefined ? '—' : `${String(valor).replace('.', ',')} %`);

  const tarjeta = (numero, etiqueta) => el('div', { class: 'card kpi' }, el('div', { class: 'num' }, numero), el('div', { class: 'eti' }, etiqueta));

  function pintar({ totales, eventos }) {
    kpis.replaceChildren(
      tarjeta(totales.eventos, 'Eventos'),
      tarjeta(totales.inscripciones_activas, 'Inscripciones activas'),
      tarjeta(totales.asistentes, 'Asistentes'),
      tarjeta(porcentaje(totales.porcentaje_asistencia_finalizados), 'Asistencia en eventos finalizados'));
    tabla.replaceChildren(...(eventos.length
      ? eventos.map((e) => el('tr', {},
        el('td', {}, e.titulo), el('td', {}, fechaHora(e.inicio)), el('td', {}, chipEstado(e.estado)),
        el('td', {}, e.organizador.nombre), el('td', {}, e.cupo), el('td', {}, e.inscritos_activos),
        el('td', {}, e.cupos_disponibles), el('td', {}, e.asistentes), el('td', {}, porcentaje(e.porcentaje_asistencia))))
      : [el('tr', {}, el('td', { colspan: 9, class: 'vacio' }, 'No hay eventos con esos filtros.'))]));
  }

  async function cargar() {
    const filtros = Object.fromEntries(new FormData(form));
    const rangoInvalido = validarRango(filtros.desde, filtros.hasta);
    if (rangoInvalido) {
      mostrarMensaje(mensaje, 'error', rangoInvalido);
      return;
    }
    mensaje.replaceChildren();
    try {
      pintar(await api(`/consolidado${qs(filtros)}`));
    } catch (error) {
      mostrarError(mensaje, error);
    }
  }

  form.addEventListener('submit', (e) => { e.preventDefault(); cargar(); });

  api('/organizadores')
    .then((usuarios) => document.getElementById('f-organizador').append(...usuarios.map((u) => el('option', { value: u.id }, u.nombre))))
    .catch((error) => mostrarError(mensaje, error));
  cargar();
}
