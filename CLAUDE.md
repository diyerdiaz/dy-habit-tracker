# Reglas del proyecto

## Cada cosa en su carpeta
Todo código nuevo va en la carpeta que le corresponde dentro de `app/`. No mezclar capas en un mismo archivo.

| Qué | Dónde | Convención de nombre |
|---|---|---|
| Modelos SQLAlchemy | `app/models/` | `<nombre>.py` |
| Lógica compartida (correo, gamificación, configuración) | `app/services/` | `<nombre>.py` |
| Rutas / blueprints | `app/routes/` | `<nombre>_route.py` (registrar el blueprint en `app/__init__.py`) |
| Plantillas HTML | `app/templates/<modulo>/` | `index.html`, `create.html`, `edit.html`, ... |
| CSS | `app/static/css/` | `<modulo>.css` |
| JavaScript | `app/static/js/` | `<modulo>.js` (nada de `<script>` largos inline en las plantillas) |
| Imágenes | `app/static/img/` | |
| Tests | `app/test/` | `test_<modulo>.py` (usar los fixtures de `app/test/conftest.py`) |

- No definir modelos dentro de archivos de rutas, ni rutas dentro de modelos.
- No poner CSS ni JS grandes dentro de los `.html`; van en `static/`.
- Si algo no encaja en ninguna carpeta, preguntar antes de crear una carpeta nueva.

## Tests siempre
Cada funcionalidad o cambio que se pida viene con sus tests en `app/test/` en la misma tarea, sin esperar a que se pidan. Correrlos antes de dar el trabajo por terminado:

```bash
venv/bin/python -m pytest app/test -q
```
