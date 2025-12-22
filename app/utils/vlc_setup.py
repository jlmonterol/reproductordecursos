"""
Función: Configurador de entorno VLC.

Le dice al sistema operativo dónde están las DLLs de VLC incluidas
en el proyecto para que no sea necesario tener VLC instalado en la
computadora del usuario.

"""

# =================================================
# IMPORTACIONES NECESARIAS
# =================================================

import os
from app.utils.paths import resource_path

# =================================================
# FUNCIÓN SETUP_VLC_ENVIRONMENT (CONFIGURACIÓN VLC)
# =================================================

# Configura las variables de entorno del sistema operativo (PATH) para obligar a Python a usar los archivos binarios (DLLs) de VLC que están incluidos dentro de la carpeta del proyecto, en lugar de buscar una instalación global.
# Debe ejecutarse ANTES de importar el módulo 'vlc'.

def setup_vlc_environment() -> bool:
    """
    Returns:
        bool: True si se encontró la carpeta vlc y se configuró, False en caso contrario.
    """
    vlc_local_path = resource_path("vlc")

    if os.path.exists(vlc_local_path):
        # 1. Definir ruta del módulo para python-vlc
        os.environ['PYTHON_VLC_MODULE_PATH'] = vlc_local_path
        
        # 2. Agregar al PATH del sistema para cargar dependencias (libvlc.dll, libvlccore.dll)
        current_path = os.environ.get('PATH', '')
        os.environ['PATH'] = f"{vlc_local_path};{current_path}"
        
        return True
    
    return False