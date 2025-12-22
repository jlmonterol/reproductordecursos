"""
Función: Archivo de constantes globales.

Define valores que se usan en toda la app, como el nombre de la aplicación, versión,
extensiones de archivo permitidas (mp4, mkv, mp3...), colores por defecto y nombres
de carpetas de datos.

"""

# =================================================
# CONSTANTES GLOBALES DE LA APLICACIÓN
# =================================================

# Metadatos de la aplicación
APP_NAME = "Reproductor de Cursos v2.1"
APP_VERSION = "2.1"
PUBLISH_DATE = "14 de Diciembre del 2025"
AUTHOR = "Jose Luis Montero Laguado"
CONTACT_EMAIL = "jlmonterol@outlook.com"
# Asunto pre-codificado para enlaces mailto: (los espacios son %20)
CONTACT_SUBJECT = "Feedback%20Reproductor%20Cursos"
REPO_GITHUB = "https://github.com/jlmonterol/reproductordecursos"

# =================================================
# EXTENSIONES SOPORTADAS
# =================================================

# Tuplas de extensiones soportadas (Se pueden adicionar más si es necesario, recordar que VLC debe soportarlas)
VIDEO_EXTS = ('.mp4', '.wmv', '.avi', '.mkv')
AUDIO_EXTS = ('.m4a', '.mp3', '.oga', '.wav')

# =================================================
# CONFIGURACIÓN POR DEFECTO
# =================================================

DEFAULT_THEME = "light"
DEFAULT_VOLUME = 80
POMODORO_DEFAULT_MINUTES = 25

# =================================================
# RUTAS DE DATOS (PERSISTENCIA)
# =================================================

# Nombres de carpetas y archivos para guardar la configuración del usuario en AppData.

DATA_FOLDER_NAME = "JLMLSoft"
DATA_FILE_NAME = "user_data.data"