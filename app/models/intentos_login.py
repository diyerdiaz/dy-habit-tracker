from datetime import datetime, timedelta

from app import db

MAX_FALLOS = 6          # al sexto intento fallido se bloquea el acceso
MINUTOS_BLOQUEO = 30
# Si pasa este tiempo sin fallar, el contador vuelve a cero
MINUTOS_OLVIDO = 30


class IntentoLogin(db.Model):
    """Intentos fallidos de inicio de sesión por nombre de usuario.
    Se guarda por el nombre escrito (exista o no la cuenta), así el bloqueo
    no revela qué usuarios existen."""
    __tablename__ = 'intentos_login'
    usuario = db.Column(db.String(80), primary_key=True)
    fallos = db.Column(db.Integer, nullable=False, default=0)
    bloqueadoHasta = db.Column(db.DateTime, nullable=True)
    actualizado = db.Column(db.DateTime, nullable=False, default=datetime.now, index=True)

    @staticmethod
    def _clave(usuario):
        return (usuario or '').strip()[:80]

    @classmethod
    def minutos_bloqueado(cls, usuario, ahora=None):
        """Minutos que faltan para poder intentar de nuevo (0 = no está bloqueado)."""
        ahora = ahora or datetime.now()
        registro = db.session.get(cls, cls._clave(usuario))
        if not registro or not registro.bloqueadoHasta or registro.bloqueadoHasta <= ahora:
            return 0
        segundos = (registro.bloqueadoHasta - ahora).total_seconds()
        return max(1, int(-(-segundos // 60)))  # redondeo hacia arriba

    @classmethod
    def registrar_fallo(cls, usuario, ahora=None):
        """Suma un fallo. Devuelve los intentos que quedan (0 = se acaba de bloquear)."""
        ahora = ahora or datetime.now()
        clave = cls._clave(usuario)
        # Limpieza: registros viejos que ya no bloquean a nadie
        cls.query.filter(cls.actualizado < ahora - timedelta(days=1)).delete(synchronize_session=False)
        registro = db.session.get(cls, clave)
        if not registro:
            registro = cls(usuario=clave, fallos=0)
            db.session.add(registro)
        elif registro.actualizado < ahora - timedelta(minutes=MINUTOS_OLVIDO):
            registro.fallos = 0
        registro.fallos += 1
        registro.actualizado = ahora
        restantes = MAX_FALLOS - registro.fallos
        if restantes <= 0:
            registro.bloqueadoHasta = ahora + timedelta(minutes=MINUTOS_BLOQUEO)
            registro.fallos = 0
            restantes = 0
        db.session.commit()
        return restantes

    @classmethod
    def limpiar(cls, usuario):
        """Al entrar bien (o recuperar la contraseña) se borran los fallos y el bloqueo."""
        cls.query.filter_by(usuario=cls._clave(usuario)).delete(synchronize_session=False)
        db.session.commit()
