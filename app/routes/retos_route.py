from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user

from app.models.retos import Reto, ABIERTOS, GANADO, PERDIDO
from app.services.gamificacion import get_or_create_progress
from app.services.retos import retos_del_usuario, marcar_resultados_vistos, responder, cumplir_hoy, resumen_reto

bp = Blueprint('retos', __name__, url_prefix='/retos')

# Retos terminados que se ven por página en el historial
POR_PAGINA = 7


def _reto_propio(id_reto):
    return Reto.query.filter_by(idReto=id_reto, idUser=current_user.idUser).first_or_404()


@bp.route('/')
@login_required
def index():
    retos = retos_del_usuario(current_user.idUser)
    abiertos = [resumen_reto(r) for r in retos if r.estado in ABIERTOS]
    terminados = [r for r in retos if r.estado not in ABIERTOS]
    # El historial va de 7 en 7, del más reciente al más antiguo
    paginas = max(1, -(-len(terminados) // POR_PAGINA))
    pagina_actual = min(max(request.args.get('pagina', 1, type=int), 1), paginas)
    inicio = (pagina_actual - 1) * POR_PAGINA
    historial = [resumen_reto(r) for r in terminados[inicio:inicio + POR_PAGINA]]
    pagina = render_template('retos/index.html', abiertos=abiertos, historial=historial,
                             xp=get_or_create_progress(current_user.idUser).xpTotal,
                             pagina=pagina_actual, paginas=paginas, total_historial=len(terminados),
                             ganados=sum(1 for r in terminados if r.estado == GANADO),
                             perdidos=sum(1 for r in terminados if r.estado == PERDIDO))
    # Al verse aquí el resultado, el botón "Retos" del menú ya no aparece por él
    marcar_resultados_vistos(terminados)
    return pagina


@bp.route('/<int:id_reto>/aceptar', methods=['POST'])
@login_required
def aceptar(id_reto):
    reto = _reto_propio(id_reto)
    error = responder(reto, acepta=True)
    if error:
        flash(error, 'warning')
    else:
        flash(f'¡Aceptaste "{reto.nombre}"! Hay {reto.apuesta} XP en juego: marca "Cumplí hoy" cada día.', 'success')
    return redirect(url_for('retos.index'))


@bp.route('/<int:id_reto>/rechazar', methods=['POST'])
@login_required
def rechazar(id_reto):
    reto = _reto_propio(id_reto)
    error = responder(reto, acepta=False)
    if error:
        flash(error, 'warning')
        return redirect(url_for('retos.index'))
    flash(f'Rechazaste "{reto.nombre}". No perdiste nada.', 'info')
    return redirect(url_for('auth.dashboard'))


@bp.route('/<int:id_reto>/cumplir', methods=['POST'])
@login_required
def cumplir(id_reto):
    reto = _reto_propio(id_reto)
    marcado, error = cumplir_hoy(reto)
    if error:
        flash(error, 'warning')
    elif reto.estado == GANADO:
        flash(f'¡Ganaste "{reto.nombre}"! Sumaste {reto.apuesta} XP.', 'success')
    elif marcado:
        flash('¡Día cumplido! Sigue así mañana.', 'success')
    else:
        flash('Quitaste la marca de hoy. Recuerda marcarlo antes de que acabe el día.', 'info')
    return redirect(url_for('retos.index'))
