"""
Función: Definición de estructuras de datos.

Define clases simples (dataclasses) como VideoItem y CourseStructure. Aunque en este
código se usa poco, sirve para estructurar la información de un video
de forma ordenada.

"""

# =================================================
# IMPORTACIONES NECESARIAS
# =================================================

# Importamos dataclasses para crear estructuras de datos limpias y tipado para validación.
from dataclasses import dataclass, field
from typing import List, Optional

# =================================================
# CLASE VIDEOITEM (MODELO DE DATOS)
# =================================================

# Representa un único archivo de video dentro del sistema.
# Almacena su ruta, título, si ya fue completado y los apuntes asociados.

@dataclass
class VideoItem:
    path: str
    title: str
    is_completed: bool = False
    notes: str = ""

# =================================================
# CLASE COURSESTRUCTURE (ESTRUCTURA DEL CURSO)
# =================================================

# Modelo para representar la estructura completa de un curso.
# Contiene la ruta raíz y una lista de objetos VideoItem.
# (Preparado para expansiones futuras de la lógica).

@dataclass
class CourseStructure:
    root_path: str
    videos: List[VideoItem] = field(default_factory=list)