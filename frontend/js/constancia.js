import { api } from './api.js';
import { el, fechaLarga, hora, mostrarError, mostrarMensaje, pintarEncabezado, TIPOS } from './comun.js';

pintarEncabezado('constancia');
const formObtener = document.getElementById('form-obtener');
const formVerificar = document.getElementById('form-verificar');
const resultados = document.getElementById('resultados');
const msgObtener = document.getElementById('msg-obtener');
const msgVerificar = document.getElementById('msg-verificar');

function imprimir(tarjeta) {
  tarjeta.classList.add('para-imprimir');                 // solo se imprime la constancia elegida
  document.body.classList.add('imprimiendo');
  window.print();
  tarjeta.classList.remove('para-imprimir');
  document.body.classList.remove('imprimiendo');
}

function constancia(c) {
  const { participante: p, evento: e } = c;
  const enlace = `${location.origin}/constancia.html?codigo=${c.codigo}`;
  const horas = String(e.duracion_horas).replace('.', ',');
  const tarjeta = el('article', { class: 'card constancia' },
    el('p', { class: 'constancia-marca' }, 'Eventos Académicos'),
    el('h2', {}, 'Constancia de asistencia'),
    el('p', {}, 'Se hace constar que'),
    el('p', { class: 'constancia-nombre' }, p.nombre_completo),
    el('p', {}, `identificado(a) con documento ${p.documento}, asistió a la actividad`),
    el('p', { class: 'constancia-evento' }, `${TIPOS[e.tipo] || e.tipo}: «${e.titulo}»`),
    el('p', {}, `realizada el ${fechaLarga(e.inicio)}, de ${hora(e.inicio)} a ${hora(e.fin)} (hora de Colombia), en ${e.lugar}.`),
    el('p', {}, `Duración: ${horas} horas · Organiza: ${e.organizador}`),
    el('div', { class: 'constancia-pie' },
      el('img', { src: `/api/constancias/${encodeURIComponent(c.codigo)}/qr`, alt: 'Código QR para verificar la constancia', width: 130, height: 130 }),
      el('div', {},
        el('p', {}, el('strong', {}, `Código: ${c.codigo}`)),
        el('p', { class: 'meta' }, `Verificar en: ${enlace}`),
        el('p', { class: 'meta' }, 'Documento generado automáticamente. No tiene firma digital.'))));
  const boton = el('button', { class: 'btn no-imprimir', type: 'button', onclick: () => imprimir(tarjeta) }, 'Imprimir o guardar como PDF');
  return el('div', { class: 'bloque-constancia' }, tarjeta, el('p', { class: 'no-imprimir' }, boton));
}

formObtener.addEventListener('submit', async (ev) => {
  ev.preventDefault();
  if (!formObtener.reportValidity()) return;
  resultados.replaceChildren();
  msgVerificar.replaceChildren();
  try {
    const lista = await api('/constancias', { metodo: 'POST', cuerpo: Object.fromEntries(new FormData(formObtener)) });
    mostrarMensaje(msgObtener, 'ok', lista.length === 1 ? 'Se encontró 1 constancia.' : `Se encontraron ${lista.length} constancias.`);
    resultados.replaceChildren(...lista.map(constancia));
  } catch (error) {
    mostrarError(msgObtener, error);
  }
});

async function verificar(codigo) {
  resultados.replaceChildren();
  msgObtener.replaceChildren();
  try {
    const c = await api(`/constancias/${encodeURIComponent(codigo.trim())}`);
    mostrarMensaje(msgVerificar, 'ok', 'Constancia válida: coincide con los registros de asistencia.');
    resultados.replaceChildren(constancia(c));
  } catch (error) {
    mostrarError(msgVerificar, error);
  }
}

formVerificar.addEventListener('submit', (ev) => {
  ev.preventDefault();
  if (formVerificar.reportValidity()) verificar(formVerificar.codigo.value);
});

const codigoEnLaDireccion = new URLSearchParams(location.search).get('codigo');
if (codigoEnLaDireccion) {
  formVerificar.codigo.value = codigoEnLaDireccion;
  verificar(codigoEnLaDireccion);
}
