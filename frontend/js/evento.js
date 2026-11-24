import { api } from './api.js';
import { barraCupo, chipTipo, el, mostrarError, mostrarMensaje, parametroId, pintarEncabezado, rangoHorario } from './comun.js';

pintarEncabezado('catalogo');
const id = parametroId();
const mensajeEvento = document.getElementById('mensaje-evento');
const contenido = document.getElementById('contenido');
const detalle = document.getElementById('detalle');
const formInscripcion = document.getElementById('form-inscripcion');
const formCancelar = document.getElementById('form-cancelar');
const botonInscribir = document.getElementById('btn-inscribir');
const avisoInscripcion = document.getElementById('aviso-inscripcion');
let inscripcionCerrada = false;

function pintarDetalle(e) {
  const pocos = e.cupos_disponibles > 0 && e.cupos_disponibles <= Math.max(3, Math.ceil(e.cupo * 0.1));
  const chipCupos = e.cupos_disponibles === 0 ? ['error', 'Agotado'] : pocos ? ['aviso', 'Últimos cupos'] : ['ok', 'Cupos disponibles'];
  const imagen = e.imagen_url && e.imagen_url.startsWith('https://')
    ? el('img', { class: 'portada', src: e.imagen_url, alt: '', referrerpolicy: 'no-referrer' }) : null;
  detalle.replaceChildren(...[       // replaceChildren convierte un null en el texto "null": se descartan los vacíos
    chipTipo(e.tipo), ' ', el('span', { class: `chip ${chipCupos[0]}` }, chipCupos[1]),
    el('h1', { style: 'margin-top:8px' }, e.titulo),
    el('p', { class: 'meta' }, `${rangoHorario(e.inicio, e.fin)} (hora de Colombia)`),
    el('p', { class: 'meta' }, `${e.lugar} · Organiza: ${e.organizador.nombre}`),
    barraCupo(e.inscritos_activos, e.cupo),
    el('p', { class: 'meta' }, el('strong', {}, `${e.cupos_disponibles} cupos disponibles`), ` de ${e.cupo}`),
    imagen,
    e.descripcion ? el('p', { style: 'white-space:pre-line' }, e.descripcion) : null,
  ].filter((nodo) => nodo !== null));
  document.title = `${e.titulo} · Eventos académicos`;

  // El formulario se bloquea cuando no se puede inscribir; el servidor lo vuelve a comprobar.
  const iniciado = new Date() >= new Date(e.inicio);
  inscripcionCerrada = e.cupos_disponibles === 0 || iniciado;
  botonInscribir.disabled = inscripcionCerrada;
  mostrarMensaje(avisoInscripcion, 'aviso',
    iniciado ? 'Las inscripciones cierran cuando el evento inicia.'
      : e.cupos_disponibles === 0 ? 'Este evento ya no tiene cupos disponibles.' : '');
}

async function cargar() {
  try {
    pintarDetalle(await api(`/eventos/${id}`));
    contenido.classList.remove('invisible');
  } catch (error) {
    contenido.classList.add('invisible');
    mostrarMensaje(mensajeEvento, 'error', error.status === 404 ? 'El evento no existe o no está disponible.' : error.mensaje);
  }
}

formInscripcion.addEventListener('submit', async (ev) => {
  ev.preventDefault();
  const msg = document.getElementById('msg-inscripcion');
  if (!formInscripcion.reportValidity()) return;
  const datos = Object.fromEntries(new FormData(formInscripcion));
  if (!datos.programa) delete datos.programa;
  botonInscribir.disabled = true;
  try {
    const r = await api(`/eventos/${id}/inscripciones`, { metodo: 'POST', cuerpo: datos });
    mostrarMensaje(msg, 'ok', `Inscripción confirmada. Quedan ${r.cupos_disponibles} cupos.`);
    formInscripcion.reset();
  } catch (error) {
    mostrarError(msg, error);
  }
  await cargar();                      // refresca los cupos y el estado del botón
  if (inscripcionCerrada) botonInscribir.disabled = true; else botonInscribir.disabled = false;
});

formCancelar.addEventListener('submit', async (ev) => {
  ev.preventDefault();
  const msg = document.getElementById('msg-cancelar');
  if (!formCancelar.reportValidity()) return;
  try {
    const r = await api(`/eventos/${id}/inscripciones/cancelar`, { metodo: 'POST', cuerpo: Object.fromEntries(new FormData(formCancelar)) });
    mostrarMensaje(msg, 'ok', `Inscripción cancelada. Ahora hay ${r.cupos_disponibles} cupos disponibles.`);
    formCancelar.reset();
    await cargar();
  } catch (error) {
    mostrarError(msg, error);
  }
});

if (id === null) {
  mostrarMensaje(mensajeEvento, 'error', 'El enlace no es válido: falta el identificador del evento.');
} else {
  cargar();
}
