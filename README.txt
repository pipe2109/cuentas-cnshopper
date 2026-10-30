CNShopper Client Assistant V4.1 — Chromium temporal
==================================================

REQUISITOS: Windows, Python 3.10+, Visual Studio Code.

INSTALAR (terminal de VS Code en la carpeta que contiene main.py):
    py -m pip install -r requirements.txt
    py -m playwright install chromium

EJECUTAR:
    py main.py

NOVEDADES:
- Pregunta CELULAR (Sí) o COMPUTADORA (No) cada vez que se abre CNShopper.
- Chromium crea un contexto temporal nuevo por apertura, sin perfil persistente.
- No se reutilizan cookies, sesiones ni caché del navegador personal.
- Al cerrar Chromium se elimina la sesión del contexto; el navegador no
  ofrece anonimato de red: el sitio puede ver IP y señales del dispositivo.
- Si hay cliente seleccionado, intenta completar nombre, email y teléfono
  únicamente en campos únicos y reconocibles de la página inicial cargada.
  Si el formulario aparece más tarde, usa los botones Copiar de Seguimiento.
- Nunca envía el formulario ni introduce contraseñas ni códigos OTP.
- La vista móvil es una emulación visual, no un teléfono real.

IMPORTANTE: la base SQLite conserva los datos de clientes en data/clients.db.
Para migrar desde V4, copia la carpeta data/ de la versión anterior a esta
carpeta antes de ejecutar la nueva versión. Guarda una copia de seguridad.
Los respaldos se guardan en backups/. No elimines la versión anterior.

PRUEBAS:
    py -m unittest discover -s tests -v

No se ha verificado el diseño HTML actual de CNShopper: puede que el
formulario no esté en la página inicial o use nombres de campos distintos.
No se automatizan validaciones ni verificaciones de CNShopper.

ACTUALIZACIÓN V4.2:
- En escritorio, Playwright intenta pulsar Register.
- En móvil, intenta pulsar Me y luego Sign Up.
- Espera la página /register y rellena solo Email Address si está vacío.
- El código de referido no se modifica. Comprueba manualmente que sea 2370842.
- Nunca pulsa Send Verification Code ni completa OTP.
- Si CNShopper cambia sus botones, navega manualmente y utiliza Copiar.
- Cada apertura sigue usando un contexto temporal separado.
\nV4.3: En vista móvil, el asistente espera el campo Email Address, se desplaza hasta él y lo rellena sin enviar el formulario. Si la página cambia, continúa manualmente.\n
V4.4 - CORRECCION DEL FORMULARIO
- El asistente ahora reintenta localizar el campo de correo si tarda en aparecer.
- Busca por placeholder, tipo y autocomplete. El scroll no es requisito previo.
- Nunca pulsa Send Verification Code, ni lee o introduce OTP.
- Si no encuentra el campo, el navegador permanece abierto para continuar manualmente.
- Los mensajes de diagnostico se imprimen en la salida del proceso del navegador.
- No se guardan cookies entre sesiones.

V4.5: Al confirmar autorización del cliente y pulsar Iniciar registro,
se solicita una sola vez el código de verificación tras rellenar el correo.
El OTP sigue siendo manual. Si la web cambia o rechaza la solicitud,
revisar el navegador y el historial; no se reintenta automáticamente.
\nV4.6: Tras solicitar un código, abre Emailnator en otra pestaña para consulta manual.\n
V4.7 - Emailnator Custom Email
-----------------------------
Después de solicitar el código, el asistente abre Emailnator, busca el enlace
"Custom email" (aunque esté más abajo), lo pulsa y prepara la dirección del
cliente cuando encuentra un campo inequívoco. No pulsa GO!, no abre mensajes,
no extrae ni introduce OTP. Si cambia la interfaz, deja la pestaña abierta
para continuar manualmente. Los mensajes de diagnóstico salen en la terminal.

V4.9 - AVISO DE COOKIES DE EMAILNATOR
------------------------------------
- Antes de abrir Custom email, intenta cerrar el aviso "Got it" cuando aparece.
- Revisa nuevamente el aviso antes del clic en Custom email, por si carga tarde.
- Comprueba que se abra el campo "Paste your custom email" y prepara el correo.
- Nunca pulsa Generate New ni GO!, ni lee mensajes o codigos OTP.
- Si no encuentra el enlace o el campo, deja el navegador abierto e informa en terminal.
- Se conserva el resto del funcionamiento de V4.8.
