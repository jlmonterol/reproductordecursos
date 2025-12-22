"""
Función: Etiquetas personalizadas que detectan clics (como la imagen del curso o el link del correo).

"""

# =================================================
# IMPORTACIONES NECESARIAS
# =================================================

from PyQt6.QtWidgets import QLabel, QApplication, QToolTip
from PyQt6.QtCore import Qt, pyqtSignal, QPoint
from PyQt6.QtGui import QPalette

# =================================================
# CLASE COURSEIMAGELABEL (IMAGEN DE CURSO)
# =================================================

# QLabel especializada para mostrar la miniatura del curso (80x80).
# Emite una señal personalizada 'doubleClicked' para permitir acciones adicionales (como abrir la carpeta del curso) al hacer doble clic.

class CourseImageLabel(QLabel):
    # Señal personalizada que no trae QLabel por defecto
    doubleClicked = pyqtSignal()

    # =================================================
    # CONSTRUCTOR (__INIT__)
    # =================================================

    def __init__(self, parent=None):
        super().__init__(parent)
        self._custom_tooltip_text = ""

    # =================================================
    # CONFIGURACIÓN TOOLTIP (SETCUSTOMTOOLTIP)
    # =================================================
    
    # Asigna el texto flotante de ayuda. Se mantiene como método separado por si se requiere lógica adicional de estilo en el futuro.

    def setCustomToolTip(self, text: str):
        self._custom_tooltip_text = text
        self.setToolTip(text)

    # =================================================
    # EVENTO DOBLE CLIC (MOUSEDOUBLECLICKEVENT)
    # =================================================
    
    # Sobrescribe el evento nativo de Qt. Si el usuario hace doble clic izquierdo, emite nuestra señal personalizada para que la ventana principal reaccione.

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.doubleClicked.emit()
        super().mouseDoubleClickEvent(event)

# =================================================
# CLASE EMAILLABEL (ENLACES DE CORREO)
# =================================================

# QLabel configurada para mostrar texto enriquecido (HTML) y permitir abrir enlaces externos (mailto: o http:) con el navegador/cliente por defecto.

class EmailLabel(QLabel):
    
    # =================================================
    # CONSTRUCTOR (__INIT__)
    # =================================================
    
    def __init__(self, text: str, parent=None):
        super().__init__(text, parent)
        self.setOpenExternalLinks(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    # =================================================
    # CONFIGURACIÓN TOOLTIP (SETCUSTOMTOOLTIP)
    # =================================================

    def setCustomToolTip(self, text: str):
        self.setToolTip(text)