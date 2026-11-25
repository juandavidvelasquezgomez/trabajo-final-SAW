# Preparar el portátil (o cualquier equipo nuevo)

Instalación y configuración una sola vez por equipo. Ruta recomendada: `C:\dev\trabajo-final-SAW`, **fuera de OneDrive**. Requiere internet para instalar. Calcula 15 minutos.

## 1. Instalar herramientas

En PowerShell:

```powershell
winget install --id Git.Git -e --source winget
```

```powershell
winget install --id GitHub.cli -e --source winget
```

```powershell
winget install --id Python.Python.3.14 -e --source winget
```

**Cierra y abre PowerShell** y comprueba (Python debe ser 3.12 o superior; el proyecto se probó con 3.14):

```powershell
git --version; gh --version; python --version
```

Si `python` abre la Microsoft Store, desactiva los alias de ejecución de aplicaciones de Python en la configuración de Windows, o usa `py` en su lugar.

## 2. Iniciar sesión en GitHub y configurar tu identidad

```powershell
gh auth login --web --git-protocol https
```

Elige GitHub.com, HTTPS, "Yes" para autenticar Git, y aprueba el código con la cuenta `juandavidvelasquezgomez`.

```powershell
git config --global user.name "Juan David Velasquez"
```

```powershell
git config --global user.email "juandavidvelasquezgomez@gmail.com"
```

## 3. Clonar el repositorio

```powershell
New-Item -ItemType Directory -Force C:\dev | Out-Null; Set-Location C:\dev; gh repo clone juandavidvelasquezgomez/trabajo-final-SAW
```

Si ya lo habías clonado: `Set-Location C:\dev\trabajo-final-SAW; git pull`.

## 4. Instalar dependencias

```powershell
Set-Location C:\dev\trabajo-final-SAW\backend; python -m venv .venv; .\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
```

## 5. Crear el archivo `.env`

El archivo `.env` es de cada equipo y **no viene en el repositorio**.

```powershell
Copy-Item ..\.env.example ..\.env
```

```powershell
.\.venv\Scripts\python.exe -c "import secrets; print(secrets.token_urlsafe(48))"
```

```powershell
notepad ..\.env
```

En el Bloc de notas: pega la clave generada después de `SECRET_KEY=` y escribe una contraseña para las cuentas de prueba después de `SEED_PASSWORD=` (10 caracteres o más, con letras y números). Guarda y cierra.

## 6. Comprobar que todo funciona

```powershell
.\.venv\Scripts\python.exe -m pytest
```

Todas las pruebas deben pasar.

## 7. Preparar la demostración (15 minutos antes de sustentar)

Con el servidor apagado:

```powershell
.\.venv\Scripts\python.exe db\seed.py --reiniciar
```

```powershell
.\.venv\Scripts\python.exe db\preparar_demo.py
```

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app
```

Abre http://127.0.0.1:8000/ y http://127.0.0.1:8000/docs. Cuentas: `coordinacion@ejemplo.test`, `ana.torres@ejemplo.test`, `luis.mora@ejemplo.test`.

Lista de verificación en el portátil:

- [ ] El catálogo muestra eventos y el detalle muestra el código QR.
- [ ] Puedes ingresar como coordinación y ver el consolidado.
- [ ] La asistencia del evento "Demostración en vivo" permite marcar.
- [ ] La constancia de `laura.gomez@ejemplo.test` con documento `1000000001` aparece.
- [ ] Conectado al proyector, las páginas se leen bien (zoom 125 %).

## 8. Rutina al cambiar de equipo

- Al empezar: `git pull`.
- Al terminar: commit y `git push`. No dejes trabajo sin subir.

---

## Texto para pegar en la sesión de Claude del portátil

Abre la app de escritorio de Claude en la carpeta `C:\dev\trabajo-final-SAW` y pega esto:

> Lee `CLAUDE.md`, `README.md` y `docs/setup-portatil.md`. Verifica en este equipo que Git, GitHub CLI y Python estén instalados, que el repositorio esté al día con `main`, que las dependencias y el archivo `.env` estén listos y que las pruebas pasen. No muestres secretos. Dime qué falta antes de modificar algo.
