# Preguntas Frecuentes — ICEpicks

[🇺🇸 Read in English](FAQ.md)

---

## General

### ¿Qué es ICEpicks?

ICEpicks es una herramienta de automatización local que monitorea el
Localizador de Detenidos en Línea de ICE buscando a una persona específica
por número de registro de extranjero (A-number) y país de origen. Ejecuta
múltiples intentos de búsqueda nuevos por cada verificación programada para
reducir los falsos negativos causados por el comportamiento inestable del
sitio.

### ¿Es esta una herramienta oficial de ICE?

No. ICEpicks es una herramienta independiente creada por defensores y abogados
para trabajar *con* el sitio web del localizador de ICE. No tiene afiliación
ni respaldo de ICE, DHS, CBP o cualquier agencia gubernamental.

### ¿ICEpicks almacena información personal en la nube?

No. ICEpicks es una herramienta local. Todos los datos, incluyendo capturas
de pantalla, artefactos HTML y registros de ejecución, se almacenan en su
máquina local. Nada se envía externamente excepto la notificación opcional
del webhook de Teams (que usted controla).

---

## Licencia

### ¿Qué licencia usa ICEpicks?

ICEpicks está licenciado bajo la **ICE Advocacy Public License (IAPL) v1.0**,
una licencia personalizada de código fuente disponible. Esta **no** es una
licencia de código abierto aprobada por OSI.

### ¿Es gratuito el uso de ICEpicks?

Para usos no comerciales calificados — incluyendo uso personal, asistencia
legal, investigación académica y supervisión de derechos civiles — sí,
ICEpicks es gratuito.

El uso comercial y el uso sistemático por organizaciones de medios
comerciales requieren una licencia de pago separada.

### ¿Puede mi oficina de defensoría pública usar ICEpicks?

Sí. Las Oficinas de Defensoría Pública, las Organizaciones de Defensores
Federales y los abogados designados por el tribunal que operan bajo autoridad
estatal o municipal están cubiertos por la licencia automática en la
Sección 6 de la IAPL v1.0.

No necesita obtener permiso previamente, pero debe:
- Usar el Software únicamente para representación legal no comercial
- Cumplir con todas las restricciones (especialmente la prohibición de uso
  para aplicación de la ley)
- Completar la verificación si se solicita

Para recibir un ID de Referencia de Licencia formal, envíe una solicitud de
verificación a `licensing.icepicks@rqn.com`.

### ¿Puede mi organización de asistencia legal sin fines de lucro usar ICEpicks?

Sí. Los proveedores de servicios legales sin fines de lucro cuya misión
principal es representar a inmigrantes o personas en procedimientos de
inmigración están cubiertos por la licencia automática. Se aplican las mismas
condiciones que para los defensores públicos mencionados anteriormente.

### ¿Puede un bufete de abogados privado usar ICEpicks?

Los bufetes de abogados privados no están cubiertos por la licencia automática.
Sin embargo, un bufete puede solicitar **permiso escrito para un caso
específico** para representación genuina pro bono en inmigración. Contacte a
`licensing.icepicks@rqn.com` con:
- Nombre del bufete y sitio web
- Descripción del/los asunto(s) pro bono específico(s)
- Confirmación de que el uso es no comercial y exclusivamente para beneficio
  del cliente

### ¿Puedo usar ICEpicks para periodismo o reportajes?

El uso periodístico ocasional y no comercial (por ejemplo, probar la
herramienta para escribir un artículo sobre la confiabilidad del localizador
de ICE) está permitido bajo los términos generales no comerciales.

El uso sistemático o recurrente por organizaciones de noticias o medios
comerciales con fines de generación de ingresos requiere una **licencia de
pago separada**. Contacte a `licensing.icepicks@rqn.com`.

### ¿Pueden las agencias gubernamentales usar ICEpicks?

De forma muy limitada. Los empleados gubernamentales pueden usar ICEpicks
únicamente para propósitos no operativos tales como:
- Análisis de políticas legislativas
- Supervisión de derechos civiles
- Revisión académica o de cumplimiento
- Uso ordenado por tribunal limitado al alcance de la orden

**Prohibición categórica:** ICEpicks nunca podrá ser utilizado por ICE, CBP,
DHS o cualquier agencia para la aplicación de leyes de inmigración,
operaciones de detención o vigilancia. Esta prohibición es absoluta y no puede
ser dispensada.

### ¿Puedo hacer un fork de ICEpicks?

Sí, bajo estas condiciones:
- Su fork debe usar la IAPL v1.0 (o una versión posterior designada por el
  Licenciante)
- Su fork debe usar una marca claramente distinta (no "ICEpicks")
- Debe incluir un aviso prominente (ver TRADEMARKS.md)
- Su fork debe ser no comercial y de código fuente disponible
- Debe incluir atribución al proyecto ICEpicks original

### ¿Puedo vender un producto comercial basado en ICEpicks?

No sin una licencia comercial separada. Contacte a
`licensing.icepicks@rqn.com`.

---

## Verificación

### ¿Cómo obtengo un ID de Referencia de Licencia?

Envíe una solicitud de verificación a `licensing.icepicks@rqn.com` con:
- Nombre y tipo de organización
- Sitio web oficial
- Nombre del contacto principal y correo electrónico institucional
- Descripción del uso previsto
- Confirmación de uso no comercial
- Confirmación de que el uso no cae dentro de ninguna categoría prohibida

Recibirá un código de verificación único y un enlace. Después de completar la
verificación, recibirá un ID de Referencia de Licencia que documenta
formalmente su uso permitido.

### ¿Cuánto tiempo toma la verificación?

El Licenciante intenta procesar solicitudes completas dentro de 10 días
hábiles. Las solicitudes incompletas pueden ser devueltas para información
adicional.

### ¿Qué sucede si mi licencia es revocada?

Se le notificará por correo electrónico. Debe cesar inmediatamente todo uso
y distribución del Software y destruir todas las copias. Consulte la
Sección 8 de LICENSE.md para los detalles.

---

## Técnico

### ¿Por qué el localizador de ICE devuelve falsos "0 Resultados de Búsqueda"?

El localizador de ICE es una aplicación de página única (SPA) inestable que
intermitentemente falla en devolver resultados para personas que están
activamente detenidas. Esto parece ser un problema de confiabilidad del sitio,
no una confirmación de ausencia. ICEpicks aborda esto ejecutando múltiples
intentos independientes y nuevos por cada verificación programada.

### ¿Qué significa cada estado de resultado?

- **`ZERO_RESULT`**: El sitio devolvió explícitamente "0 Resultados de
  Búsqueda." Esto *no* confirma que la persona no está detenida; ejecute de
  nuevo más tarde.
- **`LIKELY_POSITIVE`**: La página contiene indicadores consistentes con un
  registro de detenido. Verifique manualmente antes de actuar.
- **`AMBIGUOUS_REVIEW`**: La página cargó pero el contenido no es claro o
  cargó parcialmente. Revise los artefactos guardados.
- **`BOT_CHALLENGE_OR_BLOCKED`**: El sitio presentó un CAPTCHA o bloqueó la
  solicitud. Espere antes de reintentar.
- **`ERROR`**: El navegador o la red falló. Revise los registros y artefactos.

### ¿Cómo funciona la deduplicación?

ICEpicks calcula un hash SHA-256 del texto normalizado de la página. Si el
mismo hash ya fue enviado como notificación en una ejecución reciente, no se
envía una nueva notificación. Esto previene alertas repetidas por el mismo
registro.

### ¿Dónde se almacenan los artefactos?

Por defecto, en el directorio `artifacts/` dentro de su directorio de trabajo.
Cada ejecución obtiene su propio subdirectorio nombrado por marca de tiempo.
Consulte el README para el diseño completo.

### ¿Cómo ajusto los selectores si el sitio de ICE cambia?

Edite `src/findICE/selectors.py`. Los selectores están organizados en orden de
prioridad (basados en etiqueta → marcador de posición → rol → respaldo CSS).
Agregue o modifique candidatos según sea necesario después de inspeccionar los
artefactos HTML guardados.

---

*Para licencias: licensing.icepicks@rqn.com*
*Para marcas registradas: trademarks.icepicks@rqn.com*
