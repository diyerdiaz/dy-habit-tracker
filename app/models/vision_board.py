from app import db
from datetime import datetime

# Imágenes que se pueden subir a una meta del vision board
EXTENSIONES_IMAGEN = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
TAMANO_MAXIMO_MB = 20
# Proporción ancho/alto que separa las imágenes verticales y las panorámicas
PROPORCION_ALTA = 0.9
PROPORCION_ANCHA = 1.9

CATEGORIAS_META = [
    {'clave': 'personal', 'nombre': 'Personal', 'icono': 'bi-person-heart', 'color': '#d966ff'},
    {'clave': 'salud',    'nombre': 'Salud',    'icono': 'bi-heart-pulse-fill', 'color': '#00e676'},
    {'clave': 'estudio',  'nombre': 'Estudio',  'icono': 'bi-mortarboard-fill', 'color': '#00bac6'},
    {'clave': 'dinero',   'nombre': 'Dinero',   'icono': 'bi-cash-coin', 'color': '#ffd700'},
    {'clave': 'viajes',   'nombre': 'Viajes',   'icono': 'bi-airplane-fill', 'color': '#ff8c42'},
    {'clave': 'trabajo',  'nombre': 'Trabajo',  'icono': 'bi-briefcase-fill', 'color': '#ff6fb5'},
]
CLAVES_CATEGORIAS = [c['clave'] for c in CATEGORIAS_META]
CATEGORIAS_POR_CLAVE = {c['clave']: c for c in CATEGORIAS_META}


class MetaVision(db.Model):
    """Meta del vision board: una imagen que la representa más su título.
    La imagen vive en disco (carpeta UPLOAD_FOLDER/vision/<idUser>); aquí solo
    se guarda el nombre aleatorio con el que se guardó."""
    __tablename__ = 'metas_vision'

    idMeta = db.Column(db.Integer, primary_key=True)
    idUser = db.Column(db.Integer, db.ForeignKey('users.idUser'), nullable=False)
    titulo = db.Column(db.String(120), nullable=False)
    descripcion = db.Column(db.String(500), nullable=True)
    categoria = db.Column(db.String(20), nullable=False, default='personal')
    fechaObjetivo = db.Column(db.Date, nullable=True)
    imagen = db.Column(db.String(255), nullable=False, unique=True)
    # Tamaño real de la imagen: con él se elige la forma del recuadro del collage
    ancho = db.Column(db.Integer, nullable=True)
    alto = db.Column(db.Integer, nullable=True)
    cumplida = db.Column(db.Boolean, nullable=False, default=False)
    fechaCumplida = db.Column(db.DateTime, nullable=True)
    createdAt = db.Column(db.DateTime, default=datetime.now)

    @property
    def info_categoria(self):
        return CATEGORIAS_POR_CLAVE.get(self.categoria, CATEGORIAS_META[0])

    @property
    def forma(self):
        """'alta' (vertical), 'ancha' (panorámica) o 'normal', según la proporción
        de la imagen, para que el recuadro tenga su misma forma y no se corte."""
        if not self.ancho or not self.alto:
            return 'normal'
        proporcion = self.ancho / self.alto
        if proporcion < PROPORCION_ALTA:
            return 'alta'
        if proporcion > PROPORCION_ANCHA:
            return 'ancha'
        return 'normal'

    def dias_restantes(self, hoy=None):
        if not self.fechaObjetivo:
            return None
        hoy = hoy or datetime.now().date()
        return (self.fechaObjetivo - hoy).days
