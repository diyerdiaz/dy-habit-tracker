import os
from app import db
from datetime import datetime

# Columnas del tablero Kanban, en orden
COLUMNAS_KANBAN = [
    {'clave': 'pendiente', 'nombre': 'Por hacer',   'icono': 'bi-circle'},
    {'clave': 'progreso',  'nombre': 'En progreso', 'icono': 'bi-hourglass-split'},
    {'clave': 'hecho',     'nombre': 'Hecho',       'icono': 'bi-check-circle-fill'},
]
CLAVES_COLUMNAS = [c['clave'] for c in COLUMNAS_KANBAN]

ICONOS_METODO = [
    'bi-stopwatch', 'bi-lightbulb', 'bi-arrow-repeat', 'bi-diagram-3',
    'bi-journal-text', 'bi-question-circle', 'bi-book', 'bi-pencil-square',
    'bi-headphones', 'bi-translate', 'bi-calculator', 'bi-easel',
]
# Apuntes que se pueden subir a una tarjeta terminada (extensión -> ícono)
EXTENSIONES_APUNTES = {
    'pdf': 'bi-file-earmark-pdf', 'txt': 'bi-file-earmark-text', 'md': 'bi-file-earmark-text',
    'doc': 'bi-file-earmark-word', 'docx': 'bi-file-earmark-word', 'odt': 'bi-file-earmark-word',
    'ppt': 'bi-file-earmark-slides', 'pptx': 'bi-file-earmark-slides', 'odp': 'bi-file-earmark-slides',
    'xls': 'bi-file-earmark-spreadsheet', 'xlsx': 'bi-file-earmark-spreadsheet', 'ods': 'bi-file-earmark-spreadsheet',
    'png': 'bi-file-earmark-image', 'jpg': 'bi-file-earmark-image', 'jpeg': 'bi-file-earmark-image',
    'gif': 'bi-file-earmark-image', 'webp': 'bi-file-earmark-image',
}
# Tipos que el navegador puede mostrar directamente; el resto se descarga
EXTENSIONES_EN_LINEA = {'pdf', 'txt', 'png', 'jpg', 'jpeg', 'gif', 'webp'}
TAMANO_MAXIMO_MB = 20

COLORES_METODO = ['#d966ff', '#00bac6', '#ffd700', '#ff6fb5', '#00e676', '#ff8c42']

# Métodos que se pueden agregar de un clic cuando la lista está vacía
METODOS_SUGERIDOS = [
    {'nombre': 'Pomodoro', 'icono': 'bi-stopwatch', 'color': '#ff6fb5',
     'descripcion': 'Bloques de 25 minutos de estudio enfocado con 5 minutos de descanso.'},
    {'nombre': 'Técnica Feynman', 'icono': 'bi-lightbulb', 'color': '#ffd700',
     'descripcion': 'Explica el tema con palabras simples, como si se lo enseñaras a un niño.'},
    {'nombre': 'Repetición espaciada', 'icono': 'bi-arrow-repeat', 'color': '#00bac6',
     'descripcion': 'Repasa lo aprendido en intervalos cada vez más largos para no olvidarlo.'},
    {'nombre': 'Recuerdo activo', 'icono': 'bi-question-circle', 'color': '#d966ff',
     'descripcion': 'Ponte a prueba con preguntas en lugar de solo releer tus apuntes.'},
    {'nombre': 'Mapas mentales', 'icono': 'bi-diagram-3', 'color': '#00e676',
     'descripcion': 'Organiza las ideas de forma visual alrededor de un concepto central.'},
    {'nombre': 'Método Cornell', 'icono': 'bi-journal-text', 'color': '#ff8c42',
     'descripcion': 'Divide la hoja en notas, palabras clave y resumen para repasar mejor.'},
]


class MetodoEstudio(db.Model):
    __tablename__ = 'metodos_estudio'

    idMetodo = db.Column(db.Integer, primary_key=True)
    idUser = db.Column(db.Integer, db.ForeignKey('users.idUser'), nullable=False)
    nombre = db.Column(db.String(120), nullable=False)
    descripcion = db.Column(db.String(500), nullable=True)
    icono = db.Column(db.String(50), nullable=False, default='bi-book')
    color = db.Column(db.String(20), nullable=False, default='#d966ff')
    createdAt = db.Column(db.DateTime, default=datetime.now)

    tarjetas = db.relationship(
        'KanbanTarjeta', backref='metodo', cascade='all, delete-orphan',
        order_by='KanbanTarjeta.orden',
    )

    def conteo_por_columna(self):
        conteo = {clave: 0 for clave in CLAVES_COLUMNAS}
        for t in self.tarjetas:
            conteo[t.columna] = conteo.get(t.columna, 0) + 1
        return conteo

    def total_apuntes(self):
        return sum(len(t.apuntes) for t in self.tarjetas)

    def pct_hecho(self):
        total = len(self.tarjetas)
        return round(self.conteo_por_columna()['hecho'] / total * 100) if total else 0


class KanbanTarjeta(db.Model):
    __tablename__ = 'kanban_tarjetas'

    idTarjeta = db.Column(db.Integer, primary_key=True)
    idMetodo = db.Column(db.Integer, db.ForeignKey('metodos_estudio.idMetodo'), nullable=False)
    idUser = db.Column(db.Integer, db.ForeignKey('users.idUser'), nullable=False)
    titulo = db.Column(db.String(150), nullable=False)
    descripcion = db.Column(db.String(500), nullable=True)
    columna = db.Column(db.String(20), nullable=False, default='pendiente')
    orden = db.Column(db.Integer, nullable=False, default=0)
    createdAt = db.Column(db.DateTime, default=datetime.now)

    apuntes = db.relationship(
        'Apunte', backref='tarjeta', cascade='all, delete-orphan',
        order_by='Apunte.createdAt',
    )


class Apunte(db.Model):
    """Archivo de apuntes subido a una tarjeta del tablero que ya está en "Hecho".
    El archivo vive en disco (carpeta UPLOAD_FOLDER); aquí solo se guardan sus datos."""
    __tablename__ = 'apuntes'

    idApunte = db.Column(db.Integer, primary_key=True)
    idTarjeta = db.Column(db.Integer, db.ForeignKey('kanban_tarjetas.idTarjeta'), nullable=False)
    idUser = db.Column(db.Integer, db.ForeignKey('users.idUser'), nullable=False)
    nombreOriginal = db.Column(db.String(255), nullable=False)
    nombreGuardado = db.Column(db.String(255), nullable=False, unique=True)
    tamano = db.Column(db.Integer, nullable=False, default=0)
    createdAt = db.Column(db.DateTime, default=datetime.now)

    @property
    def extension(self):
        return os.path.splitext(self.nombreGuardado)[1].lstrip('.').lower()

    @property
    def icono(self):
        return EXTENSIONES_APUNTES.get(self.extension, 'bi-file-earmark')

    def tamano_texto(self):
        if self.tamano >= 1024 * 1024:
            return f"{self.tamano / (1024 * 1024):.1f} MB"
        return f"{max(1, round(self.tamano / 1024))} KB"
