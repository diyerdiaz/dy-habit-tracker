<p align="center">
  <img src="docs/banner.svg" alt="DY Habit Tracker & English" width="100%">
</p>

<p align="center">
  <img alt="Python" src="https://img.shields.io/badge/Python-3.12+-a855f7?style=for-the-badge&logo=python&logoColor=white">
  <img alt="Flask" src="https://img.shields.io/badge/Flask-3.1-ec4899?style=for-the-badge&logo=flask&logoColor=white">
  <img alt="SQLAlchemy" src="https://img.shields.io/badge/SQLAlchemy-2.0-3b82f6?style=for-the-badge&logo=sqlite&logoColor=white">
  <img alt="Docker" src="https://img.shields.io/badge/Docker-puerto%204000-0ea5e9?style=for-the-badge&logo=docker&logoColor=white">
  <img alt="Tests" src="https://img.shields.io/badge/tests-78%20pasando-22c55e?style=for-the-badge&logo=pytest&logoColor=white">
</p>

<h3 align="center">🕹️ Tu progreso personal, gamificado.</h3>
<p align="center">
  Una app web personal para construir hábitos, estudiar mejor, aprender inglés y mantenerte disciplinado —<br>
  con XP, niveles, rachas, 130 medallas y hasta penalizaciones si te relajas demasiado.
</p>

<br>

## 📖 ¿De qué se trata?

**DY Habit Tracker & English** es una aplicación web (Flask + SQLite) pensada como un
sistema personal de disciplina, al estilo RPG: cada hábito que completas te da experiencia
(**XP**), acumular días seguidos te da **rachas**, cada logro desbloquea **medallas**, y dejar
de hacer algo tiene **consecuencias** reales (pierdes XP, o giras la ruleta de castigos 🎡).

Además es tu espacio de estudio: organizas lo que vas a estudiar con un **tablero Kanban**
por método, guardas tus **apuntes** al terminar cada tema y practicas **inglés** con
vocabulario propio y sesiones de *shadowing*.

> En corto: tu propio *habit tracker* gamificado, con recompensas y castigos, un tablero
> de estudio y un rincón para aprender inglés a tu ritmo.

<br>

## 🧩 Módulos

| | Módulo | ¿Qué hace? |
|:---:|---|---|
| 🔥 | **Gestión de Hábitos** | Crea hábitos (nombre, categoría, frecuencia y **días de la semana en que toca**) y llévalos entre `Activo`, `Pausado` y `Completado`. |
| ✅ | **Check diario** | Marca en un toque los hábitos que cumpliste hoy. Los que no tocan hoy no aparecen ni cuentan como pendientes. |
| 📝 | **Tareas del Día** | Pendientes sueltos de hoy, sin necesidad de convertirlos en hábito permanente. |
| 🎮 | **Mi Nivel Personal** | XP por hábito, bono por racha semanal, niveles del 1 al 10 y penalización por días sin actividad. |
| 🏆 | **Medallas** | **130 medallas** en tarjetas: 30 básicas + 100 en 5 rangos que se abren al subir de nivel. |
| 📊 | **Estadísticas** | Porcentaje de cumplimiento de **cada hábito** en barras verticales, con **filtro por mes**. |
| 💬 | **Motivación** | Una **frase de anime distinta cada día** y un reto diario. |
| 🗂️ | **Métodos de Estudio** | Tarjetas con tus métodos (Pomodoro, Feynman…), cada uno con su **tablero Kanban** (arrastrar y soltar) y **subida de apuntes** al terminar un tema. |
| 🎡 | **Castigos + Ruleta** | Defines tus propios "castigos" y una ruleta los sortea cuando toca. |
| 🌐 | **Vocabulario (Inglés)** | Palabras propias con significado, ejemplos y calificación de dificultad, con calendario de repaso. |
| 🎧 | **Shadowing** | Sesiones cronometradas de práctica de pronunciación, con historial y calendario. |
| 👤 | **Mi Perfil** | Foto de perfil, cambio de usuario y de contraseña (siempre pidiendo la contraseña actual). |

<br>

## 🎮 Sistema de niveles

El nivel real está limitado por **dos** cosas a la vez: la XP acumulada **y** la cantidad
de hábitos distintos que has creado (no basta con farmear XP, también tienes que construir
hábitos nuevos).

| Nivel | Título | XP requerida |
|:---:|---|---:|
| 1 | 🌱 Novato | 0 |
| 2 | 📗 Aprendiz | 500 |
| 3 | 🔵 Constante | 1,500 |
| 4 | 🟣 Disciplinado | 3,000 |
| 5 | 🎯 Enfocado | 5,000 |
| 6 | 🛡️ Resiliente | 7,500 |
| 7 | ♟️ Estratega | 10,500 |
| 8 | 🥋 Maestro de Hábitos | 14,000 |
| 9 | 🧙 Mentor de Disciplina | 18,000 |
| 10 | 👑 Leyenda del Hábito | 22,500 |

- **+15 XP** por cada hábito marcado como hecho.
- **+20 XP** de bono cada vez que la racha llega a un múltiplo de 7 días.
- **−20 XP** por cada día completo sin actividad **en el que te tocaba algún hábito**.

### 🛋️ Días de descanso

Cada hábito tiene sus **días de la semana** (por ejemplo, Ejercicio solo lunes, miércoles y
viernes). Los días que no le tocan son de descanso: no aparece en el check, no baja tu
porcentaje, **no rompe la racha y no resta XP**.

<br>

## 🏆 Medallas

Se calculan solas a partir de tu actividad (no hay que reclamarlas) y se muestran como
tarjetas con progreso, rareza y una frase motivadora.

| Grupo | Se abre en | Medallas | Ejemplos |
|---|---|:---:|---|
| Básicas | Nivel 1 | 30 | Primer hábito, racha de 7 días, primera palabra en inglés |
| Rango I · Despertar | Nivel 2 | 20 | 150 hábitos, racha de 21 días, 7 días perfectos |
| Rango II · Forja | Nivel 4 | 20 | 400 hábitos, racha de 45 días, un mes con 80% o más |
| Rango III · Ascenso | Nivel 6 | 20 | 750 hábitos, racha de 75 días, 60 días perfectos |
| Rango IV · Élite | Nivel 8 | 20 | 1.250 hábitos, racha de 120 días |
| Rango V · Leyenda | Nivel 10 | 20 | 2.000 hábitos, **racha de un año**, 30.000 XP |

Las medallas de rango piden cumplir la meta **y** haber llegado al nivel del rango.

<br>

## 🖥️ Vista previa

Tema oscuro con hojas moradas que caen, un resplandor suave que sigue al mouse y una barra
lateral con todas las secciones:

| Ruta | Pantalla |
|---|---|
| `/` | Bienvenida + Login y registro |
| `/dashboard` | Tu Progreso Personal: hábitos de hoy, racha, consistencia y gráficos |
| `/habitos/check` | Check de Hábitos con cuenta regresiva hasta el reinicio |
| `/register_habit` | Gestión de Hábitos (crear, editar, días de la semana, estados) |
| `/tareas/` | Tareas del Día con historial |
| `/estadisticas/` | Barras de cumplimiento por hábito, filtrables por mes |
| `/menu/nivel` | Mi Nivel Personal: insignia, racha, barra de XP y mapa de niveles |
| `/medallas/` | Las 130 medallas, con filtros por categoría |
| `/motivacion/` | Frase del día, reto diario y frases anteriores |
| `/metodos/` | Métodos de Estudio y su tablero Kanban |
| `/menu/ingles` | Zona de inglés: Vocabulario y Shadowing |
| `/perfil/` | Mi Perfil: foto, usuario y contraseña |

<br>

## 🗂️ Estructura del proyecto

```text
mi-proyecto-personal/
├── app/
│   ├── models/          # Un archivo por entidad + lógica de medallas, motivación y estadísticas
│   ├── routes/          # Blueprints de Flask (auth, habits, medallas, metodos, perfil, ...)
│   ├── static/
│   │   ├── css/         # Un .css por vista (m.css = estilos globales)
│   │   └── js/          # Un .js por vista (+ csrf.js y cursor.js globales)
│   ├── templates/       # HTML por módulo (medallas/, metodos/, perfil/, menu/, ...)
│   ├── test/            # Tests con pytest
│   ├── gamificacion.py  # XP, racha, días de descanso y penalizaciones
│   ├── level_config.py  # Configuración de niveles (umbrales, bonos)
│   └── __init__.py      # App factory, blueprints y actualizar_esquema()
├── instance/            # ⚠️ Datos reales (no se versiona)
│   ├── flaskdb.sqlite   #    Base de datos SQLite
│   ├── secret_key       #    Clave de sesión generada automáticamente
│   └── uploads/         #    Apuntes (apuntes/) y fotos de perfil (avatars/)
├── docs/                # Banner del README
├── config.py            # Configuración (lee variables de entorno)
├── create_user.py       # Crea un usuario desde la terminal
├── migrar_passwords.py  # Convierte contraseñas antiguas en texto plano a hash
├── run.py               # Punto de entrada (desarrollo y gunicorn)
├── Dockerfile           # Imagen de producción con gunicorn en el puerto 4000
├── docker-compose.yml   # Arranque con un comando, con instance/ como volumen
└── requirements.txt
```

> Convención del proyecto: **modelos, rutas, estáticos (css/js) y templates viven cada uno
> en su propia carpeta**, sin mezclarse entre sí.

<br>

## 🛠️ Stack tecnológico

<p align="left">
  <img src="https://img.shields.io/badge/Flask-3.1.0-ec4899?style=flat-square&logo=flask&logoColor=white">
  <img src="https://img.shields.io/badge/Flask--Login-0.6.3-a855f7?style=flat-square">
  <img src="https://img.shields.io/badge/Flask--SQLAlchemy-3.1.1-3b82f6?style=flat-square">
  <img src="https://img.shields.io/badge/Flask--WTF-1.2.2-a855f7?style=flat-square">
  <img src="https://img.shields.io/badge/SQLAlchemy-2.0.37-3b82f6?style=flat-square">
  <img src="https://img.shields.io/badge/Jinja2-3.1.5-f59e0b?style=flat-square">
  <img src="https://img.shields.io/badge/Pillow-12.3.0-22c55e?style=flat-square">
  <img src="https://img.shields.io/badge/qrcode-8.0-22c55e?style=flat-square">
  <img src="https://img.shields.io/badge/gunicorn-23.0-16a34a?style=flat-square&logo=gunicorn&logoColor=white">
  <img src="https://img.shields.io/badge/Bootstrap-5.3-7c3aed?style=flat-square&logo=bootstrap&logoColor=white">
  <img src="https://img.shields.io/badge/pytest-tests-6366f1?style=flat-square&logo=pytest&logoColor=white">
</p>

<br>

## 🚀 Instalación y uso (local)

```bash
# 1. Clona el repositorio y entra a la carpeta
git clone https://github.com/diyerdiaz/mi-proyecto-personal.git
cd mi-proyecto-personal

# 2. Crea y activa un entorno virtual
python -m venv venv
source venv/bin/activate      # En Windows: venv\Scripts\activate

# 3. Instala las dependencias
pip install -r requirements.txt

# 4. (Opcional) crea un usuario desde la terminal (te pide la contraseña)
python create_user.py tu_usuario

# 5. Levanta la app (solo accesible desde tu equipo, sin depurador)
python run.py
#    Modo desarrollo con recarga automática:   FLASK_DEBUG=1 python run.py
#    Abrirla desde el celular en tu red wifi:  APP_HOST=0.0.0.0 python run.py
```

La app queda disponible en **http://localhost:5000** 🎉

> Al arrancar, `actualizar_esquema()` crea las tablas que falten y agrega las columnas
> nuevas a una base de datos existente **sin borrar nada**.

<br>

## 🐳 Docker (puerto 4000)

La imagen usa **gunicorn** (servidor de producción), corre con un usuario sin privilegios
y guarda los datos en `instance/`, montada como volumen para que no se pierdan al
reconstruir o reiniciar el contenedor.

```bash
docker compose up -d --build
```

Abre **http://localhost:4000**. Para ver los logs o detenerla:

```bash
docker compose logs -f
docker compose down
```

<details>
<summary>Con Podman (sin compose)</summary>

```bash
podman build -t mi-proyecto-personal .
podman run -d --name mi-proyecto-personal --userns=keep-id \
  -p 4000:4000 -v ./instance:/app/instance:z mi-proyecto-personal
```
</details>

> ⚠️ No corras al mismo tiempo `python run.py` y el contenedor sobre la misma
> `instance/flaskdb.sqlite`: usa uno u otro.

<br>

## 📱 App para el celular

**Instalarla desde el navegador (Android o iPhone):** abre la página y elige
*"Instalar app"* o *"Añadir a pantalla de inicio"*. Funciona gracias al manifiesto y al
*service worker* (`/manifest.webmanifest`, `/sw.js`).

<br>

## ⚙️ Variables de entorno

| Variable | Por defecto | Para qué sirve |
|---|---|---|
| `SECRET_KEY` | se genera en `instance/secret_key` | Clave que firma las sesiones. |
| `DATABASE_URL` | `sqlite:///flaskdb.sqlite` (en `instance/`) | Cambiar la base de datos. |
| `UPLOAD_FOLDER` | `instance/uploads` | Dónde se guardan apuntes y fotos de perfil. |
| `SESSION_COOKIE_SECURE` | `0` | Ponlo en `1` cuando la publiques con **HTTPS**. |
| `TZ` | `America/Bogota` (en Docker) | Zona horaria: el día (check, rachas, XP, frase del día) cambia a medianoche de esta zona. |
| `FLASK_DEBUG` | `0` | `1` = recarga automática y depurador (solo en tu equipo). |
| `APP_HOST` / `APP_PORT` | `127.0.0.1` / `5000` | Dirección y puerto de `python run.py`. |

<br>

## 🧪 Tests

```bash
pytest app/test
```

Los tests usan una base de datos **en memoria** y una carpeta temporal para los archivos,
así que nunca tocan tus datos reales.

<br>

## 🔒 Seguridad

- Las contraseñas se guardan con hash (`scrypt`, vía Werkzeug). Si tienes una base de datos
  antigua con contraseñas en texto plano, ejecuta `python migrar_passwords.py` (hace una copia
  de seguridad antes) o simplemente inicia sesión: se convierten solas.
- Cambiar usuario o contraseña en **Mi Perfil** siempre pide la contraseña actual.
- Todos los formularios y peticiones `fetch` llevan token **CSRF** (Flask-WTF + `static/js/csrf.js`).
- Cada usuario solo puede ver y modificar sus propios datos, apuntes y foto.
- Archivos subidos: se valida el tipo, se guardan con nombre aleatorio y las fotos se
  vuelven a procesar (recortadas a 400×400 y sin metadatos como la ubicación GPS).
- La carpeta `instance/` (base de datos, clave y archivos subidos) **no se versiona**.

<br>

## 🌍 Antes de publicarla en internet

- [ ] Servirla con **HTTPS** y poner `SESSION_COOKIE_SECURE=1`.
- [ ] Usar un hosting con **disco persistente** (la base SQLite y los archivos viven en disco).
- [ ] Programar **copias de seguridad** de `instance/`.
- [ ] Limitar los intentos de inicio de sesión y agregar cabeceras de seguridad.
- [ ] No hacer público el repositorio sin limpiar antes el historial: los commits antiguos
      incluyen una base de datos con contraseñas de prueba en texto plano.

<br>

<p align="center">
  <sub>Hecho con 🖤 y mucha disciplina propia.</sub>
</p>
