from flask import Blueprint, render_template
from flask_login import login_required, current_user
from app.models.medallas import obtener_metricas, evaluar_medallas, CATEGORIAS, RANGOS
from app.services.level_config import NIVELES

bp = Blueprint('medallas', __name__, url_prefix='/medallas')


@bp.route('/')
@login_required
def index():
    metricas = obtener_metricas(current_user.idUser)
    nivel = metricas['nivel']
    lista = evaluar_medallas(metricas)
    desbloqueadas = sum(1 for m in lista if m['desbloqueada'])

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
        categorias=CATEGORIAS,
        desbloqueadas=desbloqueadas,
        total=len(lista),
        pct_total=round(desbloqueadas / len(lista) * 100) if lista else 0,
        siguiente=siguiente,
        nivel=nivel,
        titulo_nivel=NIVELES[nivel - 1]['titulo'],
        proximo_rango=proximo_rango,
    )
