"""
Función: Ventana de configuración para elegir la ruta del IDE (editor de código), la carpeta de trabajo y opciones para borrar datos.

"""

# =================================================
# IMPORTACIONES NECESARIAS
# =================================================

from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QFrame, QFileDialog, QMessageBox)
from PyQt6.QtCore import Qt
from app.data.data_manager import DataManager

# =================================================
# CLASE OPTIONSDIALOG (CONFIGURACIÓN)
# =================================================

# Ventana para configurar:

# 1. Ruta del IDE (Editor de código).
# 2. Directorio de Trabajo (donde se copian ejercicios).
# 3. Acciones de limpieza (Borrar historial, apuntes, etc.).

class OptionsDialog(QDialog):
    
    # =================================================
    # CONSTRUCTOR (__INIT__)
    # =================================================
    
    def __init__(self, parent, data_manager: DataManager):
        super().__init__(parent)
        self.data_manager = data_manager
        self.dark_mode = (self.data_manager.get_theme() == "dark")
        self.setup_ui()

    # =================================================
    # CONFIGURACIÓN DE INTERFAZ (SETUP_UI)
    # =================================================

    def setup_ui(self):
        self.setWindowTitle("Opciones")
        self.resize(500, 320)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint)

        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        # --- SECCIÓN IDE --- #
        
        ide_group = QFrame()
        ide_group.setFrameShape(QFrame.Shape.StyledPanel)
        ide_layout = QVBoxLayout(ide_group)
        
        lbl_ide = QLabel("Ruta del IDE (Editor de código):")
        lbl_ide.setStyleSheet("font-weight: bold;")
        ide_layout.addWidget(lbl_ide)

        hbox_ide = QHBoxLayout()
        self.txt_ide = QLabel()
        current_ide = self.data_manager.get_ide_path()
        self.txt_ide.setText(current_ide if current_ide else "No definido")
        
        base_txt_style = "border: 1px solid #777; padding: 4px;"
        if not self.dark_mode:
            base_txt_style += " background-color: #f0f0f0;"
        self.txt_ide.setStyleSheet(base_txt_style)
        
        btn_select_ide = QPushButton("Seleccionar...")
        btn_select_ide.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_select_ide.clicked.connect(self.select_ide_path)
        
        hbox_ide.addWidget(self.txt_ide, 1)
        hbox_ide.addWidget(btn_select_ide)
        ide_layout.addLayout(hbox_ide)
        layout.addWidget(ide_group)

        # --- DIRECTORIO DE TRABAJO --- #

        work_group = QFrame()
        work_group.setFrameShape(QFrame.Shape.StyledPanel)
        work_layout = QVBoxLayout(work_group)
        
        lbl_work = QLabel("Directorio de trabajo (Usuario/Prácticas):")
        lbl_work.setStyleSheet("font-weight: bold;")
        work_layout.addWidget(lbl_work)

        hbox_work = QHBoxLayout()
        self.txt_work = QLabel()
        current_work = self.data_manager.get_work_dir()
        self.txt_work.setText(current_work if current_work else "No definido")
        
        # Reutilizamos el estilo base
        base_txt_style = "border: 1px solid #777; padding: 4px;"
        if not self.dark_mode:
            base_txt_style += " background-color: #f0f0f0;"
        self.txt_work.setStyleSheet(base_txt_style)
        
        btn_select_work = QPushButton("Seleccionar...")
        btn_select_work.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_select_work.clicked.connect(self.select_work_path)
        
        hbox_work.addWidget(self.txt_work, 1)
        hbox_work.addWidget(btn_select_work)
        work_layout.addLayout(hbox_work)
        
        layout.addWidget(work_group)

        # --- SECCIÓN DE BORRADO --- #
        
        danger_group = QFrame()
        danger_group.setFrameShape(QFrame.Shape.StyledPanel)
        danger_layout = QVBoxLayout(danger_group)
        
        lbl_danger = QLabel("Gestión de Datos (Acciones Irreversibles):")
        lbl_danger.setStyleSheet("font-weight: bold; color: #cc0000;")
        lbl_danger.setAlignment(Qt.AlignmentFlag.AlignCenter)
        danger_layout.addWidget(lbl_danger)
        danger_layout.addSpacing(15)

        # Botones
        self.add_danger_button("Eliminar todos los apuntes", self.confirm_del_notes, danger_layout)
        self.add_danger_button("Eliminar historial de visualización", self.confirm_del_history, danger_layout)
        self.add_danger_button("Eliminar historial de evaluaciones", self.confirm_del_tests, danger_layout)
        
        btn_reset = self.add_danger_button("Restablecer todos los datos", self.confirm_reset_all, danger_layout)
        btn_reset.setStyleSheet("color: red; font-weight: bold;")

        layout.addWidget(danger_group)
        layout.addStretch()

        # Botón Cerrar
        btn_close = QPushButton("Cerrar")
        btn_close.setFixedWidth(120)
        btn_close.clicked.connect(self.accept)
        layout.addWidget(btn_close, alignment=Qt.AlignmentFlag.AlignCenter)

        self.apply_styles()
    
    # =================================================
    # AUXILIAR BOTÓN PELIGRO (ADD_DANGER_BUTTON)
    # =================================================

    def add_danger_button(self, text, slot, layout) -> QPushButton:
        btn = QPushButton(text)
        btn.clicked.connect(slot)
        layout.addWidget(btn)
        return btn
    
    # =================================================
    # APLICAR ESTILOS (APPLY_STYLES)
    # =================================================

    def apply_styles(self):
        if self.dark_mode:
            self.setStyleSheet("""
                QDialog { background-color: #353535; color: white; }
                QLabel { color: white; }
                QPushButton { background-color: #444; color: white; border: 1px solid #666; padding: 5px; }
                QPushButton:hover { background-color: #555; }
            """)
    
    # =================================================
    # SELECCIÓN DE IDE (SELECT_IDE_PATH)
    # =================================================

    def select_ide_path(self):
        path, _ = QFileDialog.getOpenFileName(self, "Seleccionar ejecutable", "", "Ejecutables (*.exe);;Todos (*.*)")
        if path:
            self.data_manager.set_ide_path(path)
            self.txt_ide.setText(path)
            # Nota: La actualización en tiempo real del padre se hará vía señales en fases futuras
            
    # ==========================================================
    # SELECCIÓN DE DIRECTORIO DE TRABAJO (SELECT_WORK_PATH)
    # ==========================================================
    
    def select_work_path(self):
        path = QFileDialog.getExistingDirectory(self, "Seleccionar Directorio de Trabajo")
        if path:
            self.data_manager.set_work_dir(path)
            self.txt_work.setText(path)

    # =================================================
    # CONFIRMACIÓN GENÉRICA (_CONFIRM)
    # =================================================

    # Usamos QMessageBox estándar de PyQt6 para simplificar, pero aplicando estilo si es necesario.
    def _confirm(self, title, text):
        msg = QMessageBox(self)
        msg.setWindowTitle(title)
        msg.setText(text)
        msg.setIcon(QMessageBox.Icon.Warning)
        
        # Botones traducidos
        btn_yes = msg.addButton("Sí, eliminar", QMessageBox.ButtonRole.YesRole)
        msg.addButton("Cancelar", QMessageBox.ButtonRole.NoRole)
        
        if self.dark_mode:
            msg.setStyleSheet("background-color: #353535; color: white; QPushButton { background-color: #444; color: white; }")
            
        msg.exec()
        return msg.clickedButton() == btn_yes

    # =================================================
    # ACCIONES DE BORRADO (SLOTS)
    # =================================================

    def confirm_del_notes(self):
        if self._confirm("Eliminar Apuntes", "¿Seguro que deseas borrar todos los apuntes?"):
            self.data_manager.clear_all_notes()
            # Feedback visual simple
            QMessageBox.information(self, "Éxito", "Apuntes eliminados.")

    def confirm_del_history(self):
        if self._confirm("Eliminar Historial", "¿Borrar historial de visualización?"):
            self.data_manager.clear_all_history()
            QMessageBox.information(self, "Éxito", "Historial eliminado.")

    def confirm_del_tests(self):
        if self._confirm("Eliminar Tests", "¿Borrar historial de evaluaciones?"):
            self.data_manager.clear_all_tests()
            QMessageBox.information(self, "Éxito", "Puntajes eliminados.")

    def confirm_reset_all(self):
        if self._confirm("Restablecer Todo", "¡Se borrará TODO el progreso y configuración!"):
            self.data_manager.reset_all_data()
            self.txt_ide.setText("No definido")
            QMessageBox.information(self, "Reset", "Aplicación restablecida.")