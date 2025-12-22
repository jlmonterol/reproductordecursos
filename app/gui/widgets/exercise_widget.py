"""
Función: Bloque de ejercicios.

Muestra los botones específicos para las carpetas de ejercicios 
("Abrir Carpeta", "Abrir en IDE", "Copiar").

"""

# =================================================
# IMPORTACIONES NECESARIAS
# =================================================

import os
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton
from PyQt6.QtCore import Qt, QUrl
from PyQt6.QtGui import QIcon, QDesktopServices
from app.utils.paths import resource_path

# =================================================
# CLASE EXERCISEWIDGET (PANEL DE EJERCICIOS)
# =================================================

# Widget compuesto que aparece en el árbol de contenidos cuando el ítem es una carpeta.
# Contiene tres botones principales:

# 1. Abrir Carpeta (Explorador de archivos).
# 2. Abrir en IDE (VS Code, etc.).
# 3. Copiar Ejercicios (Al directorio de trabajo del usuario).

class ExerciseWidget(QWidget):
    
    # =================================================
    # CONSTRUCTOR (__INIT__)
    # =================================================
    
    def __init__(self, parent=None, folder_path="", folder_name="", dark_mode=False):
        super().__init__(parent)
        self.folder_path = folder_path
        self.folder_name = folder_name
        self.dark_mode = dark_mode
        
        # Callbacks: Funciones externas que se ejecutarán al hacer clic.
        # Se inyectan desde TreeManager o MainWindow.
        
        self.on_open_ide_click = None
        self.on_copy_click = None
        
        self.setup_ui()

    # =================================================
    # CONFIGURACIÓN DE INTERFAZ (SETUP_UI)
    # =================================================
    
    # Construye el layout vertical con dos filas de botones.
    # Carga los iconos correspondientes según el tema (Dark/Light).

    def setup_ui(self):
        v_layout = QVBoxLayout(self)
        v_layout.setContentsMargins(0, 0, 0, 0)
        v_layout.setSpacing(2)

        # --- FILA SUPERIOR (Abrir Carpeta + IDE) --- #
        row_top = QWidget()
        h_top = QHBoxLayout(row_top)
        h_top.setContentsMargins(0, 0, 0, 0)
        h_top.setSpacing(5)
        
        # Determinar sufijo de icono según modo oscuro
        suffix = "_dark.svg" if self.dark_mode else "_light.svg"

        # 1. Botón Abrir Carpeta Original
        btn_open = QPushButton(self.folder_name)
        btn_open.setToolTip("Abre el directorio original.")
        btn_open.clicked.connect(self._open_folder)
        
        icon_ex = resource_path(os.path.join("assets", "images", f"exercise{suffix}"))
        if os.path.exists(icon_ex):
            btn_open.setIcon(QIcon(icon_ex))
            
        # 2. Botón Abrir en IDE
        btn_ide = QPushButton(" Abrir en el IDE")
        btn_ide.setToolTip("Elige dónde abrir los ejercicios. (F8)")
        # Llama al callback solo si está definido
        btn_ide.clicked.connect(lambda: self.on_open_ide_click(self.folder_path) if self.on_open_ide_click else None)
        
        icon_ide = resource_path(os.path.join("assets", "images", f"ide{suffix}"))
        if os.path.exists(icon_ide):
            btn_ide.setIcon(QIcon(icon_ide))

        h_top.addWidget(btn_open, 1)
        h_top.addWidget(btn_ide, 1)
        v_layout.addWidget(row_top)

        # --- FILA INFERIOR (Copiar Ejercicios) --- #
        
        # 3. Botón Copiar a WorkDir
        btn_copy = QPushButton(" Copiar Ejercicios")
        btn_copy.setToolTip("Copia los ejercicios al directorio de trabajo configurado.")
        btn_copy.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_copy.clicked.connect(lambda: self.on_copy_click(self.folder_path) if self.on_copy_click else None)

        icon_copy = resource_path(os.path.join("assets", "images", f"copy{suffix}"))
        if os.path.exists(icon_copy):
            btn_copy.setIcon(QIcon(icon_copy))

        h_bottom = QHBoxLayout()
        h_bottom.setContentsMargins(0, 0, 0, 0)
        h_bottom.addWidget(btn_copy)
        
        v_layout.addLayout(h_bottom)

    # =================================================
    # ABRIR CARPETA (_OPEN_FOLDER)
    # =================================================
    
    # Usa los servicios de escritorio del sistema operativo para abrir el explorador de archivos en la ruta especificada.

    def _open_folder(self):
        QDesktopServices.openUrl(QUrl.fromLocalFile(self.folder_path))