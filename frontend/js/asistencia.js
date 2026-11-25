import { api } from './api.js';
import { chipEstado, el, fechaHora, mostrarError, mostrarMensaje, parametroId, pintarEncabezado, plural, rangoHorario,
         requerirSesion } from './comun.js';

const sesion = requerirSesion(['organizador', 'coordinacion']);
if (sesion) iniciar();

function iniciar() {
  pintarEncabezado('panel');
  const id = parametroId();
  const msgPagina = document.getElementById('msg-pagina');
  const msg = document.getElementById('msg-asistencia');
  const contenido = document.getElementById('contenido');
  const lista = document.getElementById('lista');
  const formMomento = document.getElementById('form-momento');
  const btnMomento = document.getElementById('btn-momento');
  const btnTodos = document.getElementById('btn-todos');
  let datos = null;

  if (id === null) {
    mostrarMensaje(msgPagina, 'error', 'El enlace no es válido: falta el identificador del evento.');
    return;
  }

  const TEXTO_VENTANA = {
    no_abierta: (v) => `El registro de asistencia abre el ${fechaHora(v.abre)}.`,
    abierta: (v) => `Registro abierto hasta ${fechaHora(v.registro_hasta)}. Se puede corregir hasta ${fechaHora(v.correccion_hasta)}.`,
    solo_correccion: (v) => `El plazo de registro terminó. Solo se pueden corregir asistencias ya registradas, hasta ${fechaHora(v.correccion_hasta)}.`,
    cerrada: () => 'El plazo terminó: la asistencia de este evento ya no se puede modificar.',
  };

  function pintar() {
    const { evento, ventana_asistencia: v, inscripciones } = datos;
    document.getElementById('titulo').textContent = `${evento.titulo} — Asistencia`;
    document.getElementById('subtitulo').textContent = `${evento.lugar} · ${rangoHorario(evento.inicio, evento.fin)}`;
    document.getElementById('banner').textContent = TEXTO_VENTANA[v.estado](v).replaceAll('..', '.');  // "a. m." ya lleva punto

    const activas = inscripciones.filter((i) => i.estado === 'activa');
    const presentes = activas.filter((i) => i.asistencia === 'presente').length;
    document.getElementById('resumen').textContent = `${presentes} de ${activas.length} presentes · ${plural(activas.length, 'inscrito activo', 'inscritos activos')}`;

    const ahora = new Date();
    const enCurso = evento.estado === 'publicado' && ahora >= new Date(evento.inicio) && ahora < new Date(evento.fin);
    btnMomento.classList.toggle('invisible', !enCurso);
    if (!enCurso) formMomento.classList.add('invisible');
    btnTodos.disabled = v.estado !== 'abierta' || activas.every((i) => i.asistencia === 'presente');

    const filas = [...activas, ...inscripciones.filter((i) => i.estado !== 'activa')].map((i) => fila(i, v));
    lista.replaceChildren(...(filas.length ? filas : [el('tr', {}, el('td', { colspan: 5, class: 'vacio' }, 'Este evento todavía no tiene inscritos.'))]));
  }

  function fila(i, ventana) {
    const activa = i.estado === 'activa';
    const bloqueada = !activa || ventana.estado === 'no_abierta' || ventana.estado === 'cerrada'
      || (ventana.estado === 'solo_correccion' && !i.asistencia_registrada_en);
    const opcion = (texto, clase, valor) => el('button', {
      type: 'button', class: `${clase}${i.asistencia === valor ? ' on' : ''}`, disabled: bloqueada,
      'aria-pressed': String(i.asistencia === valor), onclick: () => marcar(i, valor),
    }, texto);
    const quitar = activa && i.asistencia !== 'presente' && ventana.estado !== 'cerrada'
      ? el('button', { class: 'btn peligro peq', type: 'button', onclick: () => quitarInscripcion(i) }, 'Quitar') : null;
    return el('tr', {},
      el('td', {}, el('strong', {}, i.participante.nombre_completo), i.en_el_momento ? el('span', { class: 'chip aviso', style: 'margin-left:6px' }, 'en el momento') : null),
      el('td', {}, i.participante.correo),
      el('td', {}, i.participante.rol),
      el('td', {}, activa ? el('span', { class: 'seg' }, opcion('Presente', 'pres', 'presente'), opcion('Ausente', 'aus', 'ausente'))
                          : el('span', { class: 'chip gris' }, i.estado === 'cancelada' ? 'Cancelada' : 'Cancelada por el evento')),
      el('td', {}, quitar));
  }

  async function cargar() {
    try {
      datos = await api(`/eventos/${id}/inscripciones`);
      contenido.classList.remove('invisible');
      document.title = `Asistencia · ${datos.evento.titulo}`;
      pintar();
    } catch (error) {
      contenido.classList.add('invisible');
      mostrarMensaje(msgPagina, 'error', error.status === 404 ? 'El evento no existe.' : error.mensaje);
    }
  }

  async function marcar(i, estado) {
    if (i.asistencia === estado && i.asistencia_registrada_en) return;   // ya estaba registrado así
    try {
      await api(`/eventos/${id}/asistencia/${i.id}`, { metodo: 'PUT', cuerpo: { estado } });
      mostrarMensaje(msg, 'ok', '');
    } catch (error) {
      mostrarError(msg, error);
    }
    await cargar();
  }

  async function quitarInscripcion(i) {
    if (!confirm(`¿Quitar la inscripción de ${i.participante.nombre_completo}? Se libera su cupo.`)) return;
    try {
      await api(`/inscripciones/${i.id}`, { metodo: 'PATCH', cuerpo: { estado: 'cancelada' } });
      mostrarMensaje(msg, 'ok', 'Inscripción cancelada.');
    } catch (error) {
      mostrarError(msg, error);
    }
    await cargar();
  }

  btnTodos.addEventListener('click', async () => {
    const pendientes = datos.inscripciones.filter((i) => i.estado === 'activa' && i.asistencia !== 'presente').map((i) => i.id);
    if (!pendientes.length) return;
    try {
      const r = await api(`/eventos/${id}/asistencia/lote`, { metodo: 'POST', cuerpo: { inscripcion_ids: pendientes, estado: 'presente' } });
      mostrarMensaje(msg, 'ok', r.actualizadas === 1 ? 'Se marcó 1 participante como presente.' : `Se marcaron ${r.actualizadas} participantes como presentes.`);
    } catch (error) {
      mostrarError(msg, error);
    }
    await cargar();
  });

  btnMomento.addEventListener('click', () => formMomento.classList.toggle('invisible'));

  formMomento.addEventListener('submit', async (e) => {
    e.preventDefault();
    const msgMomento = document.getElementById('msg-momento');
    if (!formMomento.reportValidity()) return;
    try {
      const r = await api(`/eventos/${id}/inscripciones/en-el-momento`, { metodo: 'POST', cuerpo: Object.fromEntries(new FormData(formMomento)) });
      mostrarMensaje(msg, 'ok', `${r.participante.nombre_completo} quedó inscrito y presente. Cupos disponibles: ${r.cupos_disponibles}.`);
      mostrarMensaje(msgMomento, 'ok', '');
      formMomento.reset();
      formMomento.classList.add('invisible');
      await cargar();
    } catch (error) {
      mostrarError(msgMomento, error);
    }
  });

  cargar();
}
