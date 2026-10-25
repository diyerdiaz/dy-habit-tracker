from datetime import datetime, timedelta

from app import db

MAX_FALLOS = 6          # al sexto intento fallido se bloquea el acceso
MINUTOS_BLOQUEO = 30
# Si pasa este tiempo sin fallar, el contador vuelve a cero
MINUTOS_OLVIDO = 30
# Tope por IP sumando todos los usuarios: frena a quien prueba muchas cuentas
# desde el mismo equipo sin llegar a 6 fallos en ninguna
MAX_FALLOS_POR_IP = 20

# Fila que suma los fallos de una IP con cualquier usuario (ningún usuario se
# llama "", el login ni siquiera cuenta fallos con el nombre vacío)
TODOS = ''


class IntentoLogin(db.Model):
    """Intentos fallidos de inicio de sesión por nombre de usuario e IP.

    - Se guarda por el nombre escrito (exista o no la cuenta), así el bloqueo
      no revela qué usuarios existen.
    - Cuenta también por IP: quien falla 6 veces solo se bloquea a sí mismo
      (su IP con ese usuario) y no deja sin acceso al dueño de la cuenta.
    """
    __tablename__ = 'intentos_login_ip'
    usuario = db.Column(db.String(80), primary_key=True)
    ip = db.Column(db.String(45), primary_key=True)  # 45 = largo máximo de una IPv6
    fallos = db.Column(db.Integer, nullable=False, default=0)
    bloqueadoHasta = db.Column(db.DateTime, nullable=True)
    actualizado = db.Column(db.DateTime, nullable=False, default=datetime.now, index=True)

    @staticmethod
    def _clave(usuario):
        return (usuario or '').strip()[:80]

    @staticmethod
    def _ip(ip):
        return (ip or 'desconocida')[:45]

    @classmethod
    def _minutos(cls, registro, ahora):
        if not registro or not registro.bloqueadoHasta or registro.bloqueadoHasta <= ahora:
            return 0
        segundos = (registro.bloqueadoHasta - ahora).total_seconds()
        return max(1, int(-(-segundos // 60)))  # redondeo hacia arriba

    @classmethod
    def minutos_bloqueado(cls, usuario, ip, ahora=None):
        """Minutos que faltan para poder intentar de nuevo (0 = no está bloqueado)."""
        ahora = ahora or datetime.now()
        ip = cls._ip(ip)
        return max(cls._minutos(db.session.get(cls, (cls._clave(usuario), ip)), ahora),
                   cls._minutos(db.session.get(cls, (TODOS, ip)), ahora))

    @classmethod
    def _sumar(cls, usuario, ip, maximo, ahora):
        registro = db.session.get(cls, (usuario, ip))
        if not registro:
            registro = cls(usuario=usuario, ip=ip, fallos=0)
            db.session.add(registro)
        elif registro.actualizado < ahora - timedelta(minutes=MINUTOS_OLVIDO):
            registro.fallos = 0
        registro.fallos += 1
        registro.actualizado = ahora
        restantes = maximo - registro.fallos
        if restantes <= 0:
            registro.bloqueadoHasta = ahora + timedelta(minutes=MINUTOS_BLOQUEO)
            registro.fallos = 0
            restantes = 0
        return restantes

    @classmethod
    def registrar_fallo(cls, usuario, ip, ahora=None):
        """Suma un fallo. Devuelve los intentos que quedan (0 = se acaba de bloquear)."""
        ahora = ahora or datetime.now()
        ip = cls._ip(ip)
        # Limpieza: registros viejos que ya no bloquean a nadie
        cls.query.filter(cls.actualizado < ahora - timedelta(days=1)).delete(synchronize_session=False)
        restantes = cls._sumar(cls._clave(usuario), ip, MAX_FALLOS, ahora)
        restantes_ip = cls._sumar(TODOS, ip, MAX_FALLOS_POR_IP, ahora)
        db.session.commit()
        return min(restantes, restantes_ip)

    @classmethod
    def limpiar(cls, usuario, ip):
        """Al entrar bien se borran los fallos de ese usuario desde esa IP.
        El tope general de la IP no se borra: si no, bastaría con entrar a una
        cuenta propia cada pocos intentos para seguir probando otras."""
        cls.query.filter_by(usuario=cls._clave(usuario), ip=cls._ip(ip)).delete(synchronize_session=False)
        db.session.commit()

    @classmethod
    def limpiar_usuario(cls, usuario):
        """Al recuperar la contraseña el dueño demostró que la cuenta es suya:
        se quita el bloqueo de ese usuario desde cualquier IP."""
        cls.query.filter_by(usuario=cls._clave(usuario)).delete(synchronize_session=False)
        db.session.commit()
