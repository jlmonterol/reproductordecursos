"""
Función: Es el punto de entrada de la aplicación.

Configura el entorno (especialmente para el VLC VideoLAN), muestra el mensaje de bienvenida,
pide al usuario que seleccione la carpeta raíz del curso e inicia la ventana principal (MainWindow.py).

"""

# =================================================
# IMPORTACIONES NECESARIAS
# =================================================

import sys
import os

# 1. Configuración de entorno.

# Importamos la configuración de VLC.
from app.utils.vlc_setup import setup_vlc_environment
if not setup_vlc_environment():
    print("Advertencia: Revisar carpeta VLC.")

from PyQt6.QtWidgets import QApplication, QMessageBox, QFileDialog
from PyQt6.QtGui import QIcon
from app.gui.main_window import MainWindow
from app.utils.paths import resource_path

# Importar DataManager para acceder a la configuración antes de la ventana principal.
from app.data.data_manager import DataManager

# =================================================
# FUNCIÓN PRINCIPAL (MAIN)
# =================================================

# Punto de entrada de la aplicación.

# 1. Configura la aplicación Qt.
# 2. Muestra un mensaje de bienvenida obligatorio.
# 3. Obliga al usuario a seleccionar un directorio de curso.
# 4. Inicia la ventana principal solo si se seleccionó una ruta válida.

def main():
    # Fix para escalado en pantallas de alta resolución.
    os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"
    app = QApplication(sys.argv)
    
    # Metadatos de la instancia de la aplicación.
    app.setApplicationName("Reproductor de Cursos")
    app.setOrganizationName("JLMLSoft")

    # Configuración del icono de la ventana y barra de tareas.
    icon_path = resource_path("ReproductorCursos.ico")
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))

    # 1. Mensaje de bienvenida
    
    msg = QMessageBox()
    msg.setWindowTitle("¡Información Importante!")
    msg.setIcon(QMessageBox.Icon.Information)
    msg.setText(
        "¡Hola! ¡Bienvenido(a)!\n\n"
        "Este aplicativo ha sido desarrollado íntegramente en Python, utilizando la biblioteca "
        "PyQt6 y la librería multimedia VLC.\n\n"
        "Al presionar el botón \"Aceptar\", deberá localizar y seleccionar el directorio principal "
        "donde se encuentre el curso de programación o las grabaciones de audio. Es importante "
        "elegir la raíz del directorio y no alguno de sus subdirectorios.\n\n"
        "¡Que lo disfrutes!"
    )
    btn_accept = msg.addButton("Aceptar", QMessageBox.ButtonRole.AcceptRole)
    btn_cancel = msg.addButton("Cancelar", QMessageBox.ButtonRole.RejectRole)
    msg.exec()

    if msg.clickedButton() == btn_cancel:
        sys.exit(0)

    # 2. Inicializar DataManager temporalmente para obtener la última ruta. (Persistencia).
    temp_dm = DataManager()
    # Necesitamos leer la última ruta guardada (last_open_dir) antes de crear la ventana principal.
    last_dir = temp_dm.get_last_open_dir()

    # 3. Cuador de diálogo de selección de carpeta (usando last_dir).
    initial_path = QFileDialog.getExistingDirectory(None, "Selecciona el directorio raíz del curso", last_dir)
    
    if not initial_path:
        sys.exit(0)

    # 4. Iniciar Ventana Principal pasando la ruta seleccionada.
    # Aquí ya tenemos una ruta válida, así que instanciamos y mostramos la UI completa.
    window = MainWindow()
    window.set_course_path_init(initial_path) 
    window.show()
    
    # Iniciar el bucle de eventos de Qt
    sys.exit(app.exec())

# =================================================
# ENTRY POINT
# =================================================

if __name__ == "__main__":
    main()