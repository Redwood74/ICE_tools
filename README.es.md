# ICEpicks

[🇺🇸 Read in English](README.md)

**ICEpicks** es una herramienta de automatización local que monitorea el
[Localizador de Detenidos en Línea de ICE](https://locator.ice.gov/odls/#/index)
buscando a una persona específica por su número de registro de extranjero
(A-number) y país de origen.

> ⚠️ **El sitio del localizador de ICE es conocido por devolver falsos
> "0 Resultados de Búsqueda" entre resultados reales.** ICEpicks realiza
> múltiples intentos nuevos por cada verificación programada y clasifica
> los resultados de forma conservadora para que pueda distinguir un resultado
> positivo creíble del ruido del sitio.

---

## Qué hace

1. Abre el localizador de ICE en un navegador Chromium sin interfaz gráfica
   (vía Playwright).
2. Ingresa el A-number y el país, luego hace clic en Buscar.
3. Repite hasta N veces por ejecución, cada una en un **contexto de navegador
   nuevo**.
4. Clasifica el resultado: `ZERO_RESULT`, `LIKELY_POSITIVE`,
   `AMBIGUOUS_REVIEW`, `BOT_CHALLENGE_OR_BLOCKED`, o `ERROR`.
5. Guarda capturas de pantalla, HTML y texto extraído como artefactos locales.
6. Envía una notificación de Microsoft Teams **solamente** cuando aparece un
   nuevo resultado positivo creíble (la deduplicación previene alertas
   repetidas por el mismo registro).

## ¿Por qué múltiples intentos por ejecución?

El localizador de ICE es una aplicación de página única (SPA) inestable que
frecuentemente devuelve `0 Resultados de Búsqueda` incluso cuando una persona
está activamente detenida. Ejecutar varios intentos independientes (cada uno
con una sesión de navegador nueva) reduce significativamente la probabilidad
de un falso negativo en cualquier verificación.

> **Los resultados no son autoritativos.** Un `ZERO_RESULT` no confirma que
> una persona *no* está detenida. Un `LIKELY_POSITIVE` no reemplaza la
> verificación legal oficial. Siempre revise los artefactos guardados y
> compare con fuentes oficiales.

---

## Requisitos

- Python 3.10 o más reciente
- Windows 10/11 (también funciona en macOS/Linux para desarrollo)
- No se requieren derechos de administrador
- No se requiere Docker

---

## Instalación local (Windows)

```powershell
# 1. Clonar el repositorio
git clone https://github.com/Redwood74/ICEpicks.git
cd ICEpicks

# 2. Crear y activar un entorno virtual
python -m venv .venv
.venv\Scripts\Activate.ps1

# 3. Instalar dependencias
pip install -r requirements.txt
pip install -e .          # instala el CLI findice

# 4. Instalar el navegador Playwright
playwright install chromium

# 5. Copiar la configuración de ejemplo
copy .env.example .env
# Luego edite .env y complete A_NUMBER, COUNTRY, TEAMS_WEBHOOK_URL
```

> Consulte [`docs/windows_task_scheduler.md`](docs/windows_task_scheduler.md)
> para orientación sobre la programación de tareas.

---

## Variables de entorno

| Variable | Requerida | Predeterminado | Descripción |
|---|---|---|---|
| `A_NUMBER` | ✅ | — | Número de registro de extranjero (8–9 dígitos) |
| `COUNTRY` | ✅ | — | País de origen como aparece en el localizador de ICE |
| `TEAMS_WEBHOOK_URL` | ☐ | — | URL del webhook entrante de Teams (vacío = ejecución en seco) |
| `ATTEMPTS_PER_RUN` | ☐ | `4` | Número de intentos nuevos por ejecución |
| `ATTEMPT_DELAY_SECONDS` | ☐ | `5.0` | Segundos entre intentos |
| `HEADLESS` | ☐ | `true` | Establezca `false` para ver el navegador |
| `DRY_RUN` | ☐ | `false` | Omitir notificación de Teams |
| `ARTIFACT_BASE_DIR` | ☐ | `artifacts` | Dónde se guardan los artefactos |
| `STATE_FILE` | ☐ | `state/findice_state.json` | Estado de deduplicación |
| `LOG_LEVEL` | ☐ | `DEBUG` | `DEBUG` / `INFO` / `WARNING` |

Consulte [`.env.example`](.env.example) para la lista completa.

---

## Uso del CLI

```powershell
# Ejecutar una verificación (usa la configuración de .env)
findice check-once

# Modo con interfaz gráfica para depuración visual
findice check-once --headed

# Ejecución en seco (sin notificación de Teams)
findice check-once --dry-run

# Sobreescribir A-number y país en la línea de comandos
findice check-once --a-number A-123456789 --country MEXICO

# Imprimir configuración resuelta (redactada)
findice print-config

# Probar conectividad del webhook de Teams
findice verify-webhook

# Clasificar un fixture de muestra (sin consulta a ICE)
findice classify-sample positive
findice classify-sample zero

# Ejecutar prueba de humo en todos los fixtures locales
findice smoke-test

# Ejecutar prueba de humo en vivo usando .env (ejecución en seco forzada)
findice smoke-test --live
```

---

## Programación

Recomendado: ejecutar `check-once` cada **20 minutos** mediante el
Programador de Tareas de Windows.

El instalador registra una tarea que usa `findice-bg.exe` — un punto de
entrada **sin ventana** respaldado por `pythonw.exe`. No aparecerá ninguna
ventana de terminal durante las verificaciones programadas. Para depurar,
el punto de entrada interactivo (`findice check-once`) y el script de
PowerShell ([`scripts/run_check.ps1`](scripts/run_check.ps1)) siguen
disponibles.

Consulte [`docs/windows_task_scheduler.md`](docs/windows_task_scheduler.md)
para instrucciones paso a paso.

> No ejecute con más frecuencia que cada 10 minutos; el sitio de ICE puede
> limitar o bloquear solicitudes. Las ejecuciones finitas dirigidas por un
> programador son más seguras que un bucle infinito.

---

## Rutas de artefactos

Después de cada ejecución, los artefactos se guardan en:

```
artifacts/
  run_<TIMESTAMP>/
    attempt_01_<estado>.png     # captura de pantalla
    attempt_01_<estado>.html    # HTML sin procesar de la página
    attempt_01_<estado>.txt     # texto extraído
    run_summary.json            # metadatos de la ejecución y hash del resultado
```

Revise los artefactos cuando un resultado parezca sospechoso antes de actuar.

---

## Comportamiento de notificaciones

- **`LIKELY_POSITIVE`** – envía notificación de Teams si el resultado es nuevo
  (nuevo = hash del contenido no visto en ejecuciones recientes).
- **`ZERO_RESULT`** – sin notificación; solo registros en log.
- **`AMBIGUOUS_REVIEW`** – guarda artefactos y registra una advertencia; sin
  notificación.
- **`BOT_CHALLENGE_OR_BLOCKED`** – guarda artefactos y sale con código `3`.
- **`ERROR`** – guarda artefactos y registra; sale con código distinto de cero
  si todos los intentos fallan.

La supresión de positivos duplicados se basa en un hash SHA-256 del texto
extraído de la página. El mismo registro no volverá a notificar hasta que
cambie el contenido.

---

## Limitaciones

- ICEpicks depende completamente de la estructura del sitio del localizador de
  ICE. Si ICE cambia el DOM del sitio, puede que sea necesario actualizar los
  selectores (consulte
  [`src/findICE/selectors.py`](src/findICE/selectors.py)).
- Un resultado `LIKELY_POSITIVE` debe ser verificado manualmente por un
  abogado o representante legal calificado.
- No se requiere ni se incluye infraestructura en la nube.

---

## Legal / licencia

Este software está licenciado bajo la
**ICE Advocacy Public License (IAPL) v1.0**
(consulte [`LICENSE.md`](LICENSE.md)).

**Puntos clave:**

- Código fuente disponible, **no** es aprobada por OSI ni código abierto.
- Gratuito para uso de defensa no comercial, asistencia legal y uso
  humanitario.
- **Categóricamente prohibido para la aplicación de leyes de inmigración,
  operaciones de detención, vigilancia o cualquier uso que asista
  materialmente a las actividades de aplicación de ICE/CBP/DHS.**
- Licencia automática disponible para Defensores Públicos, Defensores
  Federales, abogados designados por el tribunal, organizaciones de
  asistencia legal y proveedores de servicios legales de inmigración sin
  fines de lucro. Consulte [`FAQ.es.md`](FAQ.es.md).
- El uso comercial o de medios/periodismo requiere una licencia escrita
  separada.

Consulte [`FAQ.es.md`](FAQ.es.md) para preguntas sobre licencias y el
proceso de verificación.

---

## Aviso de marcas registradas

**ICEpicks** y el logotipo de **ICEpicks** son marcas registradas de
Ray Quinney & Nebeker P.C. Consulte [`TRADEMARKS.md`](TRADEMARKS.md) para
la política de uso. La licencia del software no otorga derechos sobre las
marcas registradas.

---

## Resumen ético / uso prohibido

Esta herramienta **no debe** usarse para:

- Asistir a ICE, CBP, DHS o cualquier agencia gubernamental en la aplicación
  de leyes de inmigración u operaciones de detención.
- Vigilar, rastrear o monitorear personas con fines de aplicación de la ley.
- Facilitar la deportación, detención o procedimientos de remoción contra
  inmigrantes.

Cualquier uso que perjudique a las personas a quienes esta herramienta está
diseñada para ayudar es una violación de la licencia y está moralmente
prohibido.

---

## Diagrama del pipeline

Un diagrama de flujo interactivo que muestra el pipeline lógico completo —
desde la invocación del CLI hasta la automatización del navegador, la
clasificación y la notificación — está disponible en
[`docs/pipeline_flowchart.html`](docs/pipeline_flowchart.html).

Ábralo en cualquier navegador para ver cuatro diagramas:

1. **Pipeline general** – CLI → configuración → orquestación → notificación → persistencia
2. **Automatización del navegador** – lanzamiento stealth → llenado de formulario → extracción de resultados → detalles de la instalación
3. **Clasificación** – coincidencia conservadora de frases: bot → cero → página de error → positivo → ambiguo
4. **Resolución de selectores** – fallback por capas: ARIA → placeholder → rol → CSS → heurístico

---

## Contribuir

Consulte [`CONTRIBUTING.md`](CONTRIBUTING.md).

## Seguridad

Consulte [`SECURITY.md`](SECURITY.md) para reportar vulnerabilidades.
