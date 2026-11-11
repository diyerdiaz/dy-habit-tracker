from flask import Blueprint, render_template, jsonify
from flask_login import login_required, current_user
from app.services.medallas import obtener_metricas, evaluar_medallas, medallas_sin_ver, marcar_vista, CATEGORIAS, RANGOS
from app.services.level_config import NIVELES

bp = Blueprint('medallas', __name__, url_prefix='/medallas')


@bp.route('/')
@login_required
def index():
    metricas = obtener_metricas(current_user.idUser)
    nivel = metricas['nivel']
    lista = evaluar_medallas(metricas)
    desbloqueadas = sum(1 for m in lista if m['desbloqueada'])
    # Las que aún esperan su aviso: se marcan con "¡Nueva!" (el aviso las anuncia)
    nuevas = medallas_sin_ver(current_user.idUser, lista)
    ids_nuevas = {m['id'] for m in nuevas}

    # La medalla más cercana a conseguirse entre las que ya permite tu nivel
    pendientes = [m for m in lista if not m['desbloqueada'] and not m['falta_nivel']]
    siguiente = max(pendientes, key=lambda m: m['pct']) if pendientes else None
    proximo_rango = next((r for r in RANGOS if r['nivel'] > nivel), None)

    def seccion(medallas, **datos):
        return {**datos, 'medallas': medallas,
                'ganadas': sum(1 for m in medallas if m['desbloqueada'])}

    secciones = [seccion(
        [m for m in lista if m['rango'] is None],
        clave='basicas', titulo='Medallas básicas',
        lema='Tus primeros logros. Están disponibles desde el nivel 1.',
        nivel=1, abierto=True,
    )]
    for r in RANGOS:
        secciones.append(seccion(
            [m for m in lista if m['rango'] == r['numero']],
            clave=f"rango{r['numero']}", titulo=f"Rango {'I II III IV V'.split()[r['numero'] - 1]} · {r['nombre']}",
            lema=r['lema'], nivel=r['nivel'], abierto=nivel >= r['nivel'],
            titulo_nivel=NIVELES[r['nivel'] - 1]['titulo'],
        ))

    return render_template(
        'medallas/index.html',
        secciones=secciones,
        nuevas=nuevas,
        ids_nuevas=ids_nuevas,
        categorias=CATEGORIAS,
        desbloqueadas=desbloqueadas,
        total=len(lista),
        pct_total=round(desbloqueadas / len(lista) * 100) if lista else 0,
        siguiente=siguiente,
        nivel=nivel,
        titulo_nivel=NIVELES[nivel - 1]['titulo'],
        proximo_rango=proximo_rango,
    )


@bp.route('/sin-ver')
@login_required
def sin_ver():
    """Medallas recién ganadas para el aviso que sale en cualquier pantalla."""
    campos = ('id', 'nombre', 'descripcion', 'frase', 'icono', 'rareza')
    return jsonify([{c: m[c] for c in campos} for m in medallas_sin_ver(current_user.idUser)])


@bp.route('/vista/<id_medalla>', methods=['POST'])
@login_required
def vista(id_medalla):
    """El usuario cerró el aviso de esa medalla: no se vuelve a anunciar."""
    if not marcar_vista(current_user.idUser, id_medalla):
        return jsonify({'ok': False}), 404
    return jsonify({'ok': True})
