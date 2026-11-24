import { api } from './api.js';
import { avisoPendiente, mostrarError, pintarEncabezado } from './comun.js';
import { cerrarSesion, guardarSesion } from './sesion.js';

pintarEncabezado('login');
const form = document.getElementById('form-login');
const boton = document.getElementById('btn-login');
const mensaje = document.getElementById('mensaje');
avisoPendiente(document.getElementById('aviso'));

/** Solo se vuelve a páginas propias (evita redirecciones a otros sitios). */
function destino() {
  const volver = new URLSearchParams(location.search).get('volver') || '';
  return /^[a-z]+\.html(\?[\w=&%.-]*)?$/.test(volver) ? volver : 'panel.html';
}

form.addEventListener('submit', async (e) => {
  e.preventDefault();
  if (!form.reportValidity()) return;
  cerrarSesion();                                   // un intento nuevo parte sin sesión previa
  boton.disabled = true;
  try {
    const r = await api('/auth/login', { metodo: 'POST', cuerpo: Object.fromEntries(new FormData(form)) });
    guardarSesion(r.access_token, r.usuario, r.expira_en);
    location.href = destino();
  } catch (error) {
    form.password.value = '';
    mostrarError(mensaje, error);
    boton.disabled = false;
  }
});
