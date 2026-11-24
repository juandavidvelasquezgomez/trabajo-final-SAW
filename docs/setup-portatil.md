# Preparar el portátil (o cualquier equipo nuevo)

Se hace una sola vez por equipo. Ruta recomendada: `C:\dev\trabajo-final-SAW`, **fuera de OneDrive**.

## 1. Instalar herramientas
En PowerShell:

```powershell
winget install --id Git.Git -e --source winget
winget install --id GitHub.cli -e --source winget
```

Cierra y abre PowerShell para que tome el PATH nuevo, y comprueba:

```powershell
git --version
gh --version
```

## 2. Iniciar sesión en GitHub
```powershell
gh auth login --web --git-protocol https
```
Elige GitHub.com, HTTPS, "Yes" para autenticar Git, y aprueba el código en el navegador con la cuenta `juandavidvelasquezgomez`.

## 3. Configurar la identidad de Git
Debe ser la misma que en el otro equipo, para que los commits queden bajo un único autor:

```powershell
git config --global user.name "Juan David Velasquez"
git config --global user.email "juandavidvelasquezgomez@gmail.com"
git config --global init.defaultBranch main
```

## 4. Clonar el repositorio
```powershell
New-Item -ItemType Directory -Force C:\dev | Out-Null
Set-Location C:\dev
gh repo clone juandavidvelasquezgomez/trabajo-final-SAW
Set-Location trabajo-final-SAW
git status -sb
```

## 5. Después del código
Cuando exista código, sigue la sección "Configuración del Entorno" del `README.md` (dependencias, `.env` a partir de `.env.example`, base de datos y datos de prueba). El archivo `.env` es local de cada equipo y nunca se sube.

## 6. Rutina al cambiar de equipo
- Al empezar: `git pull` (y `git fetch` si hay ramas nuevas).
- Al terminar: commit y `git push`. No dejes trabajo sin subir.

---

## Texto para pegar en la sesión de Claude del portátil

Abre la app de escritorio de Claude en la carpeta `C:\dev\trabajo-final-SAW` y pega esto:

> Lee `CLAUDE.md` y `docs/requisitos.md` de este repositorio para tomar el contexto del proyecto. Comprueba que Git y GitHub CLI estén instalados y con sesión iniciada, que mi identidad de Git coincida con la indicada en `CLAUDE.md`, y que el repositorio esté al día con `main` y con sus ramas remotas. Dime en qué punto va el trabajo y qué sigue, sin modificar nada todavía.
