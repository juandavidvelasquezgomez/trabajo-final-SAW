import { api, qs } from './api.js';
import { aIsoBogota, ahoraBogota, aLocalBogota, TIPOS, avisoPendiente, chipEstado, desdeLocalBogota, el, fechaHora,
         mostrarError, mostrarMensaje, pintarEncabezado, requerirSesion } from './comun.js';

const sesion = requerirSesion(['organizador', 'coordinacion']);
if (sesion) iniciar();

function iniciar() {
  pintarEncabezado('panel');
  const esCoordinacion = sesion.usuario.rol === 'coordinacion';
  const f = document.getElementById('form-evento');
  const tabla = document.getElementById('tabla');
  const msgPanel = document.getElementById('msg-panel');
  const msgForm = document.getElementById('msg-form');
  const filtroEstado = document.getElementById('f-estado');
  const btnPublicar = document.getElementById('btn-publicar');
  const btnCancelarEdicion = document.getElementById('btn-cancelar-edicion');
  let editando = null;                              // evento que se está editando (o null si se crea uno nuevo)

  avisoPendiente(msgPanel);
  document.getElementById('subtitulo').textContent = esCoordinacion
    ? 'Todos los eventos de la institución.' : 'Tus eventos y su estado.';
  if (esCoordinacion) {
    document.getElementById('th-organizador').classList.remove('invisible');
    document.getElementById('campo-organizador').classList.remove('invisible');
  }

  // ------------------------------------------------------------------- fechas
  // Las fechas pasadas quedan deshabilitadas: solo se consultan como historial.
  // Es una ayuda de la interfaz; la regla real la aplica el servidor (RN-09).
  function limitesDeFechas() {
    if (f.inicio.disabled) return;                  // evento ya iniciado: sus fechas no se editan
    f.inicio.min = ahoraBogota();
    if (f.inicio.value && f.inicio.value < f.inicio.min) f.inicio.value = '';
    if (!f.inicio.value) {
      f.fin.value = '';
      f.fin.disabled = true;
      f.fin.removeAttribute('min');
      f.fin.removeAttribute('max');
      return;
    }
    const inicio = desdeLocalBogota(f.inicio.value);
    f.fin.disabled = false;
    f.fin.min = aLocalBogota(new Date(inicio.getTime() + 60 * 1000));
    f.fin.max = aLocalBogota(new Date(inicio.getTime() + 8 * 3600 * 1000));
    if (f.fin.value && (f.fin.value < f.fin.min || f.fin.value > f.fin.max)) f.fin.value = '';
  }
  f.inicio.addEventListener('change', limitesDeFechas);
  f.inicio.addEventListener('focus', limitesDeFechas);

  // ------------------------------------------------------------------- tabla
  function acciones(ev) {
    const boton = (texto, clase, accion) => el('button', { class: `btn ${clase} peq`, type: 'button', onclick: accion }, texto);
    const enlace = (texto, clase) => el('a', { class: `btn ${clase} peq`, href: `asistencia.html?id=${ev.id}` }, texto);
    if (ev.estado === 'borrador') return [boton('Editar', 'sec', () => editar(ev)), boton('Publicar', '', () => cambiarEstado(ev, 'publicado')), boton('Cancelar', 'peligro', () => cambiarEstado(ev, 'cancelado'))];
    if (ev.estado === 'publicado') return [boton('Editar', 'sec', () => editar(ev)), enlace('Asistencia', ''), boton('Cancelar', 'peligro', () => cambiarEstado(ev, 'cancelado'))];
    if (ev.estado === 'finalizado') return [enlace('Ver asistencia', 'sec')];
    return [];
  }

  function fila(ev) {
    return el('tr', {},
      el('td', {}, el('strong', {}, ev.titulo), el('br'), el('span', { class: 'meta' }, TIPOS[ev.tipo])),
      el('td', {}, fechaHora(ev.inicio)),
      el('td', {}, chipEstado(ev.estado)),
      el('td', {}, `${ev.inscritos_activos} / ${ev.cupo}`),
      esCoordinacion ? el('td', {}, ev.organizador.nombre) : null,
      el('td', { class: 'acciones' }, acciones(ev)));
  }

  async function cargar() {
    try {
      const eventos = await api(`/panel/eventos${qs({ estado: filtroEstado.value })}`);
      tabla.replaceChildren(...(eventos.length
        ? eventos.map(fila)
        : [el('tr', {}, el('td', { colspan: 6, class: 'vacio' }, 'No hay eventos para mostrar.'))]));
    } catch (error) {
      mostrarError(msgPanel, error);
    }
  }

  async function cambiarEstado(ev, estado) {
    if (estado === 'cancelado' && !confirm(`¿Cancelar «${ev.titulo}»?\nLas inscripciones activas se conservarán como canceladas por el evento.`)) return;
    try {
      await api(`/eventos/${ev.id}/estado`, { metodo: 'PATCH', cuerpo: { estado } });
      mostrarMensaje(msgPanel, 'ok', estado === 'publicado' ? 'Evento publicado.' : 'Evento cancelado.');
      await cargar();
    } catch (error) {
      mostrarError(msgPanel, error);
    }
  }

  // --------------------------------------------------------------- formulario
  async function cargarOrganizadores() {
    if (!esCoordinacion) return;
    const select = document.getElementById('ev-organizador');
    const usuarios = await api('/organizadores');
    select.replaceChildren(...usuarios.map((u) =>
      el('option', { value: u.id }, u.id === sesion.usuario.id ? `Yo (${u.nombre})` : `${u.nombre} (${u.rol === 'coordinacion' ? 'coordinación' : u.rol})`)));
    select.value = String(sesion.usuario.id);
  }

  function reiniciarFormulario() {
    editando = null;
    f.reset();
    f.inicio.disabled = false;
    f.fin.disabled = true;
    if (esCoordinacion) f.organizador_id.value = String(sesion.usuario.id);
    document.getElementById('titulo-form').textContent = 'Nuevo evento';
    document.getElementById('btn-guardar').textContent = 'Guardar borrador';
    btnPublicar.classList.remove('invisible');
    btnCancelarEdicion.classList.add('invisible');
    mostrarMensaje(msgForm, 'ok', '');
    limitesDeFechas();
  }

  function editar(ev) {
    editando = ev;
    f.titulo.value = ev.titulo;
    f.tipo.value = ev.tipo;
    f.lugar.value = ev.lugar;
    f.cupo.value = ev.cupo;
    f.descripcion.value = ev.descripcion || '';
    f.imagen_url.value = ev.imagen_url || '';
    if (esCoordinacion) f.organizador_id.value = String(ev.organizador.id);
    // Un evento publicado que ya inició conserva sus fechas; un borrador vencido se puede reprogramar.
    const iniciado = ev.estado === 'publicado' && new Date() >= new Date(ev.inicio);
    f.inicio.disabled = iniciado;
    f.fin.disabled = iniciado;
    f.inicio.value = ev.inicio.slice(0, 16);        // la API devuelve la hora de Colombia
    f.fin.value = ev.fin.slice(0, 16);
    if (!iniciado) {
      limitesDeFechas();                            // si la fecha ya pasó, se vacía para elegir una nueva
      if (f.inicio.value) f.fin.value = ev.fin.slice(0, 16);
    }
    document.getElementById('titulo-form').textContent = `Editar evento: ${ev.titulo}`;
    document.getElementById('btn-guardar').textContent = 'Guardar cambios';
    btnPublicar.classList.add('invisible');
    btnCancelarEdicion.classList.remove('invisible');
    mostrarMensaje(msgForm, iniciado ? 'aviso' : 'ok', iniciado ? 'Este evento ya inició: sus fechas no se pueden modificar.' : '');
    f.scrollIntoView({ behavior: 'smooth' });
  }

  function cuerpoCreacion() {
    const cuerpo = {
      titulo: f.titulo.value, tipo: f.tipo.value, lugar: f.lugar.value,
      inicio: aIsoBogota(f.inicio.value), fin: aIsoBogota(f.fin.value),
      cupo: f.cupo.value === '' ? null : Number(f.cupo.value),
    };
    if (f.descripcion.value.trim()) cuerpo.descripcion = f.descripcion.value;
    if (f.imagen_url.value.trim()) cuerpo.imagen_url = f.imagen_url.value;
    if (esCoordinacion) cuerpo.organizador_id = Number(f.organizador_id.value);
    return cuerpo;
  }

  /** Solo se envía lo que cambió, para no tocar nada más. */
  function diferencias() {
    const cambios = {};
    const original = editando;
    if (f.titulo.value !== original.titulo) cambios.titulo = f.titulo.value;
    if (f.tipo.value !== original.tipo) cambios.tipo = f.tipo.value;
    if (f.lugar.value !== original.lugar) cambios.lugar = f.lugar.value;
    if (Number(f.cupo.value) !== original.cupo) cambios.cupo = Number(f.cupo.value);
    if (f.descripcion.value !== (original.descripcion || '')) cambios.descripcion = f.descripcion.value.trim() ? f.descripcion.value : null;
    if (f.imagen_url.value !== (original.imagen_url || '')) cambios.imagen_url = f.imagen_url.value.trim() ? f.imagen_url.value : null;
    if (!f.inicio.disabled) {
      if (f.inicio.value !== original.inicio.slice(0, 16)) cambios.inicio = aIsoBogota(f.inicio.value);
      if (f.fin.value !== original.fin.slice(0, 16)) cambios.fin = aIsoBogota(f.fin.value);
    }
    if (esCoordinacion && Number(f.organizador_id.value) !== original.organizador.id) cambios.organizador_id = Number(f.organizador_id.value);
    return cambios;
  }

  async function guardar(publicar) {
    mostrarMensaje(msgForm, 'ok', '');
    if (!f.reportValidity()) return;
    try {
      if (editando) {
        const cambios = diferencias();
        if (!Object.keys(cambios).length) { mostrarMensaje(msgForm, 'aviso', 'No hay cambios que guardar.'); return; }
        await api(`/eventos/${editando.id}`, { metodo: 'PUT', cuerpo: cambios });
        mostrarMensaje(msgPanel, 'ok', 'Evento actualizado.');
      } else {
        const creado = await api('/eventos', { metodo: 'POST', cuerpo: cuerpoCreacion() });
        if (publicar) {
          try {
            await api(`/eventos/${creado.id}/estado`, { metodo: 'PATCH', cuerpo: { estado: 'publicado' } });
            mostrarMensaje(msgPanel, 'ok', 'Evento creado y publicado.');
          } catch (error) {
            mostrarMensaje(msgPanel, 'aviso', `El evento se guardó como borrador, pero no se pudo publicar: ${error.mensaje}`);
          }
        } else {
          mostrarMensaje(msgPanel, 'ok', 'Evento guardado como borrador.');
        }
      }
      reiniciarFormulario();
      await cargar();
      window.scrollTo({ top: 0, behavior: 'smooth' });
    } catch (error) {
      mostrarError(msgForm, error);
    }
  }

  f.addEventListener('submit', (e) => { e.preventDefault(); guardar(false); });
  btnPublicar.addEventListener('click', () => guardar(true));
  btnCancelarEdicion.addEventListener('click', reiniciarFormulario);
  document.getElementById('btn-nuevo').addEventListener('click', () => { reiniciarFormulario(); f.scrollIntoView({ behavior: 'smooth' }); f.titulo.focus(); });
  filtroEstado.addEventListener('change', cargar);

  limitesDeFechas();
  cargarOrganizadores().catch((error) => mostrarError(msgForm, error));
  cargar();
}
