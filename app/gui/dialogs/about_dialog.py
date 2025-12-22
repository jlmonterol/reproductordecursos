"""
Función: Ventana que muestra la información de "Acerca de" (mensaje, versión y fecha de publicación).

"""

# =================================================
# IMPORTACIONES NECESARIAS
# =================================================

from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton
from PyQt6.QtCore import Qt
from app.config import APP_VERSION, AUTHOR, PUBLISH_DATE, REPO_GITHUB

# =================================================
# CLASE ABOUTDIALOG (VENTANA ACERCA DE)
# =================================================

# Diálogo modal sencillo que muestra la información del desarrollador, la versión de la aplicación y un mensaje de agradecimiento.

class AboutDialog(QDialog):
    
    # =================================================
    # CONSTRUCTOR (__INIT__)
    # =================================================
    
    def __init__(self, parent=None, dark_mode=False):
        super().__init__(parent)
        self.dark_mode = dark_mode
        self.setup_ui()
        
    # =================================================
    # CONFIGURACIÓN DE INTERFAZ (SETUP_UI)
    # =================================================
    
    # Construye los elementos visuales: etiquetas de texto y botón de aceptar.
    # Elimina el botón de ayuda de la barra de título para limpieza visual.

    def setup_ui(self):
        self.setWindowTitle("Acerca de: Reproductor de Cursos")
        self.setMinimumWidth(380)
        
        # Eliminar el botón de ayuda (?) de la barra de título
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint)

        layout = QVBoxLayout(self)
        layout.addSpacing(15)

        body_text = (
            "Esta aplicación ha sido desarrollada con Python utilizando la biblioteca PyQt6 y "
            "la librería multimedia VLC. Su propósito es exclusivamente académico, orientado "
            "a cursos de programación.\n\n"
            "No persigue fines de lucro; su objetivo es ofrecer una herramienta práctica para "
            "reproducir los videos de manera dinámica y agradable.\n\n"
            "El uso adecuado de este aplicativo recae únicamente en el usuario, quien se "
            "compromete a no difundir material protegido por derechos de autor, como cursos "
            "de pago.\n\n"
            "Gracias por utilizarla, por dedicar unos minutos a leer este mensaje y, sobre todo, "
            "por tu interés en aprender a programar.\n\n"
            "¡ Saludos !"
        )
        
        lbl_body = QLabel(body_text)
        lbl_body.setWordWrap(True)
        lbl_body.setAlignment(Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(lbl_body)
        layout.addSpacing(10)

        # Definimos el color del enlace según el modo (oscuro o claro) para que resalte
        link_color = "#4da6ff" if self.dark_mode else "#0000ff"

        # Usamos HTML para formatear. 
        sig_text = (
            f"Versión {APP_VERSION}<br><br>"
            f"{PUBLISH_DATE}<br><br>"
            f"<a href='{REPO_GITHUB}' style='color: {link_color}; text-decoration: none;'>{REPO_GITHUB}</a>"
        )

        lbl_sig = QLabel(sig_text)
        lbl_sig.setAlignment(Qt.AlignmentFlag.AlignRight)
        
        # Esta peermite que al dar clic se abra el navegador web.
        lbl_sig.setOpenExternalLinks(True) 

        lbl_sig.setStyleSheet("font-weight: bold;" if not self.dark_mode else "font-weight: bold;")
        layout.addWidget(lbl_sig)
        layout.addSpacing(20)

        # Botón
        btn_layout = QHBoxLayout()
        btn_ok = QPushButton("Aceptar")
        btn_ok.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_ok.clicked.connect(self.accept)
        
        btn_layout.addStretch()
        btn_layout.addWidget(btn_ok)
        btn_layout.addStretch()
        
        layout.addLayout(btn_layout)
        
        self.apply_styles()

    # =================================================
    # APLICAR ESTILOS (APPLY_STYLES)
    # =================================================
    
    # Aplica colores oscuros si el modo Dark está activado.

    def apply_styles(self):
        if self.dark_mode:
            self.setStyleSheet("""
                QDialog { background-color: #353535; color: white; }
                QLabel { color: white; }
                QPushButton { background-color: #444; color: white; border: 1px solid #666; padding: 5px 15px; }
                QPushButton:hover { background-color: #555; }
            """)