"""
Función: Gestor de rutas absolutas.

Vital para que el programa encuentre sus imágenes e iconos tanto cuando
está en desarrollo como cuando se compila en un .exe (usando _MEIPASS).

"""

# =================================================
# IMPORTACIONES NECESARIAS
# =================================================

import sys
import os

# =================================================
# FUNCIÓN GET_PROJECT_ROOT (RAÍZ DEL PROYECTO)
# =================================================

# Obtiene la ruta base absoluta del proyecto.
# Es vital porque detecta si estás corriendo en modo desarrollo (código fuente) o en modo compilado (_MEIPASS con PyInstaller).

def get_project_root() -> str:
    """
    Devuelve la ruta raíz del proyecto.
    Maneja la diferencia entre ejecución normal y PyInstaller (_MEIPASS).
    """
    if hasattr(sys, "_MEIPASS"):
        # En modo ejecutable (PyInstaller), _MEIPASS es la raíz temporal
        return sys._MEIPASS # type: ignore
    else:
        # En desarrollo, este archivo está en app/utils/paths.py
        # Subimos 3 niveles: utils -> app -> RAÍZ
        return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# =================================================
# FUNCIÓN RESOURCE_PATH (RUTA DE RECURSOS)
# =================================================

# Genera una ruta absoluta correcta para cargar archivos externos (imágenes, iconos, audios), independientemente de si el programa está instalado o en desarrollo.
# Se debe usar siempre en lugar de rutas relativas simples.

def resource_path(relative_path: str) -> str:
    """
    Devuelve la ruta absoluta a un recurso, compatible con PyInstaller.
    
    Args:
        relative_path (str): Ruta relativa desde la raíz del proyecto.
                             Ej: "images/icon.png" o "vlc"
    """
    base_path = get_project_root()
    return os.path.join(base_path, relative_path)