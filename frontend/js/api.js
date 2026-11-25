import { cerrarSesion, obtenerSesion } from './sesion.js';

export class ErrorApi extends Error {
  constructor(status, codigo, mensaje, detalles = []) {
    super(mensaje);
    this.status = status;
    this.codigo = codigo;
    this.mensaje = mensaje;
    this.detalles = detalles;
  }
}

/** Arma una query string ignorando los valores vacíos. */
export function qs(parametros) {
  const p = new URLSearchParams();
  for (const [clave, valor] of Object.entries(parametros)) {
    if (valor !== '' && valor !== null && valor !== undefined) p.set(clave, valor);
  }
  const texto = p.toString();
  return texto ? `?${texto}` : '';
}

/** Llama a la API. Si hay sesión, envía el token. Lanza ErrorApi con el mensaje del servidor. */
export async function api(ruta, { metodo = 'GET', cuerpo } = {}) {
  const cabeceras = {};
  if (cuerpo !== undefined) cabeceras['Content-Type'] = 'application/json';
  const sesion = obtenerSesion();
  if (sesion) cabeceras['Authorization'] = `Bearer ${sesion.token}`;

  let respuesta;
  try {
    respuesta = await fetch(`/api${ruta}`, {
      method: metodo,
      headers: cabeceras,
      body: cuerpo !== undefined ? JSON.stringify(cuerpo) : undefined,
    });
  } catch {
    throw new ErrorApi(0, 'SIN_CONEXION', 'No se pudo conectar con el servidor. Comprueba que esté en ejecución.');
  }

  let datos = null;
  try { datos = await respuesta.json(); } catch { /* respuesta sin cuerpo */ }

  if (!respuesta.ok) {
    const e = datos && datos.error ? datos.error : {};
    if (respuesta.status === 401 && sesion) {            // la sesión venció o dejó de ser válida
      cerrarSesion();
      sessionStorage.setItem('aviso', e.mensaje || 'La sesión venció. Inicia sesión de nuevo.');
      const pagina = location.pathname.split('/').pop() || 'index.html';
      location.href = `login.html?volver=${encodeURIComponent(pagina + location.search)}`;
    }
    throw new ErrorApi(respuesta.status, e.codigo || 'ERROR', e.mensaje || 'Ocurrió un error inesperado.', e.detalles || []);
  }
  return datos;
}
