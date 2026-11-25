import { api, qs } from './api.js';
import { barraCupo, chipTipo, el, mostrarError, mostrarMensaje, pintarEncabezado, plural, rangoHorario, validarRango } from './comun.js';

pintarEncabezado('catalogo');
const form = document.getElementById('filtros');
const lista = document.getElementById('lista');
const mensaje = document.getElementById('mensaje');

function disponibilidad(e) {
  if (e.cupos_disponibles === 0) return el('span', { class: 'chip error' }, 'Agotado');
  const pocos = e.inscritos_activos > 0 && e.cupos_disponibles <= Math.max(3, Math.ceil(e.cupo * 0.1));
  return el('span', { class: `chip ${pocos ? 'aviso' : 'ok'}` }, pocos ? 'Últimos cupos' : 'Cupos disponibles');
}

function tarjeta(e) {
  return el('article', { class: 'card evento' },
    chipTipo(e.tipo), ' ', disponibilidad(e),
    el('h3', {}, e.titulo),
    el('p', { class: 'meta' }, rangoHorario(e.inicio, e.fin)),
    el('p', { class: 'meta' }, e.lugar),
    barraCupo(e.inscritos_activos, e.cupo),
    el('p', { class: 'meta' }, `${plural(e.inscritos_activos, 'inscrito', 'inscritos')} · `, el('strong', {}, plural(e.cupos_disponibles, 'cupo', 'cupos')), ` de ${e.cupo}`),
    el('p', { style: 'margin:12px 0 0' },
      el('a', { class: `btn peq${e.cupos_disponibles ? '' : ' sec'}`, href: `evento.html?id=${e.id}` }, 'Ver detalle')));
}

async function cargar() {
  const desde = form.desde.value;
  const hasta = form.hasta.value;
  const rangoInvalido = validarRango(desde, hasta);
  if (rangoInvalido) {                       // se avisa antes de consultar, con el mismo texto que da la API
    mostrarMensaje(mensaje, 'error', rangoInvalido);
    lista.replaceChildren();
    return;
  }
  mensaje.replaceChildren();
  try {
    const eventos = await api(`/eventos${qs({ tipo: form.tipo.value, desde, hasta })}`);
    lista.replaceChildren(...(eventos.length
      ? eventos.map(tarjeta)
      : [el('p', { class: 'vacio', style: 'grid-column:1/-1' }, 'No hay eventos próximos con esos filtros.')]));
  } catch (error) {
    lista.replaceChildren();
    mostrarError(mensaje, error);
  }
}

form.addEventListener('submit', (e) => { e.preventDefault(); cargar(); });
cargar();
