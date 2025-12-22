"""
Función: Ventana para elegir qué apuntes exportar a Excel/CSV (solo el actual, todo el curso o todo global).

"""

# =================================================
# IMPORTACIONES NECESARIAS
# =================================================

import os
import csv

from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QRadioButton, QPushButton, QFileDialog, QMessageBox)
from PyQt6.QtCore import Qt
from app.data.data_manager import DataManager

# =================================================
# CLASE EXPORTNOTESDIALOG (EXPORTACIÓN)
# =================================================

# Diálogo que permite al usuario elegir el alcance de la exportación de sus apuntes:

# 1. Solo el video actual.
# 2. Todo el curso actual.
# 3. Todos los cursos (Global).

class ExportNotesDialog(QDialog):
    
    # =================================================
    # CONSTRUCTOR (__INIT__)
    # =================================================
    
    def __init__(self, parent, data_manager: DataManager, current_course_path: str, current_video_path=None):
        super().__init__(parent)
        self.data_manager = data_manager
        self.course_path = current_course_path
        self.video_path = current_video_path
        self.dark_mode = (self.data_manager.get_theme() == "dark")
        self.setup_ui()

    # =================================================
    # CONFIGURACIÓN DE INTERFAZ (SETUP_UI)
    # =================================================

    def setup_ui(self):
        self.setWindowTitle("Exportación de apuntes")
        self.resize(450, 170)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Seleccione qué tipo de exportación desea realizar:"))
        layout.addSpacing(15)

        self.rb_current = QRadioButton("Exportar únicamente los apuntes del presente audio/vídeo.")
        self.rb_course = QRadioButton("Exportar todos los apuntes del presente curso.")
        self.rb_all = QRadioButton("Exportar todos los apuntes del aplicativo (Global).")

        if self.video_path:
            self.rb_current.setChecked(True)
        else:
            self.rb_current.setEnabled(False)
            self.rb_course.setChecked(True)

        layout.addWidget(self.rb_current)
        layout.addWidget(self.rb_course)
        layout.addWidget(self.rb_all)
        layout.addStretch()

        btn_layout = QHBoxLayout()
        btn_export = QPushButton("Exportar")
        btn_export.clicked.connect(self.export_action)
        btn_cancel = QPushButton("Cancelar")
        btn_cancel.clicked.connect(self.reject)

        # ... (dentro de setup_ui)
        btn_layout = QHBoxLayout()
        btn_export = QPushButton("Exportar")
        btn_export.clicked.connect(self.export_action)
        btn_cancel = QPushButton("Cancelar")
        btn_cancel.clicked.connect(self.reject)

        # CENTRADO DE BOTONES
        btn_layout.addStretch()  # <--- RESORTE IZQUIERDO
        btn_layout.addWidget(btn_export)
        btn_layout.addWidget(btn_cancel)
        btn_layout.addStretch()  # <--- RESORTE DERECHO
        
        layout.addLayout(btn_layout)
        self.apply_styles()
        
    # =================================================
    # APLICAR ESTILOS (APPLY_STYLES)
    # =================================================

    def apply_styles(self):
        if self.dark_mode:
            self.setStyleSheet("""
                QDialog { background-color: #353535; color: white; }
                QLabel, QRadioButton { color: white; }
                QPushButton { background-color: #444; color: white; border: 1px solid #666; padding: 5px; }
            """)

    # =================================================
    # LÓGICA DE EXPORTACIÓN (EXPORT_ACTION)
    # =================================================
    
    # Recopila los datos según la opción seleccionada, abre un cuadro de diálogo para guardar archivo y escribe el CSV.

    def export_action(self):
        rows = []
        
        # 1. Recopilar datos
        if self.rb_current.isChecked() and self.video_path:
            rel = os.path.relpath(self.video_path, self.course_path)
            note = self.data_manager.get_notes(self.course_path, rel)
            if note.strip():
                rows.append([os.path.basename(self.course_path), os.path.basename(rel), note])
        
        elif self.rb_course.isChecked():
            # Accedemos a la data interna del manager (un poco intrusivo pero necesario aquí)
            key = self.data_manager._get_course_key(self.course_path)
            if key in self.data_manager.data["courses"]:
                notes_dict = self.data_manager.data["courses"][key]["notes"]
                for rel, text in notes_dict.items():
                    if text.strip():
                        rows.append([os.path.basename(self.course_path), os.path.basename(rel), text])

        elif self.rb_all.isChecked():
            for c_key, c_data in self.data_manager.data["courses"].items():
                c_name = os.path.basename(c_key)
                for rel, text in c_data.get("notes", {}).items():
                    if text.strip():
                        rows.append([c_name, os.path.basename(rel), text])

        if not rows:
            QMessageBox.information(self, "Información", "No hay apuntes para exportar.")
            return

        # 2. Guardar archivo
        path, _ = QFileDialog.getSaveFileName(self, "Guardar CSV", "", "CSV (*.csv)")
        if path:
            try:
                with open(path, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f, delimiter=';')
                    writer.writerow(["Curso", "Archivo", "Apuntes"])
                    writer.writerows(rows)
                QMessageBox.information(self, "Éxito", "Exportación completada.")
                self.accept()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Fallo al guardar: {e}")