"""
Función: Estilos visuales.

Contiene funciones para aplicar el "Tema Oscuro" o "Tema Claro".
Define los colores y bordes de la aplicación usando hojas de estilo
(CSS de Qt).

"""

# =================================================
# IMPORTACIONES NECESARIAS
# =================================================

from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QPalette, QColor
from PyQt6.QtCore import Qt

# =================================================
# FUNCIÓN APPLY_DARK_THEME (TEMA OSCURO)
# =================================================

# Configura la paleta de colores de la aplicación para el modo oscuro (Dark Mode).
# Utiliza el estilo "Fusion" de Qt como base y modifica los colores de la paleta para lograr un aspecto gris oscuro/negro con acentos azules.

def apply_dark_theme(app: QApplication):
    app.setStyle("Fusion")
    
    palette = QPalette()
    # Fondo general de ventanas.
    palette.setColor(QPalette.ColorRole.Window, QColor(53, 53, 53))
    # Texto general.
    palette.setColor(QPalette.ColorRole.WindowText, Qt.GlobalColor.white)
    # Fondo de controles (listas, cajas de texto).
    palette.setColor(QPalette.ColorRole.Base, QColor(25, 25, 25))
    # Fondo alterno (para filas de tablas impares, etc.).
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor(53, 53, 53))
    # Tooltips (Texto de ayuda).
    palette.setColor(QPalette.ColorRole.ToolTipBase, Qt.GlobalColor.black)
    palette.setColor(QPalette.ColorRole.ToolTipText, Qt.GlobalColor.white)
    # Texto en controles.
    palette.setColor(QPalette.ColorRole.Text, Qt.GlobalColor.white)
    # Botones.
    palette.setColor(QPalette.ColorRole.Button, QColor(53, 53, 53))
    palette.setColor(QPalette.ColorRole.ButtonText, Qt.GlobalColor.white)
    # Texto brillante (ej. errores).
    palette.setColor(QPalette.ColorRole.BrightText, Qt.GlobalColor.red)
    # Enlaces.
    palette.setColor(QPalette.ColorRole.Link, QColor(42, 130, 218))
    # Color de resaltado (selección).
    palette.setColor(QPalette.ColorRole.Highlight, QColor(42, 130, 218))
    palette.setColor(QPalette.ColorRole.HighlightedText, Qt.GlobalColor.black)
    
    app.setPalette(palette)
    
    # CSS adicional para widgets que no respetan totalmente la paleta o para personalizaciones específicas (como los bordes).
    app.setStyleSheet("""
        QToolTip { color: #ffffff; background-color: #2a82da; border: 1px solid white; }
        QTreeWidget { background-color: #252525; color: white; border: none; }
        QTextEdit, QTextBrowser { background-color: #303030; color: white; border: 1px solid #555; }
        QHeaderView::section { background-color: #353535; color: white; }
    """)

# =================================================
# FUNCIÓN APPLY_LIGHT_THEME (TEMA CLARO)
# =================================================

# Restaura el tema visual por defecto (Claro) de Qt.
# Limpia cualquier hoja de estilo personalizada previa.

def apply_light_theme(app: QApplication):
    app.setStyle("Fusion")
    app.setPalette(app.style().standardPalette())
    app.setStyleSheet("") # Limpiar estilos custom