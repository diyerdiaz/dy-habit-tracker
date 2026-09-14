<p align="center">
  <img src="docs/banner.svg" alt="DY Habit Tracker & English" width="100%">
</p>

<p align="center">
  <img alt="Python" src="https://img.shields.io/badge/Python-3.11+-a855f7?style=for-the-badge&logo=python&logoColor=white">
  <img alt="Flask" src="https://img.shields.io/badge/Flask-3.1-ec4899?style=for-the-badge&logo=flask&logoColor=white">
  <img alt="SQLAlchemy" src="https://img.shields.io/badge/SQLAlchemy-2.0-3b82f6?style=for-the-badge&logo=sqlite&logoColor=white">
  <img alt="Status" src="https://img.shields.io/badge/estado-en%20desarrollo-facc15?style=for-the-badge">
</p>

<h3 align="center">🕹️ Tu progreso personal, gamificado.</h3>
<p align="center">
  Una app web personal para construir hábitos, aprender inglés y mantenerte disciplinado —<br>
  con XP, niveles, rachas y hasta penalizaciones si te relajas demasiado.
</p>

<br>

## 📖 ¿De qué se trata?

**DY Habit Tracker & English** es una aplicación web (Flask + SQLite) pensada como un
sistema personal de disciplina, al estilo RPG: cada hábito que completas te da experiencia
(**XP**), acumular días seguidos te da **rachas**, y dejar de hacer algo tiene **consecuencias**
reales (pierdes XP, o giras la ruleta de castigos 🎡). En paralelo, funciona como tu
espacio de estudio de inglés, con vocabulario propio y sesiones de *shadowing*.

> En corto: es tu propio *habit tracker* gamificado, con recompensas y castigos, más un
> rincón para aprender inglés a tu ritmo.

<br>

## 🧩 Módulos

| | Módulo | ¿Qué hace? |
|:---:|---|---|
| 🔥 | **Gestión de Hábitos** | Crea hábitos (nombre, categoría, frecuencia) y llévalos entre `Activo`, `Pausado` y `Completado`. |
| ✅ | **Check diario** | Marca en un toque los hábitos que cumpliste hoy; el conteo se reinicia cada 24h. |
| 📝 | **Tareas del Día** | Pendientes sueltos de hoy, sin necesidad de convertirlos en hábito permanente. |
| 🎮 | **Gamificación** | XP por hábito, bono por racha semanal, niveles del 1 al 10 y penalización por días sin actividad. |
| 🎡 | **Castigos + Ruleta** | Defines tus propios "castigos" (consecuencias) y una ruleta los sortea cuando toca. |
| 🌐 | **Vocabulario (Inglés)** | Registras palabras propias con significado, ejemplos y calificación de dificultad (fácil/medio/difícil), con calendario de repaso. |
| 🎧 | **Shadowing** | Sesiones cronometradas de práctica de pronunciación (repetir audio en inglés), con historial y calendario. |
| 📊 | **Estadísticas** | Cumplimiento, radar por categoría, racha más larga, todo visualizado. |
| 👤 | **Usuarios** | Login propio con `Flask-Login` y generación de **código QR** por usuario. |

<br>

## 🎮 Sistema de niveles

El nivel real está limitado por **dos** cosas a la vez: la XP acumulada, **y** la cantidad
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
- **−20 XP** por cada día completo sin ninguna actividad registrada.

<br>

## 🖥️ Vista previa

La interfaz usa un tema oscuro con esferas de luz en degradé (púrpura/rosa para hábitos y
gamificación, azul para la zona de inglés):

- **`/` — Bienvenida + Login:** *"Retoma el control de tus hábitos y acelera tu aprendizaje diario"*, con acceso rápido a Habits / English.
- **`/dashboard` — Tu Progreso Personal:** resumen de hábitos de hoy y análisis visual.
- **`/habitos/check` — Check de Hábitos:** lista táctil con cuenta regresiva hasta el próximo reinicio.
- **`/menu/nivel` — Mi Nivel Personal:** insignia de nivel, racha en llamas 🔥, barra de XP y estadísticas.
- **`/menu/ingles` — Aprende Inglés:** zona azul independiente con accesos a Vocabulario y Shadowing.
- **`/tareas/` — Tareas del Día:** lista rápida de pendientes con historial.

<br>

## 🗂️ Estructura del proyecto

```text
mi proyecto personal/
├── app/
│   ├── models/        # Un archivo por entidad (User, Habit, Tarea, Castigo, ...)
│   ├── routes/         # Blueprints de Flask (auth, habits, tareas, castigos, menu...)
│   ├── static/
│   │   ├── css/        # Un .css por vista
│   │   └── js/         # Un .js por vista
│   ├── templates/       # HTML por módulo (menu/, tareas/, castigos/, users/, register/)
│   ├── gamificacion.py  # Lógica de mutación de XP, racha y penalizaciones
│   ├── level_config.py  # Configuración pura de niveles (umbrales, bonos)
│   └── __init__.py      # App factory + registro de blueprints
├── instance/
│   └── flaskdb.sqlite   # Base de datos SQLite (no versionar cambios de datos reales)
├── config.py             # Configuración de Flask/SQLAlchemy
├── create_user.py        # Script para crear un usuario inicial
├── run.py                # Punto de entrada de la app
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
  <img src="https://img.shields.io/badge/SQLAlchemy-2.0.37-3b82f6?style=flat-square">
  <img src="https://img.shields.io/badge/Jinja2-3.1.5-f59e0b?style=flat-square">
  <img src="https://img.shields.io/badge/qrcode-8.0-22c55e?style=flat-square">
  <img src="https://img.shields.io/badge/Pillow-11.1.0-22c55e?style=flat-square">
  <img src="https://img.shields.io/badge/pytest-tests-6366f1?style=flat-square&logo=pytest&logoColor=white">
</p>

<br>

## 🚀 Instalación y uso

```bash
# 1. Clona el repositorio y entra a la carpeta
git clone <url-del-repo>
cd "mi proyecto personal"

# 2. Crea y activa un entorno virtual
python -m venv venv
source venv/bin/activate      # En Windows: venv\Scripts\activate

# 3. Instala las dependencias
pip install -r requirements.txt

# 4. (Opcional) crea un usuario de prueba: diyer / 123456
python create_user.py

# 5. Levanta la app
python run.py
```

La app queda disponible en **http://localhost:5000** 🎉

<br>

## 🧪 Tests

```bash
pytest app/test
```

<br>

<p align="center">
  <sub>Hecho con 🖤 y mucha disciplina propia.</sub>
</p>
