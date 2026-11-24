// La sesión vive solo mientras la pestaña esté abierta (sessionStorage) y vence con el token,
// que caduca a las 00:00 de Colombia.
const CLAVE = 'sesion';

export function guardarSesion(token, usuario, expiraEn) {
  sessionStorage.setItem(CLAVE, JSON.stringify({ token, usuario, expiraEn }));
}

export function cerrarSesion() {
  sessionStorage.removeItem(CLAVE);
}

export function obtenerSesion() {
  try {
    const sesion = JSON.parse(sessionStorage.getItem(CLAVE));
    if (!sesion) return null;
    if (new Date(sesion.expiraEn) <= new Date()) {
      cerrarSesion();
      return null;
    }
    return sesion;
  } catch {
    return null;
  }
}
