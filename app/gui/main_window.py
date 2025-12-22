""""
Función: La ventana principal y orquestador central.

Es el archivo más grande e importante. Conecta todo: crea los paneles, botones, menús y conecta
las acciones (clics) con la lógica (reproducir, pausar, guardar nota). Gestiona los eventos del
teclado (atajos) y la disposición general.

"""

# =================================================
# IMPORTACIONES NECESARIAS
# =================================================

import os
import sys
import csv
import datetime
import html
import re
import shutil
from typing import Optional


# Importamos todos los widgets necesarios de PyQt6

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QSplitter, 
    QTreeWidget, QTreeWidgetItem, QTreeWidgetItemIterator, 
    QLabel, QPushButton, QSlider, QFrame, QCheckBox, 
    QTextBrowser, QTextEdit, QScrollArea, QFileDialog, QMessageBox, 
    QApplication, QMenu, QStyle, QSizePolicy, QDialog, QRadioButton,
    QDialogButtonBox, QButtonGroup, QSpacerItem
    
)
from PyQt6.QtCore import Qt, QSize, QEvent, QTimer, QUrl, QByteArray
from PyQt6.QtGui import QIcon, QAction, QDesktopServices, QPixmap, QColor, QPalette, QKeySequence, QShortcut

# Importaciones de NUESTRA arquitectura

from app.config import VIDEO_EXTS, AUDIO_EXTS, APP_NAME
from app.utils.paths import resource_path
from app.utils.helpers import format_ms_to_time, clean_title_text, format_date_name, text_to_html_link
from app.data.data_manager import DataManager
from app.logic.player_ctrl import PlayerController
from app.logic.scanner import CourseScanner
from app.logic.pomodoro import PomodoroTimer
from app.logic.file_manager import FileManager

# Widgets y Diálogos Propios

from app.gui.widgets.exercise_widget import ExerciseWidget
from app.gui.widgets.video_widget import VideoWidget
from app.gui.widgets.custom_labels import CourseImageLabel, EmailLabel
from app.gui.dialogs.about_dialog import AboutDialog
from app.gui.dialogs.options_dialog import OptionsDialog
from app.gui.dialogs.pomodoro_dialog import PomodoroDialog
from app.gui.dialogs.test_dialog import TestEvaluationDialog
from app.gui.dialogs.export_dialog import ExportNotesDialog
from app.gui.tree_manager import CourseTreeManager
from app.gui.styles import apply_dark_theme, apply_light_theme


# =================================================
# CLASE CUSTOMTEXTBROWSER (NAVEGADOR MEJORADO)
# =================================================

# Una pequeña subclase de QTextBrowser para tener un menú contextual (Clic derecho) en ESPAÑOL (Copiar, Seleccionar todo), ya que el de Qt viene en inglés por defecto. (Posible uso para cambiar el idioma a la interfaz)
class CustomTextBrowser(QTextBrowser):
    def contextMenuEvent(self, event):
        menu = QMenu(self)
        action_copy = menu.addAction("Copiar")
        action_copy.triggered.connect(self.copy)
        if not self.textCursor().hasSelection():
            action_copy.setEnabled(False)
        
        action_select_all = menu.addAction("Seleccionar todo")
        action_select_all.triggered.connect(self.selectAll)
        
        anchor_url = self.anchorAt(event.pos())
        if anchor_url:
            menu.addSeparator()
            action_link = menu.addAction("Copiar enlace")
            action_link.triggered.connect(lambda: QApplication.clipboard().setText(anchor_url))
        
        menu.exec(event.globalPos())

# =================================================
# CLASE MAINWINDOW (VENTANA PRINCIPAL)
# =================================================

# Esta es la clase maestra de la aplicación. Hereda de QMainWindow.
# Coordina la UI, el reproductor de video, la base de datos y la lógica de negocio.

class MainWindow(QMainWindow):

    # =================================================
    # CONSTRUCTOR (__INIT__)
    # =================================================
    
    # Inicializa los controladores, carga la configuración guardada,
    # construye la interfaz gráfica y conecta las señales (eventos).

    def __init__(self):
        super().__init__()
        
        # 1. Inicializar Lógica y Datos.
        
        self.data_manager = DataManager()
        self.player = PlayerController()

        # Variables de estado interno.
        self.course_path = ""
        self.current_media_info = {} # Diccionario con info del video actual.

        # Cargar preferencia de tema guardada (Oscuro/Claro)
        self.dark_mode = (self.data_manager.get_theme() == "dark")
        self.is_video_fullscreen = False
        
        # Timer para la cuenta regresiva (Reproducción continua).
        self.countdownTimer = QTimer()
        self.countdownTimer.setInterval(1000) # 1 segundo
        self.countdownTimer.timeout.connect(self._on_countdown_tick)
        self.countdown_remaining = 0
        self.next_item_candidate = None

        # Configuración Lógica Pomodoro.
        self.pomodoro_logic = PomodoroTimer()
        
        # Conectar señales del motor Pomodoro a métodos de la ventana.
        self.pomodoro_logic.tick.connect(self._on_pomodoro_tick)
        self.pomodoro_logic.phase_changed.connect(self._on_pomodoro_phase)
        self.pomodoro_logic.finished.connect(self._on_pomodoro_finished)
        self.pomodoro_logic.stopped.connect(self._on_pomodoro_stopped)
        # Implementación para conectart la señal de Pausa.
        self.pomodoro_logic.paused_status.connect(self._on_pomodoro_paused_status)
        # Variable para validar si Pomodoro está activo.
        self.is_pomodoro_active = False
        # Variable para guardar si debemos pausar video.
        self.pomodoro_pause_video = False

        # Timer para efecto visual de parpadeo (Pausa Pomodoro).
        self.blink_timer = QTimer(self)
        self.blink_timer.setInterval(500) # 500ms
        self.blink_timer.timeout.connect(self._blink_pomodoro_label)
        self.blink_label_visible = True
        
        # Configuración Base de la Ventana.
        self.setWindowTitle(APP_NAME)
        # Tamaño por defecto (se sobrescribirá si hay datos guardados).
        self.resize(1200, 720) 
        icon_path = resource_path("ReproductorCursos.ico")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        # 2. Construir Interfaz (Método Gigante).
        
        self.setup_ui()
        
        # Delegar la gestión del árbol al TreeManager.
        self.tree_manager = CourseTreeManager(self.tree, self.data_manager, self.dark_mode)

        # 3. Conectar Señales del Reproductor (PlayerController).
        
        # Conectamos eventos del VLC (cambio de tiempo, fin de video) a la UI.
        self.player.time_changed.connect(self._on_player_time_changed)
        self.player.position_changed.connect(self._on_player_position_changed)
        self.player.play_state_changed.connect(self._on_player_state_changed)
        self.player.finished.connect(self._on_player_finished)
        
        # 4. Vincular el VideoWidget con el Player.
        
        # Esto le dice a VLC "pinta el video dentro de este widget negro".
        self.player.set_video_output(self.videoWidget)

        # 5. Aplicar Tema Inicial.
        
        if self.dark_mode:
            self.apply_dark_theme()
        else:
            self.apply_light_theme()

        # 6. Filtro de eventos global (Para detectar teclas especiales si es necesario).
        self.installEventFilter(self)
        
        # 7. Ajustes finales visuales.

        # Esto asegura que los colores del slider y títulos sean correctos al iniciar
        self._apply_slider_style()
        self._apply_title_styles()
        
        # Forzar color inicial del tiempo
        time_color = "#dddddd" if self.dark_mode else "#333333"
        self.lbl_time.setStyleSheet(f"color: {time_color};")
        
        # 8. Restaurar estado previo (Posición de ventana, tamaño de paneles)
        self._restore_ui_state()

        # 9. Inicializar atajos de teclado (Shortcuts)
        self.setup_shortcuts()
     
    # =================================================
    # DIÁLOGO DE EXPORTACIÓN (SHOW_EXPORT_DIALOG)
    # =================================================
        
    def show_export_dialog(self):
        current_vid = None
        if self.current_media_info:
            current_vid = self.current_media_info["path"]
            
        dlg = ExportNotesDialog(self, self.data_manager, self.course_path, current_vid)
        dlg.exec()

    # =================================================
    # EVENTO CIERRE DE VENTANA (CLOSEEVENT)
    # =================================================
    
    # Se ejecuta automáticamente al cerrar la app.
    # Guarda la geometría de la ventana y la posición de los divisores (splitters) para que al abrirla de nuevo esté igual.

    def closeEvent(self, event):
        # 1. Guardar Geometría (Tamaño y Posición)
        geo = self.saveGeometry().toHex().data().decode('utf-8')
        self.data_manager.set_window_geometry(geo)
        # 2. Guardar Estado de Paneles (Splitters)
        main_state = self.main_splitter.saveState().toHex().data().decode('utf-8')
        self.data_manager.set_splitter_state("main_splitter", main_state)
        # Splitter Derecho (Video vs Notas)
        right_state = self.right_splitter.saveState().toHex().data().decode('utf-8')
        self.data_manager.set_splitter_state("right_splitter", right_state)
        # Continuar con el cierre normal
        super().closeEvent(event)

    # =================================================
    # FILTRO DE EVENTOS (EVENTFILTER)
    # =================================================
    
    # Permite interceptar eventos antes de que lleguen a los widgets hijos.
    # Se usa aquí para detectar el DOBLE CLIC DERECHO en el árbol (marcar visto).
    
    def eventFilter(self, watched, event):
        # Detectar doble clic derecho en el área visual del árbol.
        if watched == self.tree.viewport():
            if event.type() == QEvent.Type.MouseButtonDblClick:
                if event.button() == Qt.MouseButton.RightButton:
                    item = self.tree.itemAt(event.pos())
                    if item:
                        self._toggle_item_completion(item)
                        return True 
        
        return super().eventFilter(watched, event)

    # =================================================
    # LÓGICA DE CUENTA REGRESIVA (_ON_COUNTDOWN_TICK)
    # =================================================
    
    # Maneja la lógica de "Reproducción Continua". Muestra un aviso en pantalla antes de saltar al siguiente video automáticamente.
    
    def _cancel_countdown(self):
        if self.countdownTimer.isActive():
            self.countdownTimer.stop()
        self.countdownLabel.setVisible(False)
        self.next_item_candidate = None

    # Se ejecuta cada segundo cuando hay una cuenta regresiva; si llega a cero, reproduce el siguiente video.
    def _on_countdown_tick(self):
        self.countdown_remaining -= 1
        
        if self.countdown_remaining > 0:
            self.countdownLabel.setText(
                f"Reproducción continua: siguiente vídeo/audio en {self.countdown_remaining} segundos..."
            )
        else:
            # Tiempo cumplido: Saltar al siguiente.
            self._cancel_countdown()
            
            # Ejecutar el siguiente video.
            if self.next_item_candidate:
                self.tree.setCurrentItem(self.next_item_candidate)
            # Recuperar data para cargar.
                data = self.next_item_candidate.data(0, Qt.ItemDataRole.UserRole)
                self.load_media(data)
            else:
                self.play_next()

    # ===============================================================
    # BÚSQUEDA DEL SIGUIENTE ÍTEM (_FIND_NEXT_ITEM_CANDIDATE)
    # ===============================================================
    
    # Recorre el árbol linealmente para encontrar qué nodo sigue al actual sin reproducirlo todavía.

    def _find_next_item_candidate(self):
        if not self.current_media_info: return None
        # ... (Lógica de iteración sobre QTreeWidgetItemIterator) ...
        # (Código omitido para brevedad, ver archivo original)
        # Devuelve el QTreeWidgetItem siguiente o None.

        # Recuperar ruta actual de forma segura
        current_full_path = (self.current_media_info.get("path") or 
                             self.current_media_info.get("audio_path") or 
                             self.current_media_info.get("video_path"))

        iterator = QTreeWidgetItemIterator(self.tree)
        current_found = False
        
        while iterator.value():
            item = iterator.value()
            data = item.data(0, Qt.ItemDataRole.UserRole)
            
            if not data:
                iterator += 1
                continue

            item_path = data.get("path") or data.get("audio_path") or data.get("video_path")
            item_type = data.get("type")

            if not current_found:
                if item_path and item_path == current_full_path:
                    current_found = True
            elif current_found:
                if item_type in ["media", "video", "audio"]:
                    return item
            
            iterator += 1
        return None

    # =================================================
    # CONFIGURACIÓN DE UI (SETUP_UI)
    # =================================================
    
    # Construye toda la estructura visual: Paneles, Botones, Sliders, Layouts.
 
    def setup_ui(self):
        # 1. Splitter Principal (Divide Panel Izquierdo / Panel Derecho)
        self.main_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.setCentralWidget(self.main_splitter)

        # Estilo para los separadores
        self.setStyleSheet("""
            QSplitter::handle {
                background-color: #a0a0a0;
            }
            QSplitter::handle:horizontal {
                width: 4px;  /* Aumentado de 4px a 10px */
            }
            QSplitter::handle:vertical {
                height: 4px; /* Aumentado de 4px a 10px */
            }
            /* Opcional: Un efecto hover para que se ilumine al pasar el mouse */
            QSplitter::handle:hover {
                background-color: #42a5f5; 
            }
        """)

        # --- PANEL IZQUIERDO (Navegación) --- #
        
        self.left_panel = QWidget()
        left_layout = QVBoxLayout(self.left_panel)
        
        # Botones Superiores (Abrir, Opciones, Pomodoro...).
        
        # Fila 1 (Abrir Curso, Abrir Audios y Opciones).
        row1 = QHBoxLayout()
        self.btn_open_course = QPushButton("Abrir Curso...")
        self.btn_open_course.setToolTip("Seleccionar directorio raíz del curso de video. (Alt + C)")
        self.btn_open_course.clicked.connect(self.change_course)
        
        self.btn_open_audio = QPushButton("Abrir Audios...")
        self.btn_open_audio.setToolTip("Seleccionar directorio de grabaciones/audios. (Alt + A)")
        self.btn_open_audio.clicked.connect(self.change_audios)

        self.btn_options = QPushButton("Opciones")
        self.btn_options.setToolTip("Opciones y configuración del reproductor. (Alt + O)")
        self.btn_options.clicked.connect(self.show_options)
        
        row1.addWidget(self.btn_open_course)
        row1.addWidget(self.btn_open_audio)
        row1.addWidget(self.btn_options)
        left_layout.addLayout(row1)

        # Fila 2 Botones (Pomodoro, Tema y Acerca de:)
        row2 = QHBoxLayout()
        self.btn_pomodoro = QPushButton("Pomodoro")
        self.btn_pomodoro.setToolTip("Iniciar temporizador Pomodoro para sesiones de estudio. (Alt + P)")
        self.btn_pomodoro.clicked.connect(self.show_pomodoro)
        self.btn_theme = QPushButton("Tema")
        self.btn_theme.setToolTip("Cambiar entre tema claro y oscuro. (Alt + T)")
        self.btn_theme.clicked.connect(self.toggle_theme)
        self.btn_about = QPushButton("Acerca de")
        self.btn_about.setToolTip("Información sobre esta aplicación. (F1)")
        self.btn_about.clicked.connect(self.show_about)
        row2.addWidget(self.btn_pomodoro)
        row2.addWidget(self.btn_theme)
        row2.addWidget(self.btn_about)
        left_layout.addLayout(row2)
        left_layout.addSpacing(10)

        # Árbol de Contenidos
        left_layout.addWidget(QLabel("<b>Explorador de contenido:</b>"))
        self.tree = QTreeWidget()
        self.tree.setHeaderHidden(True)
        self.tree.itemClicked.connect(self._on_tree_item_clicked)
        
        left_layout.addWidget(self.tree, 1) 
        left_layout.addSpacing(5)

        # Áreas de Archivos y Ejercicios (Scroll Areas).
        
        # Archivos del capítulo.
        left_layout.addWidget(QLabel("<b>Archivos relacionados del Capítulo:</b>"))
        self.scroll_files = QScrollArea()
        self.scroll_files.setWidgetResizable(True)
        self.scroll_files.setMinimumHeight(150)
        self.files_container = QWidget()
        self.files_layout = QVBoxLayout(self.files_container)
        self.files_layout.setContentsMargins(5,5,5,5)
        self.scroll_files.setWidget(self.files_container)
        left_layout.addWidget(self.scroll_files)
        left_layout.addSpacing(5)

        # Ejercicios.
        left_layout.addWidget(QLabel("<b>Ejercicios del Capítulo:</b>"))
        self.scroll_exercises = QScrollArea()
        self.scroll_exercises.setWidgetResizable(True)
        self.scroll_exercises.setFixedHeight(70)
        self.scroll_exercises.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.exercises_container = QWidget()
        self.ex_layout = QVBoxLayout(self.exercises_container)
        self.ex_layout.setContentsMargins(5,5,5,5)
        self.scroll_exercises.setWidget(self.exercises_container)
        left_layout.addWidget(self.scroll_exercises)

        # Información de Pomodoro (Visible solo en ejecución).
        self.lbl_pomodoro_status = QLabel("")
        self.lbl_pomodoro_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_pomodoro_status.setStyleSheet("color: #aa0000; font-weight: bold;")
        left_layout.addWidget(self.lbl_pomodoro_status)
        
        # Footer (Información de Autor y Correo).
        footer_widget = QWidget()
        footer_layout = QVBoxLayout(footer_widget)
        footer_layout.setContentsMargins(0, 10, 0, 0)
        footer_layout.setSpacing(2)
        
        lbl_created = QLabel("Creado por:")
        lbl_created.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_created.setStyleSheet("font-weight: bold;")
        
        lbl_name = QLabel("Jose Luis Montero Laguado")
        lbl_name.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Texto del asunto codificado (los espacios son %20)
        subject = "Muchas%20gracias%20por%20compartir%20el%20Reproductor%20de%20Cursos"
        
        self.lbl_email = EmailLabel(f'<a href="mailto:jlmonterol@outlook.com?subject={subject}">jlmonterol@outlook.com</a>')
        self.lbl_email.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_email.setToolTip("Se abre tu correo… ¡y espero tu mensaje alegre! ;)")
        
        lbl_year = QLabel("2025")
        lbl_year.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_year.setStyleSheet("font-weight: bold;")
        
        footer_layout.addWidget(lbl_created)
        footer_layout.addWidget(lbl_name)
        footer_layout.addWidget(self.lbl_email)
        footer_layout.addWidget(lbl_year)
        
        left_layout.addWidget(footer_widget)

        # --- PANEL DERECHO (Video + Info) --- #

        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0,0,0,0)

        # Header (Imagen del curso, Títulos, Checkbox completado).
        
        self.header_container = QWidget()
        self.header_container.setFixedHeight(100)
        header_layout = QHBoxLayout(self.header_container)
        header_layout.setContentsMargins(10, 0, 10, 0)
        
        # A. Imagen del curso 80x80.
        self.img_course = CourseImageLabel()
        # self.img_course.setToolTip("Doble clic para ver información del curso") OJO al habilitarlo el ToolTip no respeta los colores del tema (Investigar).
        self.img_course.setFixedSize(80, 80)
        self.img_course.setStyleSheet("background-color: #000; border: 1px solid #555;")
        self.img_course.doubleClicked.connect(self.show_course_info)
        header_layout.addWidget(self.img_course)
        
        # B. Resorte.
        header_layout.addStretch()
        
        # C. Títulos.
        titles_layout = QVBoxLayout()
        self.lbl_course_title = QLabel("Curso no seleccionado")
        self.lbl_course_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_chapter_title = QLabel("...")
        self.lbl_chapter_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_media_title = QLabel("Selecciona un vídeo")
        self.lbl_media_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        titles_layout.addWidget(self.lbl_course_title)
        titles_layout.addWidget(self.lbl_chapter_title)
        titles_layout.addWidget(self.lbl_media_title)
        
        header_layout.addLayout(titles_layout)
        
        # D. Resorte.
        header_layout.addStretch()
        
        # E. Checkbox.
        v_chk_wrapper = QVBoxLayout()
        v_chk_wrapper.addStretch()
        
        self.chk_completed = QCheckBox("¿ Completado ?")
        self.chk_completed.setToolTip("Marcar este vídeo/audio como completado. (F5)")
        self.chk_completed.setEnabled(False)
        self.chk_completed.toggled.connect(self._on_completed_toggled)
        self.chk_completed.setLayoutDirection(Qt.LayoutDirection.LeftToRight) 
        
        v_chk_wrapper.addWidget(self.chk_completed)
        v_chk_wrapper.addStretch()

        header_layout.addLayout(v_chk_wrapper)

        right_layout.addWidget(self.header_container)

        # Separador Header.
        self.header_separator = QFrame()
        self.header_separator.setFrameShape(QFrame.Shape.HLine)
        self.header_separator.setFrameShadow(QFrame.Shadow.Sunken)
        self.header_separator.setStyleSheet("color: #555;")
        right_layout.addWidget(self.header_separator)

        # Splitter Vertical Derecho.
        self.right_splitter = QSplitter(Qt.Orientation.Vertical)
        
        # --- ZONA DE VIDEO Y CONTROLES --- #

        video_full_container = QWidget()
        video_full_layout = QVBoxLayout(video_full_container)
        video_full_layout.setContentsMargins(0,0,0,0)
        video_full_layout.setSpacing(0)
        
        # Título sección.
        h_vid_title = QHBoxLayout()
        h_vid_title.setContentsMargins(5, 5, 5, 5)
        h_vid_title.addWidget(QLabel("<b>Reproductor de audio/vídeo</b>"))
        h_vid_title.addStretch()
        video_full_layout.addLayout(h_vid_title)
        
        # Label de cuenta regresiva.
        self.countdownLabel = QLabel("")
        self.countdownLabel.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.countdownLabel.setStyleSheet("""
            background-color: #333; 
            color: #FFD700; /* Dorado brillante */
            font-weight: bold; 
            font-size: 14px; 
            padding: 8px; 
            border-bottom: 2px solid #FFD700;
        """)
        self.countdownLabel.setVisible(False)
        video_full_layout.addWidget(self.countdownLabel)

        # Instancia de VideoWidget (clase personalizada).
        
        self.videoWidget = VideoWidget()
        self.videoWidget.setStyleSheet("background-color: black;")
        self.videoWidget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        # Conexión de clics para pausar/pantalla completa.
        self.videoWidget.clicked.connect(self.player.toggle_play_pause)
        self.videoWidget.doubleClicked.connect(self.toggle_fullscreen)
        video_full_layout.addWidget(self.videoWidget, 1) 
        
        # CONTROLES (Play, Stop, Slider, Volumen).
        
        self.controls_container = QWidget()
        self.controls_container.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum)
        self.controls_container.setMaximumHeight(200)
        
        controls_layout = QVBoxLayout(self.controls_container)
        controls_layout.setContentsMargins(10, 5, 10, 5)
        controls_layout.setSpacing(5)
        
        # Slider.
        self.slider_seek = QSlider(Qt.Orientation.Horizontal)
        self.slider_seek.setRange(0, 1000)
        self.slider_seek.setMinimumHeight(30)
        self.slider_seek.sliderMoved.connect(self._on_slider_moved)
        self.slider_seek.sliderPressed.connect(self._on_slider_pressed)
        self.slider_seek.sliderReleased.connect(self._on_slider_released)
        controls_layout.addWidget(self.slider_seek)
        
        # Grid Inferior.
        lower_controls_layout = QHBoxLayout()
        lower_controls_layout.setContentsMargins(0, 0, 0, 0)
        
        # Izquierda: Tiempo.
        v_time = QVBoxLayout()
        self.lbl_time = QLabel("<b>Duración:</b> 00:00 (x1.0) / 00:00")
        v_time.addWidget(self.lbl_time)
        v_time.addStretch()
        lower_controls_layout.addLayout(v_time)
        
        lower_controls_layout.addStretch()
        
        # Centro: Botones.
        cluster_layout = QVBoxLayout()
        cluster_layout.setSpacing(8)
        
        # Fila 1: Reproducción.
        row_c1_container = QHBoxLayout()
        lbl_rep = QLabel("Reproducción:")
        lbl_rep.setStyleSheet("font-weight: bold;")
        lbl_rep.setFixedWidth(100)
        lbl_rep.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        row_c1_container.addWidget(lbl_rep)
        
        row_c1 = QHBoxLayout()
        row_c1.setSpacing(10)
        self.btn_prev = QPushButton("Anterior pista")
        self.btn_prev.setToolTip("Reproducir el vídeo/audio anterior. (Alt + Flecha Izquierda)")
        self.btn_prev.clicked.connect(self.play_previous)
        self.btn_rewind = QPushButton("<< 5s")
        self.btn_rewind.setToolTip("Retroceder 5 segundos. (Flecha Izquierda)")
        self.btn_rewind.clicked.connect(lambda: self.player.seek_relative(-5000))
        self.btn_play = QPushButton("Reproducir / Pausar")
        self.btn_play.setToolTip("Alternar reproducción/pausa. (Barra espaciadora)")
        self.btn_play.setMinimumWidth(140)
        self.btn_play.clicked.connect(self.player.toggle_play_pause)
        self.btn_stop = QPushButton("Detener")
        self.btn_stop.setToolTip("Detener reproducción.")
        self.btn_stop.clicked.connect(self.player.stop)
        self.btn_forward = QPushButton("5s >>")
        self.btn_forward.setToolTip("Avanzar 5 segundos. (Flecha Derecha)")
        self.btn_forward.clicked.connect(lambda: self.player.seek_relative(5000))
        self.btn_next = QPushButton("Siguiente pista")
        self.btn_next.setToolTip("Reproducir el siguiente vídeo/audio. (Alt + Flecha Derecha)")
        self.btn_next.clicked.connect(self.play_next)
        
        for btn in [self.btn_prev, self.btn_rewind, self.btn_play, self.btn_stop, self.btn_forward, self.btn_next]:
            row_c1.addWidget(btn)
        row_c1_container.addLayout(row_c1)
        cluster_layout.addLayout(row_c1_container)
        
        # Fila 2: Opciones.
        row_c2_container = QHBoxLayout()
        lbl_opt = QLabel("Opciones:")
        lbl_opt.setStyleSheet("font-weight: bold;")
        lbl_opt.setFixedWidth(100)
        lbl_opt.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        row_c2_container.addWidget(lbl_opt)

        row_c2 = QHBoxLayout()
        row_c2.setSpacing(10)
        self.btn_repeat = QPushButton("Repetir indefinidamente")
        self.btn_repeat.setToolTip("Reproduce automáticamente el mismo audio/vídeo al finalizar. (F9)")
        self.btn_repeat.setCheckable(True)
        self.btn_repeat.toggled.connect(self.toggle_repeat)
        self.btn_continuous = QPushButton("Reproducción continua")
        self.btn_continuous.setToolTip("Reproduce automáticamente el siguiente audio/vídeo. (F10)")
        self.btn_continuous.setCheckable(True)
        self.btn_continuous.toggled.connect(self.toggle_continuous)
        self.btn_fullscreen = QPushButton("Pantalla ampliada")
        self.btn_fullscreen.setToolTip("Alterna a pantalla ampliada. Doble clic primario en el video también funciona. (F11)")
        self.btn_fullscreen.setCheckable(True)
        self.btn_fullscreen.clicked.connect(self.toggle_fullscreen)
        
        row_c2.addWidget(self.btn_repeat)
        row_c2.addWidget(self.btn_continuous)
        row_c2.addWidget(self.btn_fullscreen)
        row_c2_container.addLayout(row_c2)
        cluster_layout.addLayout(row_c2_container)
        
        # Fila 3: Velocidad.
        row_c3_container = QHBoxLayout()
        lbl_vel = QLabel("Velocidad:")
        lbl_vel.setStyleSheet("font-weight: bold;")
        lbl_vel.setFixedWidth(100)
        lbl_vel.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        row_c3_container.addWidget(lbl_vel)

        row_c3 = QHBoxLayout()
        row_c3.setSpacing(10)
        btn_slower = QPushButton("Más lento")
        btn_slower.setToolTip("Disminuir velocidad de reproducción en 0.1x. (Ctrl + -)")
        btn_slower.clicked.connect(lambda: self.change_speed(-0.1))
        self.btn_normal_speed = QPushButton("Normal")
        self.btn_normal_speed.setToolTip("Restablecer velocidad de reproducción a 1.0x. (Ctrl + *)")
        self.btn_normal_speed.clicked.connect(lambda: self.change_speed(0, reset=True))
        btn_faster = QPushButton("Más rápido")
        btn_faster.setToolTip("Aumentar velocidad de reproducción en 0.1x. (Ctrl + +)")
        btn_faster.clicked.connect(lambda: self.change_speed(0.1))
        self.lbl_speed = QLabel("x1.0")
        self.lbl_speed.setVisible(False)
        
        row_c3.addWidget(btn_slower)
        row_c3.addWidget(self.btn_normal_speed)
        row_c3.addWidget(btn_faster)
        row_c3_container.addLayout(row_c3)
        cluster_layout.addLayout(row_c3_container)
        
        lower_controls_layout.addLayout(cluster_layout)
        lower_controls_layout.addStretch()
        
        # Derecha: Volumen.
        vol_layout = QVBoxLayout()
        vol_layout.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignTop)
        vol_layout.setContentsMargins(0, 0, 0, 10)
        
        lbl_vol = QLabel("Volumen")
        lbl_vol.setStyleSheet("font-weight: bold;")
        lbl_vol.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.slider_vol = QSlider(Qt.Orientation.Vertical)
        self.slider_vol.setRange(0, 100)
        self.slider_vol.setValue(80)
        self.slider_vol.setMinimumHeight(100)
        self.slider_vol.setToolTip("Ajustar el volumen de reproducción. (Flecha Arriba / Abajo)")
        self.slider_vol.valueChanged.connect(self.player.set_volume)
        
        vol_layout.addWidget(lbl_vol)
        vol_layout.addWidget(self.slider_vol, alignment=Qt.AlignmentFlag.AlignCenter)
        lower_controls_layout.addLayout(vol_layout)
        
        controls_layout.addLayout(lower_controls_layout)
        video_full_layout.addWidget(self.controls_container, 0)

        # DESCRIPCIÓN Y NOTAS.
        
        self.desc_widget = QWidget()
        desc_layout = QVBoxLayout(self.desc_widget)
        desc_layout.addWidget(QLabel("<b>Descripción del audio/vídeo:</b>"))
        self.txt_desc = CustomTextBrowser() # Navegador HTML.
        self.txt_desc.setOpenExternalLinks(True)
        desc_layout.addWidget(self.txt_desc)
        
        self.notes_widget = QWidget()
        notes_layout = QVBoxLayout(self.notes_widget)
        notes_layout.addWidget(QLabel("<b>Apuntes del audio/vídeo:</b>"))
        self.txt_notes = QTextEdit() # Editor de texto plano.
        notes_layout.addWidget(self.txt_notes)
        
        h_notes_btns = QHBoxLayout()
        self.btn_save_notes = QPushButton("Guardar apuntes")
        self.btn_save_notes.setToolTip("Guardar los apuntes realizados para este audio/vídeo. (Alt + S)")
        self.btn_save_notes.clicked.connect(self.save_notes)
        self.btn_save_notes.setEnabled(False)
        self.txt_notes.textChanged.connect(self._on_notes_text_changed)
        
        self.btn_export_notes = QPushButton("Exportar apuntes")
        self.btn_export_notes.setToolTip("Realiza uno de los tres tipos de exportación a un archivo CSV. (Alt + E)")
        self.btn_export_notes.clicked.connect(self.show_export_dialog)
        h_notes_btns.addWidget(self.btn_save_notes)
        h_notes_btns.addWidget(self.btn_export_notes)
        notes_layout.addLayout(h_notes_btns)

        # Agregar todo al Splitter Derecho.
        self.right_splitter.addWidget(video_full_container) # Video + Controles.
        self.right_splitter.addWidget(self.desc_widget) # Descripción.
        self.right_splitter.addWidget(self.notes_widget) # Notas.
        self.right_splitter.setStretchFactor(0, 10) 
        self.right_splitter.setStretchFactor(1, 1)
        self.right_splitter.setStretchFactor(2, 1)

        right_layout.addWidget(self.right_splitter)
        
        # Agregar paneles al Splitter Principal
        self.main_splitter.addWidget(self.left_panel)
        self.main_splitter.addWidget(right_widget)
        self.main_splitter.setSizes([400, 800])
        
        # Filtros de eventos
        self.videoWidget.installEventFilter(self)
        self.tree.viewport().installEventFilter(self)
        self.installEventFilter(self)
                
        self.slider_pressed = False
        
        # Inicialización de iconos y estilos
        self._update_icons()
        self._apply_title_styles()
        self._apply_slider_style()

    # =================================================
    # RESTAURAR ESTADO UI (_RESTORE_UI_STATE)
    # =================================================

    # Restaura el tamaño de ventana y posición de los paneles guardados.

    def _restore_ui_state(self):
        # 1. Restaurar Geometría de Ventana
        geo_hex = self.data_manager.get_window_geometry()
        if geo_hex:
            geo_bytes = QByteArray.fromHex(geo_hex.encode('utf-8'))
            self.restoreGeometry(geo_bytes)
            
        # 2. Restaurar Splitters
        main_hex = self.data_manager.get_splitter_state("main_splitter")
        if main_hex:
            self.main_splitter.restoreState(QByteArray.fromHex(main_hex.encode('utf-8')))
            
        right_hex = self.data_manager.get_splitter_state("right_splitter")
        if right_hex:
            self.right_splitter.restoreState(QByteArray.fromHex(right_hex.encode('utf-8')))
    
    # =================================================
    #   APLICAMOS ESTILOS A LOS TITULOS
    # =================================================

    # Pinta el slider de progreso con CSS según el tema (Azul/Gris en Dark mode, etc.).

    def _apply_title_styles(self):
        color = "#ffffff" if self.dark_mode else "#000000"
        
        # Usamos tu nueva lógica de estilos
        self.lbl_course_title.setStyleSheet(f"font-size: 21px; font-weight: bold; color: {color};")
        self.lbl_chapter_title.setStyleSheet(f"font-size: 18px; font-weight: bold; color: {color};")
        self.lbl_media_title.setStyleSheet(f"font-size: 16px; color: {color};")

    # =================================================
    # ESTILOS VISUALES (_APPLY_SLIDER_STYLE / TITLE)
    # =================================================
    
    # Aplica hojas de estilo CSS (QSS) complejas para personalizar la apariencia de los sliders (barras de desplazamiento) según el tema.

    def _apply_slider_style(self):
        
        # Colores comunes
        GROOVE_HEIGHT = "10px"
        HANDLE_SIZE = "24px"
        HANDLE_RADIUS = "4px"
        BLUE_ACCENT = "#3a8ee6"

        if self.dark_mode:
            css = f"""
                QSlider::groove:horizontal {{
                    border: 1px solid #3a3a3a;
                    background: #2b2b2b;
                    height: {GROOVE_HEIGHT};
                    border-radius: 4px;
                }}
                QSlider::sub-page:horizontal {{
                    background: {BLUE_ACCENT};
                    border: 1px solid {BLUE_ACCENT};
                    height: {GROOVE_HEIGHT};
                    border-radius: 4px;
                }}
                QSlider::add-page:horizontal {{
                    background: #2b2b2b;
                    border: 1px solid #3a3a3a;
                    height: {GROOVE_HEIGHT};
                    border-radius: 4px;
                }}
                QSlider::handle:horizontal {{
                    background: #505050;
                    border: 1px solid #6c6c6c;
                    width: {HANDLE_SIZE};
                    height: {HANDLE_SIZE};
                    margin: -7px 0;
                    border-radius: {HANDLE_RADIUS};
                }}
                QSlider::handle:horizontal:hover {{
                    background: #606060;
                }}
            """
        else:
            css = f"""
                QSlider::groove:horizontal {{
                    border: 1px solid #c0c0c0;
                    background: #e0e0e0;
                    height: {GROOVE_HEIGHT};
                    border-radius: 4px;
                }}
                QSlider::sub-page:horizontal {{
                    background: {BLUE_ACCENT};
                    border: 1px solid {BLUE_ACCENT};
                    height: {GROOVE_HEIGHT};
                    border-radius: 4px;
                }}
                QSlider::add-page:horizontal {{
                    background: #e0e0e0;
                    border: 1px solid #c0c0c0;
                    height: {GROOVE_HEIGHT};
                    border-radius: 4px;
                }}
                QSlider::handle:horizontal {{
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #f6f6f6, stop:1 #dadada);
                    border: 1px solid #888;
                    width: {HANDLE_SIZE};
                    height: {HANDLE_SIZE};
                    margin: -7px 0;
                    border-radius: {HANDLE_RADIUS};
                }}
                QSlider::handle:horizontal:hover {{
                    background: #ffffff;
                }}
            """
        
        self.slider_seek.setStyleSheet(css)

    # =================================================
    # SLOTS DEL REPRODUCTOR (_ON_PLAYER_...)
    # =================================================
    
    # Estos métodos reciben las señales del PlayerController y actualizan la UI.
    
    # Actualiza el label de tiempo (00:00 / 10:00).
    def _on_player_time_changed(self, current_ms, total_ms):
        from app.utils.helpers import format_ms_to_time, format_playback_rate
        
        if total_ms > 0:
            current_str = format_ms_to_time(current_ms)
            total_str = format_ms_to_time(total_ms)
            rate_str = format_playback_rate(self.player.get_rate())
            
            text = f"<b>Duración:</b> {current_str} ({rate_str}) / {total_str}"
            self.lbl_time.setText(text)

    # Mueve el slider de progreso automáticamente.
    def _on_player_position_changed(self, position):
        # Solo actualiza si el usuario NO está arrastrando el slider manualmente.
        if not self.slider_pressed:
            self.slider_seek.setValue(int(position * 1000))

    def _on_player_state_changed(self, is_playing):
        self.btn_play.setText("Pausa" if is_playing else "Reproducir")

    # Lógica a ejecutar cuando termina un video.
    def _on_player_finished(self):
        
        # 1. Modo Repetir.
        if getattr(self, 'repeat_enabled', False):
            self.player.stop()
            self.player.play()
            return

        # 2. Modo Continuo CON Countdown.
        if getattr(self, 'continuous_enabled', False):
            # Buscar siguiente.
            next_item = self._find_next_item_candidate()
            
            if next_item:
                self.next_item_candidate = next_item
                self.countdown_remaining = 5
                
                # Configurar Label.
                self.countdownLabel.setText(
                    f"Reproducción continua: siguiente vídeo/audio en {self.countdown_remaining} segundos..."
                )
                self.countdownLabel.setVisible(True)
                
                # Iniciar Timer.
                self.countdownTimer.start()
            return

        # 3. Comportamiento normal (sin continuo activado).

        # self.play_next() # Descomentar si quieres autoplay por defecto sin espera.

    def _on_slider_pressed(self):
        self.slider_pressed = True

    def _on_slider_released(self):
        self.slider_pressed = False
        val = self.slider_seek.value()
        self.player.set_position(val / 1000.0)

    def _on_slider_moved(self, val):
        if self.slider_pressed:
            pass

    # =================================================
    #   INICIALIZACIÓN DEL CURSO
    # =================================================

    # Método de arranque. Recibe la ruta, detecta si es video o audio, guarda la ruta en historial y construye el árbol. Método llamado desde main.py al iniciar la app.

    def set_course_path_init(self, path):
        self.course_path = path
        self.lbl_course_title.setText(os.path.basename(path))
        
        # Guardamos la ruta inmediatamente al iniciar.
        self.data_manager.set_last_open_dir(path)
        
        # LÓGICA INTELIGENTE DE INICIO
        
        if self._directory_has_videos(path):
            # Es un curso de video normal.
            self._build_tree(path) 
            self.lbl_chapter_title.setText("...")
            self.lbl_media_title.setText("Selecciona un vídeo")
        else:
            # Es una carpeta de audios.
            self._build_audio_tree(path) 
            self.lbl_chapter_title.setText("...")
            self.lbl_media_title.setText("Selecciona un audio")
            
            # Ajustar interfaz a modo audio.
            self.is_audio_mode = True
            self.show_audio_overlay(True)
            
        self._load_course_image(path)

    # =============================================================
    # DETECCION DE CONTENIDO (_DIRECTORY_HAS_VIDEOS)
    # =============================================================

    # Recorre superficialmente (o un poco profundo) para ver si hay videos. Si encuentra .mp4, .mkv, etc., devuelve True.

    def _directory_has_videos(self, root_path: str) -> bool:
        # Miramos hasta 3 niveles de profundidad para ser eficientes.
        depth_limit = 3
        current_depth = 0
        
        for dirpath, dirnames, filenames in os.walk(root_path):
            # Chequear archivos en este nivel.
            for f in filenames:
                if f.lower().endswith(VIDEO_EXTS):
                    return True
            
            # Control de profundidad manual.
            current_depth += 1
            if current_depth >= depth_limit:
                break
                
        return False

    # =============================================================
    #   GESTIÓN DEL ÁRBOL Y ARCHIVOS
    # =============================================================

    # Método de arranque. Recibe la ruta, detecta si es video o audio, guarda la ruta en historial y construye el árbol.

    def change_course(self):
        # Recuperar última ruta
        last_dir = self.data_manager.get_last_open_dir()
        path = QFileDialog.getExistingDirectory(self, "Seleccionar Curso", last_dir)
        
        if path:
            self.course_path = path
            # Guardar nueva ruta
            self.data_manager.set_last_open_dir(path)
            
            self.lbl_course_title.setText(os.path.basename(path))
            self._build_tree(path)
            self._load_course_image(path)
            
            # Reset UI
            self.txt_desc.clear()
            self.txt_notes.clear()
            self.player.stop()

    # Recorre carpetas y archivos recursivamente para llenar el árbol de navegación lateral.

    def _build_tree(self, root_path):
        # Delegamos TODO al manager
        self.tree_manager.set_course_path(root_path)
        self.tree_manager.build_video_tree(root_path)

    # Maneja el clic en el árbol. Si es video/audio, lo carga; si es test, abre el diálogo de evaluación.

    def _on_tree_item_clicked(self, item, col):
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if not data:
            return
        
        item_type = data.get("type")
        
        # Aceptar cualquier tipo de medio.
        if item_type in ["media", "video", "audio"]:
            self.load_media(data)
            
        elif item_type == "test":
            self.open_test(data)

    # Marca/desmarca un ítem como "Visto" (verde) y guarda el estado en la base de datos.

    def _toggle_item_completion(self, item):
        info = item.data(0, Qt.ItemDataRole.UserRole)
        if not info:
            return
            
        # Verificar que sea un tipo válido (video o audio) OJO Usamos get() para evitar errores si la clave no existe.
        item_type = info.get("type")
        if item_type in ("media", "video", "audio"):
            
            # Recuperar ruta de forma segura.
            full_path = (info.get("path") or 
                         info.get("audio_path") or 
                         info.get("video_path"))
                         
            if not full_path: return

            # Validación segura de ruta.
            try:
                rel_path = os.path.relpath(full_path, self.course_path)
            except ValueError:
                rel_path = full_path
            
            # 1. Invertir estado en la base de datos.
            current_state = self.data_manager.is_video_completed(self.course_path, rel_path)
            new_state = not current_state
            self.data_manager.set_video_completed(self.course_path, rel_path, new_state)
            
            # 2. Pintar de verde/blanco inmediatamente.
            self._update_item_color(item)
            
            # 3. Si justo es el archivo que estoy reproduciendo, mover el checkbox también.
            if self.current_media_info:
                curr_path = (self.current_media_info.get("path") or 
                             self.current_media_info.get("audio_path") or 
                             self.current_media_info.get("video_path"))
                
                if curr_path == full_path:
                    self.chk_completed.blockSignals(True)
                    self.chk_completed.setChecked(new_state)
                    self.chk_completed.blockSignals(False)

    # Elimina la numeración 'XX - ' del inicio si existe.

    def _clean_title_text(self, text):
        parts = text.split(" - ", 1)
        if len(parts) > 1 and parts[0].strip().isdigit():
            return parts[1].strip()
        return text
    
    # =================================================
    # CARGA DE MEDIOS (LOAD_MEDIA)
    # =================================================
    
    # Es el método clave que orquesta la reproducción de un archivo.

    def load_media(self, info):
        self._cancel_countdown()
        self.current_media_info = info
        
        # 1. Recuperar ruta de forma segura.
        raw_path = info.get("path") or info.get("audio_path") or info.get("video_path")
        
        if not raw_path or not os.path.exists(raw_path):
            print(f"Error: Archivo no encontrado: {raw_path}")
            return

        file_path = os.path.normpath(raw_path)
        
        # 2. Cargar y reproducir.
        self.player.load_media(file_path)
        self.player.play()
        
        # 3. Lógica de Títulos (USANDO HELPERS).
        course_name = os.path.basename(self.course_path)
        self.lbl_course_title.setText(f">>>  > {course_name} <  <<<")

        if info.get("type") == "audio":
            raw_chapter = info.get("chapter_title", "...")
            self.lbl_chapter_title.setText(f"* {raw_chapter} *")
            
            filename = os.path.basename(file_path)
            self.lbl_media_title.setText(format_date_name(filename, include_index=False))
            
            self.is_audio_mode = True
            self.videoWidget.set_audio_mode(True)
            
        else:
            chapter_dir_name = os.path.basename(info.get("parent_dir", ""))
            
            # Usamos clean_title_text para quitar "01 - ".
            clean_chapter = clean_title_text(chapter_dir_name)
            self.lbl_chapter_title.setText(f"* {clean_chapter} *")
            
            video_filename = os.path.splitext(os.path.basename(file_path))[0]
            clean_video = clean_title_text(video_filename)
            self.lbl_media_title.setText(clean_video)
            
            self.is_audio_mode = False
            self.videoWidget.set_audio_mode(False)

        # Aplicar estilos CSS a los títulos.
        self._apply_title_styles()

        # 4. Gestión de Estado (Checkbox y Notas).
        rel_path = os.path.relpath(file_path, self.course_path)
        is_done = self.data_manager.is_video_completed(self.course_path, rel_path)
        
        self.chk_completed.blockSignals(True)
        self.chk_completed.setEnabled(True)
        self.chk_completed.setChecked(is_done)
        self.chk_completed.blockSignals(False)
        
        notes = self.data_manager.get_notes(self.course_path, rel_path)
        self.txt_notes.setText(notes)
        self.btn_save_notes.setEnabled(False)
        
        # 5. Carga de Descripción (USANDO HELPER HTML).
        base_path = os.path.splitext(file_path)[0]
        desc_text = "Sin descripción."
        
        if os.path.exists(base_path + ".md"):
            with open(base_path + ".md", "r", encoding="utf-8") as f: desc_text = f.read()
        elif os.path.exists(base_path + ".txt"):
            with open(base_path + ".txt", "r", encoding="utf-8") as f: desc_text = f.read()
        
        # Aquí usamos el helper nuevo que escapa HTML y crea enlaces.
        link_color = "#66ccff" if self.dark_mode else "#0000ff"
        final_html = text_to_html_link(desc_text, link_color)
        
        self.txt_desc.setHtml(final_html)

        # 6. Cargar Archivos Relacionados (Ejercicios).
        parent_dir = info.get("parent_dir") or info.get("chapter_dir")
        if parent_dir:
            self._load_related_files(parent_dir)

    def _update_item_color(self, item):
        self.tree_manager.update_item_color(item)

    def _on_completed_toggled(self, checked):
        if not self.current_media_info: return
        
        # Recuperar path seguro.
        path = (self.current_media_info.get("path") or 
                self.current_media_info.get("audio_path") or 
                self.current_media_info.get("video_path"))
        
        if not path: return

        try:
            rel_path = os.path.relpath(path, self.course_path)
        except ValueError:
            # Si están en discos diferentes, usamos el path absoluto.
            rel_path = path

        # Guardar.
        rel_path = os.path.relpath(path, self.course_path)
        self.data_manager.set_video_completed(self.course_path, rel_path, checked)
        
        # Actualizar color en el árbol
        current_item = self.tree.currentItem()
        if current_item:
            self._update_item_color(current_item)

    # =================================================
    # GESTIÓN DE APUNTES (SAVE_NOTES)
    # =================================================

    # Guarda el texto escrito en el panel de apuntes en la base de datos.

    def save_notes(self):
        if not self.current_media_info: return
        
        # 1. Recuperación robusta del path (Audio o Video).
        path = (self.current_media_info.get("path") or 
                self.current_media_info.get("audio_path") or 
                self.current_media_info.get("video_path"))
                
        if not path: 
            return

        rel_path = os.path.relpath(path, self.course_path)
        text = self.txt_notes.toPlainText()
        
        self.data_manager.set_notes(self.course_path, rel_path, text)
        
        # Desactivar botón y notificar
        self.btn_save_notes.setEnabled(False)
        self._show_custom_info("Guardado", "Los apuntes se han guardado correctamente.")

    # =================================================
    #   FUNCIONALIDADES EXTRA
    # =================================================
    
    def open_test(self, info):
        # 1. Pregunta de confirmación (Restaurada)
        test_name = os.path.splitext(os.path.basename(info["path"]))[0]
        
        if not self._show_custom_confirmation("Confirmar evaluación", f"¿Estás seguro de presentar la evaluación: '{test_name}'?"):
            return

        # 2. Carga y ejecución
        test_data = CourseScanner.load_test_file(info["path"])
        if not test_data:
            QMessageBox.critical(self, "Error", "El archivo de test es inválido o está vacío.")
            return
            
        dlg = TestEvaluationDialog(self, test_data, self.data_manager, 
                                   self.course_path, test_name, 
                                   self.dark_mode)
        dlg.exec()

    # =================================================
    # POMODORO (INTEGRACIÓN)
    # =================================================

    # Abre el diálogo del temporizador Pomodoro.

    # Muestra el diálogo de configuración. Si ya corre, pausa/reanuda.
    def show_pomodoro(self):
        # Abrir diálogo pasando el estado actual.
        dlg = PomodoroDialog(self, self.dark_mode, is_running=self.is_pomodoro_active)
        
        code = dlg.exec()
        
        # 1. Si el usuario pidió DETENER desde el diálogo.
        if dlg.stop_requested:
            self._stop_pomodoro_and_notify()
            return

        # 2. Si el usuario dio ACEPTAR / INICIAR / PAUSAR.
        if code == QDialog.DialogCode.Accepted and dlg.result_data:
            
            if self.is_pomodoro_active:
                # Si YA está activo, el botón del diálogo actuó como "Pausar/Reanudar".
                self.pomodoro_logic.toggle()
            else:
                # Si NO estaba activo, iniciamos una nueva secuencia con los datos del diálogo.
                data = dlg.result_data
                self.pomodoro_pause_video = data["pause_video"]
                
                self.pomodoro_logic.start_sequence(
                    data["study"], 
                    data["short"], 
                    data["cycles"], 
                    data["long"]
                )
                self.is_pomodoro_active = True
                
                # Feedback inicial inmediato.
                self.lbl_pomodoro_status.setText("¡Pomodoro Iniciado!")
                self._current_pomodoro_color = "#aa0000" # Inicializar color
                self.lbl_pomodoro_status.setStyleSheet("color: #aa0000; font-weight: bold; font-size: 11pt;")

    # Actualiza el label y guarda el color actual para el parpadeo.
    def _on_pomodoro_tick(self, text, color):
        # Guardamos el color actual en una variable de clase
        self._current_pomodoro_color = color 
        
        self.lbl_pomodoro_status.setText(text)
        self.lbl_pomodoro_status.setStyleSheet(f"color: {color}; font-weight: bold; font-size: 11pt;")

    # =================================================
    # POMODORO (FINALIZACIÓN DE CICLOS)
    # =================================================

    # Lógica al terminar una fase (Trabajo/Descanso).
    
    def _on_pomodoro_phase(self, phase_name, is_work_finished):
        
        # Pausar video si corresponde.
        if is_work_finished and self.pomodoro_pause_video:
            if self.player.is_playing():
                self.player.pause()
        
        # Reproducir sonido Bip.
        try:
            sound_path = resource_path(os.path.join("assets", "audio", "Bip_pomodoro.wav"))
            if os.path.exists(sound_path):
                # Usamos una instancia VLC temporal para el bip :D
                import vlc
                vlc.Instance().media_new(sound_path).player_new_from_media().play()
        except:
            pass

        # Mostrar mensaje (No bloqueante idealmente, o QDialog simple).
        msg = "¡Tiempo de estudio terminado!\nToma un descanso." if is_work_finished else "¡Descanso terminado!\n A estudiar."
        self._show_custom_info("Pomodoro", f"{phase_name}\n\n{msg}")

    def _on_pomodoro_finished(self):
        self.is_pomodoro_active = False
        self.lbl_pomodoro_status.setText("¡Sesión completada!")
        self.lbl_pomodoro_status.setStyleSheet("color: #0000aa; font-weight: bold; font-size: 11pt;") # Azul final
        self._show_custom_info("Felicidades", "Has completado todos los ciclos del Pomodoro.")

    def _on_pomodoro_stopped(self):
        self.is_pomodoro_active = False
        self.lbl_pomodoro_status.setText("")

    # --- NUEVOS MÉTODOS PARA PARPADEO Y PAUSA --- #

    # Reacciona al cambio de estado Pausa/Reanudar.

    def _on_pomodoro_paused_status(self, is_paused):
        if is_paused:
            # Iniciar parpadeo.
            self.blink_timer.start()
            self.lbl_pomodoro_status.setText(self.lbl_pomodoro_status.text() + " (PAUSADO)")
        else:
            # Detener parpadeo y restaurar visibilidad.
            self.blink_timer.stop()
            # El texto se actualizará solo con el siguiente tick o resume().
            self.lbl_pomodoro_status.setVisible(True)
    
    # Alterna el color del texto entre transparente y el color original.

    def _blink_pomodoro_label(self):
        self.blink_label_visible = not self.blink_label_visible
        
        # Recuperamos el último color conocido o usamos uno por defecto (Rojo).
        color = getattr(self, '_current_pomodoro_color', '#aa0000')
        
        if self.blink_label_visible:
            # TEXTO VISIBLE: Restauramos el color y estilo.
            self.lbl_pomodoro_status.setStyleSheet(f"color: {color}; font-weight: bold; font-size: 11pt;")
        else:
            # TEXTO INVISIBLE (Pero ocupa espacio): Color transparente.
            self.lbl_pomodoro_status.setStyleSheet("color: transparent; font-weight: bold; font-size: 11pt;")

    def _on_pomodoro_stopped(self):
        self.is_pomodoro_active = False
        self.blink_timer.stop()
        self.lbl_pomodoro_status.setVisible(True)
        self.lbl_pomodoro_status.setText("")
    
    # Lógica F3: - Si NO está activo -> Inicia (Start) - Si está activo y corriendo -> Pausa - Si está activo y pausado -> Reanuda.
    def _toggle_pomodoro_f3(self):

        if not self.is_pomodoro_active:
            self.pomodoro_logic.start_sequence(study=25, short_brk=5, cycles=4, long_brk=30)
            self.is_pomodoro_active = True
            self.lbl_pomodoro_status.setText("¡Pomodoro Iniciado!")
            self.lbl_pomodoro_status.setStyleSheet("color: #00aa00; font-weight: bold;")
        else:
            # Alternar Pausa/Resume.
            self.pomodoro_logic.toggle()

    # Función para el F4 (Detener + Mensaje).
    
    def _stop_pomodoro_and_notify(self):
        if self.is_pomodoro_active:
            self.pomodoro_logic.stop()
            self._show_custom_info("Pomodoro", "El temporizador se ha detenido.")

    # =================================================
    #   ACTUALIZACIÓN DE ICONOS DE BOTONES 
    # =================================================

    # Asigna los iconos correctos (blancos o negros) a todos los botones según el tema actual.

    def _update_icons(self):
        suffix = "_dark.svg" if self.dark_mode else "_light.svg"
        base_path = resource_path(os.path.join("assets", "images"))
        
        # Mapeo: {Objeto_Boton: "nombre_archivo_sin_sufijo"}
        icon_map = {
            # Panel Izquierdo
            self.btn_open_course: "folder",
            self.btn_open_audio: "music",
            self.btn_options: "settings",
            self.btn_pomodoro: "clock",
            self.btn_theme: "theme",
            self.btn_about: "info",
            
            # Reproductor
            self.btn_prev: "previous",
            self.btn_rewind: "rewind",
            self.btn_play: "play_pause",
            self.btn_stop: "stop",
            self.btn_forward: "fast_forward",
            self.btn_next: "next",
            self.btn_repeat: "repeat",
            self.btn_continuous: "forward",
            self.btn_fullscreen: "monitor",
            
            # Notas
            self.btn_save_notes: "save",
            self.btn_export_notes: "export"
        }

        for btn, name in icon_map.items():
            full_path = os.path.join(base_path, f"{name}{suffix}")
            if os.path.exists(full_path):
                btn.setIcon(QIcon(full_path))
                btn.setIconSize(QSize(18, 18)) # Tamaño consistente

    # Cambia entre modo Claro y Oscuro, recargando estilos e iconos.

    def toggle_theme(self):
        self.dark_mode = not self.dark_mode
        self.data_manager.set_theme("dark" if self.dark_mode else "light")
        
        if self.dark_mode:
            self.apply_dark_theme()
        else:
            self.apply_light_theme()
            
        self._update_icons()
        self._apply_title_styles()
        self._apply_slider_style()
        
        # Forzar color inicial del tiempo
        time_color = "#dddddd" if self.dark_mode else "#333333"
        self.lbl_time.setStyleSheet(f"color: {time_color};")

        # Actualizar colores de items completados (Verde/Blanco)
        iterator = QTreeWidgetItemIterator(self.tree)
        
        # --- Refrescar iconos de TEST ---
        suffix = "_dark.svg" if self.dark_mode else "_light.svg"
        test_icon_path = resource_path(os.path.join("assets", "images", f"test{suffix}"))
        new_test_icon = QIcon(test_icon_path) if os.path.exists(test_icon_path) else QIcon()

        # Actualizar iconos y colores del árbol via manager
        self.tree_manager.update_theme(self.dark_mode)

        while iterator.value():
            item = iterator.value()
            self._update_item_color(item) # Tu lógica existente de colores
            
            # Lógica nueva para iconos
            data = item.data(0, Qt.ItemDataRole.UserRole)
            if data and data.get("type") == "test":
                item.setIcon(0, new_test_icon)
                
            iterator += 1

    def apply_dark_theme(self):
        # ... (Tu configuración de paleta igual que antes) ...
        QApplication.setStyle("Fusion")
        palette = QPalette()
        palette.setColor(QPalette.ColorRole.Window, QColor(53, 53, 53))
        palette.setColor(QPalette.ColorRole.WindowText, Qt.GlobalColor.white)
        palette.setColor(QPalette.ColorRole.Base, QColor(25, 25, 25))
        palette.setColor(QPalette.ColorRole.AlternateBase, QColor(53, 53, 53))
        palette.setColor(QPalette.ColorRole.ToolTipBase, Qt.GlobalColor.black)
        palette.setColor(QPalette.ColorRole.ToolTipText, Qt.GlobalColor.white)
        palette.setColor(QPalette.ColorRole.Text, Qt.GlobalColor.white)
        palette.setColor(QPalette.ColorRole.Button, QColor(53, 53, 53))
        palette.setColor(QPalette.ColorRole.ButtonText, Qt.GlobalColor.white)
        palette.setColor(QPalette.ColorRole.BrightText, Qt.GlobalColor.red)
        palette.setColor(QPalette.ColorRole.Link, QColor(42, 130, 218))
        palette.setColor(QPalette.ColorRole.Highlight, QColor(42, 130, 218))
        palette.setColor(QPalette.ColorRole.HighlightedText, Qt.GlobalColor.black)
        QApplication.setPalette(palette)
        
        self.setStyleSheet("""
            QToolTip { color: #ffffff; background-color: #2a82da; border: 1px solid white; }
            QTreeWidget { background-color: #252525; color: white; }
            QTextEdit, QTextBrowser { background-color: #303030; color: white; }
            
            /* --- ESTRATEGIA DE BORDES (DARK) --- */
            
            /* Base transparente: Hace que el área de agarre sea invisible */
            QSplitter::handle { 
                background: transparent; 
            }

            /* 1. BARRA VERTICAL (Izquierda vs Derecha) */
            QSplitter::handle:horizontal {
                width: 9px;                      /* Área total para agarrar */
                border-left: 2px solid #505050;  /* LÍNEA FINA VISIBLE A LA IZQUIERDA */
                border-right: 0px;               /* Resto transparente */
            }

            /* 2. BARRA HORIZONTAL (Video vs Notas) */
            QSplitter::handle:vertical {
                height: 9px;                     /* Área total para agarrar */
                border-top: 2px solid #505050;   /* LÍNEA FINA VISIBLE ARRIBA */
                border-bottom: 0px;              /* Resto transparente */
            }

            /* Efecto Hover: Cambiamos el color del BORDE, no del fondo */
            QSplitter::handle:hover { 
                border-color: #42a5f5; 
            }
        """)

    def apply_light_theme(self):
        QApplication.setStyle("Fusion")
        QApplication.setPalette(QApplication.style().standardPalette())
        
        self.setStyleSheet("""
            /* --- ESTRATEGIA DE BORDES (LIGHT) --- */
            
            QSplitter::handle { 
                background: transparent; 
            }

            /* 1. BARRA VERTICAL */
            QSplitter::handle:horizontal {
                width: 9px;
                border-left: 2px solid #c0c0c0;  /* Línea gris clara */
                border-right: 0px;
            }

            /* 2. BARRA HORIZONTAL */
            QSplitter::handle:vertical {
                height: 9px;
                border-top: 2px solid #c0c0c0;   /* Línea gris clara */
                border-bottom: 0px;
            }

            QSplitter::handle:hover { 
                border-color: #42a5f5; 
            }
        """)

    # =================================================
    # PANTALLA COMPLETA (TOGGLE_FULLSCREEN)
    # =================================================

    # Oculta los paneles laterales e inferiores para dejar solo el video en pantalla completa.

    def toggle_fullscreen(self):
        if not self.is_video_fullscreen:
            # Ocultamos paneles
            self.left_panel.hide()
            self.desc_widget.hide()
            self.notes_widget.hide()
            # OJO no ocultamos self.header_container para que se vea el título.
            
            self.showFullScreen()
            self.is_video_fullscreen = True
            self.btn_fullscreen.setChecked(True)
        else:
            # Restauramos.
            self.left_panel.show()
            self.header_container.show()
            self.desc_widget.show()
            self.notes_widget.show()
            
            self.showNormal()
            self.is_video_fullscreen = False
            self.btn_fullscreen.setChecked(False)

    # =================================================
    # REPRODUCIR LA SIGUIENTE PISTA (AUDIO/VÍDEO)
    # =================================================

    # Lógica para encontrar y reproducir el siguiente archivo en la lista del árbol.

    def play_next(self):
        self._cancel_countdown()
        if not self.current_media_info:
            return

        # 1. Obtener la ruta actual de forma segura (soporta audio, video o genérico).
        current_full_path = (self.current_media_info.get("path") or 
                             self.current_media_info.get("audio_path") or 
                             self.current_media_info.get("video_path"))

        iterator = QTreeWidgetItemIterator(self.tree)
        current_found = False
        
        while iterator.value():
            item = iterator.value()
            data = item.data(0, Qt.ItemDataRole.UserRole)
            
            if not data:
                iterator += 1
                continue

            # Obtener ruta del ítem que estamos revisando.
            item_path = data.get("path") or data.get("audio_path") or data.get("video_path")
            item_type = data.get("type")

            # A. Buscar dónde estamos parados.
            if not current_found:
                # Comparamos rutas para saber si este es el item actual.
                if item_path and item_path == current_full_path:
                    current_found = True
            
            # B. Si ya encontramos el actual, buscamos el SIGUIENTE compatible.
            elif current_found:
                if item_type in ["media", "video", "audio"]:
                    # ¡Encontrado! Seleccionar y reproducir
                    self.tree.setCurrentItem(item)
                    self.load_media(data)
                    return
            
            iterator += 1

    # =================================================
    # REPRODUCIR LA ANTERIOR PISTA (AUDIO/VÍDEO)
    # =================================================

    # Lógica para encontrar y reproducir el anterior archivo en la lista del árbol.

    def play_previous(self):
        self._cancel_countdown()
        if not self.current_media_info:
            return

        current_full_path = (self.current_media_info.get("path") or 
                             self.current_media_info.get("audio_path") or 
                             self.current_media_info.get("video_path"))

        iterator = QTreeWidgetItemIterator(self.tree)
        prev_media_item = None
        prev_media_data = None
        
        while iterator.value():
            item = iterator.value()
            data = item.data(0, Qt.ItemDataRole.UserRole)
            
            if not data:
                iterator += 1
                continue

            item_path = data.get("path") or data.get("audio_path") or data.get("video_path")
            item_type = data.get("type")

            # Si llegamos al actual...
            if item_path and item_path == current_full_path:
                # ...reproducimos el que teníamos guardado como "previo" (si existe).
                if prev_media_data:
                    self.tree.setCurrentItem(prev_media_item)
                    self.load_media(prev_media_data)
                return
            
            # Si no es el actual, pero es un medio válido, lo guardamos como candidato "previo".
            if item_type in ["media", "video", "audio"]:
                prev_media_item = item
                prev_media_data = data
            
            iterator += 1

    def show_about(self):
        AboutDialog(self, self.dark_mode).exec()
        
    def show_options(self):
        OptionsDialog(self, self.data_manager).exec()

    # ================================================================
    # CARGUE DE LA IMAGEN DEL CURSO ESQUINA SUPERIOR IZQUIERDA 80x80
    # ================================================================

    # Busca una imagen (png/jpg) en la raíz del curso de forma robusta, prioriza archivos que contengan 'imagencurso' en el nombre.

    def _load_course_image(self, path):
        self.img_course.clear()
        self.img_course.setText("Sin img")
        
        # Extensiones válidas (minúsculas)
        valid_exts = [".png", ".jpg", ".jpeg"]
        
        try:
            # Listar archivos y filtrar solo imágenes.
            files = os.listdir(path)
            image_files = [f for f in files if os.path.splitext(f)[1].lower() in valid_exts]
            
            if not image_files:
                return

            target_image = None
            
            # 1. Prioridad: Buscar coincidencia con "imagencurso" (insensible a mayúsculas).
            for f in image_files:
                if "imagencurso" in f.lower():
                    target_image = f
                    break
            
            # 2. Respaldo: Si no hay "imagencurso", usar la primera imagen encontrada.
            if not target_image:
                # Ordenamos alfabéticamente para tener consistencia.
                image_files.sort()
                target_image = image_files[0]
            
            # Construir ruta absoluta y NORMALIZADA (importante para Windows).
            full_path = os.path.normpath(os.path.join(path, target_image))
            
            # Cargar imagen.
            pixmap = QPixmap(full_path)
            
            if not pixmap.isNull():
                # Escalar manteniendo aspecto.
                scaled = pixmap.scaled(80, 80, Qt.AspectRatioMode.KeepAspectRatio, 
                                     Qt.TransformationMode.SmoothTransformation)
                self.img_course.setPixmap(scaled)
            else:
                print(f"Advertencia: Se encontró {target_image} pero no se pudo cargar (¿archivo corrupto?).")
                
        except Exception as e:
            print(f"Error crítico cargando imagen: {e}")

    # --- LÓGICA DE BOTONES --- #
    
    def toggle_repeat(self, checked):
        self.repeat_enabled = checked

    def toggle_continuous(self, checked):
        self.continuous_enabled = checked

    def change_speed(self, delta, reset=False):
        if reset:
            new_rate = 1.0
        else:
            new_rate = round(self.player.get_rate() + delta, 1)
        
        new_rate = max(0.5, min(new_rate, 3.0))
        self.player.set_rate(new_rate)
        self.lbl_speed.setText(f"x{new_rate}")

    # =================================================
    # GESTIÓN DE EJERCICIOS Y ARCHIVOS
    # =================================================

    # Busca archivos extra (PDFs, ejercicios) en la carpeta del video y crea botones para abrirlos.

    def _load_related_files(self, folder):
        while self.files_layout.count():
            child = self.files_layout.takeAt(0)
            if child.widget(): child.widget().deleteLater()
        while self.ex_layout.count():
            child = self.ex_layout.takeAt(0)
            if child.widget(): child.widget().deleteLater()
            
        for f in sorted(os.listdir(folder)):
            full_p = os.path.join(folder, f)
            
            # SECCIÓN EJERCICIOS (Refactorizada con Widget)
            if os.path.isdir(full_p) and f.lower().startswith("ejercicio"):
                
                ex_widget = ExerciseWidget(
                    parent=self.exercises_container,
                    folder_path=full_p, 
                    folder_name=f, 
                    dark_mode=self.dark_mode
                )
                
                # CONECTAMOS las señales a nuestros métodos locales.
                # Usamos lambda para pasar los argumentos necesarios (ruta fuente, ruta padre)
                ex_widget.on_open_ide_click = lambda p, parent=folder: self._open_in_ide_enhanced(p, parent)
                ex_widget.on_copy_click = lambda p, parent=folder: self._copy_exercises_to_work_dir(p, parent)
                
                self.ex_layout.addWidget(ex_widget)
                
            elif os.path.isfile(full_p):
                ext = os.path.splitext(f)[1].lower()
                if ext not in VIDEO_EXTS and ext not in AUDIO_EXTS and ext != ".test" and not f.endswith(".txt") and not f.endswith(".md"):
                     btn = QPushButton(f)
                     btn.clicked.connect(lambda ch, p=full_p: QDesktopServices.openUrl(QUrl.fromLocalFile(p)))
                     self.files_layout.addWidget(btn)

    # Abre el IDE usando el FileManager.

    def _open_in_ide(self, path):
        ide_config = self.data_manager.get_ide_path()
        
        if FileManager.open_in_ide(path, ide_config):
            return
            
        QMessageBox.warning(self, "IDE no encontrado", 
                            "No se pudo abrir un editor de código.\nConfigura la ruta en 'Opciones'.")

    #   Lógica para F8: Busca automáticamente la primera carpeta compatible (Ejercicio, Ejercicios, etc.) y lo abre en el IDE.

    def _open_current_exercise_shortcut(self):
        if not self.current_media_info:
            return

        # 1. Obtener directorio del capítulo actual.
        current_dir = (self.current_media_info.get("parent_dir") or 
                       self.current_media_info.get("chapter_dir"))
        
        if not current_dir or not os.path.exists(current_dir):
            return

        # 2. Buscar carpeta de ejercicio.
        target_path = None
        
        # Lista de prefijos válidos (puedes agregar "source", "codigo", "practica", etc.).
        valid_prefixes = ("ejercicio", "ejercicios") 
        
        try:
            for entry in sorted(os.listdir(current_dir)):
                full_path = os.path.join(current_dir, entry)
                
                # Verificamos si es carpeta Y si empieza por alguno de los prefijos.
                if os.path.isdir(full_path) and entry.lower().startswith(valid_prefixes):
                    target_path = full_path
                    break
        except OSError:
            pass

        # 3. Abrir o Notificar.
        if target_path:
            # Pasamos target_path (la carpeta 'Ejercicios') y current_dir (la carpeta del Capítulo).
            self._open_in_ide_enhanced(target_path, current_dir)
        else:
            # Feedback en consola (no invasivo).
            print(f"F8: No se encontraron carpetas {valid_prefixes} en: {current_dir}")

    def change_audios(self):
        last_dir = self.data_manager.get_last_open_dir()
        path = QFileDialog.getExistingDirectory(self, "Seleccionar Directorio de Audios", last_dir)
        # ------------------------------------
        
        if path:
            self.course_path = path
            
            # --- NUEVO: Guardar nueva ruta ---
            self.data_manager.set_last_open_dir(path)
            # ---------------------------------
            
            # Reset UI
            self.lbl_course_title.setText(os.path.basename(path))
            self.lbl_chapter_title.setText("...")
            self.lbl_media_title.setText("Selecciona un audio")
            
            self.player.stop()
            self.txt_desc.clear()
            self.txt_notes.clear()
            self.img_course.clear()
            self.chk_completed.setChecked(False)
            self.chk_completed.setEnabled(False)
            
            # Construir árbol recursivo
            self._build_audio_tree(path)
            
            self._load_course_image(path)

    # Convierte nombres de archivo tipo "01-01-2024" a "1 de Enero del 2024". Convierte nombres de archivo/carpeta con formato de fecha. Ejemplo: '01 - 23-01-2025' -> '01 - 23 de Enero del 2025'

    def _format_date_name(self, filename: str) -> str:
        import re
        name_no_ext = os.path.splitext(filename)[0]
        
        # Intento 1: Con índice "XX - DD-MM-AAAA".
        match_index = re.match(r'^\s*(\d+)\s*-\s*(\d{2})-(\d{2})-(\d{4})\s*$', name_no_ext)
        
        # Intento 2: Sin índice "DD-MM-AAAA".
        match_simple = re.match(r'^\s*(\d{2})-(\d{2})-(\d{4})\s*$', name_no_ext)
        
        day, month, year = None, None, None
        prefix = ""
        
        if match_index:
            prefix = f"{match_index.group(1)} - "
            day = int(match_index.group(2))
            month = int(match_index.group(3))
            year = int(match_index.group(4))
        elif match_simple:
            day = int(match_simple.group(1))
            month = int(match_simple.group(2))
            year = int(match_simple.group(3))
        else:
            return name_no_ext # No coincide, devolver nombre original

        meses = {
            1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril",
            5: "Mayo", 6: "Junio", 7: "Julio", 8: "Agosto",
            9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre"
        }
        mes_nombre = meses.get(month, str(month))
        
        return f"{prefix}{day:02d} de {mes_nombre} del {year}"
    
    #   Formatea nombres con fecha (DD-MM-AAAA). Si no es fecha, devuelve el original. Maneja 'include_index' para evitar errores de argumentos.
    
    def _format_date_name_v14(self, raw_name: str, include_index: bool = True) -> str:
        import re
        name_no_ext = os.path.splitext(raw_name)[0]
        
        # Regex: Detecta "04 - 12-12-2024" o "12-12-2024"
        match = re.match(r'^\s*(\d+\s*-\s*)?(\d{2})-(\d{2})-(\d{4})\s*$', name_no_ext)
        
        if not match:
            return name_no_ext

        prefix = match.group(1) or ""
        day = int(match.group(2))
        month = int(match.group(3))
        year = int(match.group(4))

        meses = {
            1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril",
            5: "Mayo", 6: "Junio", 7: "Julio", 8: "Agosto",
            9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre"
        }
        mes_nombre = meses.get(month, str(month))
        
        date_str = f"{day:02d} de {mes_nombre} del {year}"
        
        if include_index and prefix:
            return f"{prefix}{date_str}"
        
        return date_str
    
    # Lógica especial para cursos de solo audio. Aplana carpetas si contienen un único archivo de audio con el mismo nombre.

    def _build_audio_tree(self, root_path):
        # Delegamos TODO al manager
        self.tree_manager.set_course_path(root_path)
        self.tree_manager.build_audio_tree(root_path)

    # Helper para agregar el nodo de audio con metadata y estilo.

    def _add_audio_node(self, parent_item, folder_path, filename, chapter_title_display):
        base_name, _ = os.path.splitext(filename)
        
        # Formatear nombre del archivo (Ej: "01 - Audio.m4a").
        display_text = self._format_date_name_v14(base_name, include_index=True)
        
        audio_item = QTreeWidgetItem(parent_item)
        audio_item.setText(0, display_text)
        
        # Metadata.
        audio_info = {
            "type": "audio",
            "chapter_title": chapter_title_display,
            "chapter_dir": folder_path,
            "audio_title": base_name,
            "audio_path": os.path.join(folder_path, filename),
            "parent_dir": folder_path
        }
        audio_item.setData(0, Qt.ItemDataRole.UserRole, audio_info)
        
        # Verificar si está completado (Color verde).
        rel_path = os.path.relpath(audio_info["audio_path"], self.course_path)
        is_done = self.data_manager.is_video_completed(self.course_path, rel_path)
        
        if hasattr(self, '_update_item_color'):
            self._update_item_color(audio_item)
        else:
            color = QColor("#00AA00") if is_done else (QColor("white") if self.dark_mode else QColor("black"))
            audio_item.setForeground(0, color)
    
    # Actualiza la etiqueta de velocidad cuando el reproductor notifica un cambio.
    
    def _on_rate_changed(self, rate):
        from app.utils.helpers import format_playback_rate
        # Si no tienes el helper importado, usa simplemente: f"x{rate:.1f}"
        self.lbl_speed.setText(format_playback_rate(rate))

    # Habilita el botón de guardar cuando el usuario escribe.

    def _on_notes_text_changed(self):
        self.btn_save_notes.setEnabled(True)

    # Muestra mensaje informativo con botón 'Aceptar' CENTRADO usando QDialog.

    def _show_custom_info(self, title, text):
        dlg = QDialog(self)
        dlg.setWindowTitle(title)
        dlg.setWindowFlags(dlg.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint)
        dlg.setMinimumWidth(300)
        
        layout = QVBoxLayout(dlg)
        
        # Contenido (Icono + Texto).
        h_content = QHBoxLayout()
        # Icono informativo standard.
        icon_label = QLabel()
        icon_label.setPixmap(self.style().standardIcon(QStyle.StandardPixmap.SP_MessageBoxInformation).pixmap(40, 40))
        icon_label.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        text_label = QLabel(text)
        text_label.setWordWrap(True)
        text_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        h_content.addWidget(icon_label)
        h_content.addSpacing(15)
        h_content.addWidget(text_label, 1)
        layout.addLayout(h_content)
        layout.addSpacing(15)
        
        # Botón Centrado.
        h_btns = QHBoxLayout()
        h_btns.addStretch()
        btn_accept = QPushButton("Aceptar")
        btn_accept.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_accept.clicked.connect(dlg.accept)
        h_btns.addWidget(btn_accept)
        h_btns.addStretch()
        
        layout.addLayout(h_btns)
        
        # Estilos.
        if self.dark_mode:
            dlg.setStyleSheet("""
                QDialog { background-color: #353535; color: white; }
                QLabel { color: white; }
                QPushButton { background-color: #444; color: white; border: 1px solid #666; padding: 5px 15px; }
            """)
            
        dlg.exec()

    # Lee el archivo info.txt, convierte enlaces a HTML clicable y lo muestra en una ventana emergente.

    def show_course_info(self):
        if not self.course_path: return
        
        info_path = os.path.join(self.course_path, "info.txt")
        content = ""
        
        # --- NUEVO: Búsqueda robusta de info.txt ---
        try:
            files = os.listdir(self.course_path)
            for f in files:
                if f.lower() == "info.txt":
                    info_path = os.path.join(self.course_path, f)
                    break
        except OSError:
            pass
        
        if os.path.exists(info_path):
            try:
                with open(info_path, "r", encoding="utf-8") as f:
                    content = f.read()
            except Exception:
                content = "Error al leer el archivo info.txt"
        else:
            content = "No se encontró el archivo info.txt en la raíz del curso."

        dlg = QDialog(self)
        dlg.setWindowTitle("Información del Curso")
        dlg.resize(500, 240) # El primer valor es el ancho inicial y el segundo la altura.
        dlg.setWindowFlags(dlg.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint)
        
        layout = QVBoxLayout(dlg)
        layout.setContentsMargins(15, 15, 15, 15)
        
        # --- CONFIGURACIÓN DEL NAVEGADOR ---
        browser = QTextBrowser()
        browser.setOpenExternalLinks(True) 
        browser.setFrameShape(QFrame.Shape.NoFrame) 
        
        # 1. Escapar HTML y Detectar Enlaces
        safe_content = html.escape(content)
        url_pattern = re.compile(r'((?:https?://|www\.)[^\s]+)')
        
        def link_wrap(match):
            url = match.group(1)
            href = url
            if url.startswith("www."):
                href = "http://" + url
            # Enlace simple sin estilos extra para no romper herencia
            return f'<a href="{href}">{url}</a>'
            
        linked_content = url_pattern.sub(link_wrap, safe_content)
        
        # Convertir saltos de línea a <br>
        html_content = linked_content.replace("\n", "<br>")
        
        # 2. Definir Colores según Tema
        if self.dark_mode:
            bg_color = "#353535"
            text_color = "white"
            link_color = "#66ccff" 
            btn_bg = "#444"
            btn_border = "#666"
        else:
            bg_color = "#f0f0f0"
            text_color = "black"
            link_color = "#0000ff"
            btn_bg = "#e0e0e0"
            btn_border = "#ccc"

        # 3. HTML "NUCLEAR" (Estilos en línea y atributos clásicos)
        # Usamos <div align="center"> que Qt respeta siempre.
        final_html = f"""
        <html>
        <head>
            <style type="text/css">
                a {{ color: {link_color}; text-decoration: underline; }}
            </style>
        </head>
        <body style="background-color:{bg_color};">
            <div align="center" style="font-size: 14px; font-weight: bold; color: {text_color}; font-family: 'Segoe UI', sans-serif;">
                {html_content}
            </div>
        </body>
        </html>
        """
        
        browser.setHtml(final_html)
        
        # Aseguramos el fondo desde el widget también por si acaso
        browser.setStyleSheet(f"QTextBrowser {{ background-color: {bg_color}; border: none; }}")
        
        layout.addWidget(browser)
        
        # Botón Aceptar
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        btn_ok = QPushButton("Aceptar")
        btn_ok.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_ok.setFixedWidth(100)
        btn_ok.clicked.connect(dlg.accept)
        btn_layout.addWidget(btn_ok)
        btn_layout.addStretch()
        
        layout.addLayout(btn_layout)
        
        # Estilos del Diálogo y Botón
        dlg.setStyleSheet(f"""
            QDialog {{ background-color: {bg_color}; color: {text_color}; }}
            QPushButton {{ 
                background-color: {btn_bg}; 
                color: {text_color}; 
                border: 1px solid {btn_border}; 
                padding: 6px; 
                border-radius: 4px;
                font-weight: bold;
            }}
            QPushButton:hover {{ background-color: #888; color: white; }}
        """)
        
        dlg.exec()

    # Muestra confirmación con botones CENTRADOS.

    def _show_custom_confirmation(self, title, text):
        dlg = QDialog(self)
        dlg.setWindowTitle(title)
        dlg.setWindowFlags(dlg.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint)
        dlg.setMinimumWidth(350)
        
        layout = QVBoxLayout(dlg)
        
        h_content = QHBoxLayout()
        icon_label = QLabel()
        icon_label.setPixmap(self.style().standardIcon(QStyle.StandardPixmap.SP_MessageBoxQuestion).pixmap(40, 40))
        icon_label.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        text_label = QLabel(text)
        text_label.setWordWrap(True)
        
        h_content.addWidget(icon_label)
        h_content.addSpacing(15)
        h_content.addWidget(text_label, 1)
        layout.addLayout(h_content)
        layout.addSpacing(15)
        
        # Botones Centrados
        h_btns = QHBoxLayout()
        h_btns.addStretch() # Resorte
        
        btn_accept = QPushButton("Aceptar")
        btn_accept.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_accept.clicked.connect(dlg.accept)
        
        btn_cancel = QPushButton("Cancelar")
        btn_cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_cancel.clicked.connect(dlg.reject)
        
        h_btns.addWidget(btn_accept)
        h_btns.addSpacing(10)
        h_btns.addWidget(btn_cancel)
        h_btns.addStretch() # Resorte
        
        layout.addLayout(h_btns)
        
        if self.dark_mode:
            dlg.setStyleSheet("""
                QDialog { background-color: #353535; color: white; }
                QLabel { color: white; }
                QPushButton { background-color: #444; color: white; border: 1px solid #666; padding: 5px 15px; }
            """)
            
        return dlg.exec() == QDialog.DialogCode.Accepted

    # =======================================================================
    #   FUNCIÓN PARA ASEGURAR ESCRITURA EN CAMPOS "APUNTES" Y "DESCRIPCIÓN"
    # =======================================================================

    def _safe_shortcut(self, action_callback):
        focus_widget = QApplication.focusWidget()
        if focus_widget in [self.txt_notes, self.txt_desc]:
            return 
        action_callback()

    # =======================================================================
    #   FUNCIONES PARA LA SUBIDA/BAJADA DE VOLUMEN Y PANTALLA COMPLETA
    # =======================================================================

    def _volume_up(self):
        curr = self.player.get_volume()
        self.player.set_volume(min(100, curr + 5))
        self.slider_vol.setValue(self.player.get_volume())

    def _volume_down(self):
        curr = self.player.get_volume()
        self.player.set_volume(max(0, curr - 5))
        self.slider_vol.setValue(self.player.get_volume())

    def _exit_fullscreen(self):
        if self.is_video_fullscreen:
            self.toggle_fullscreen()

    # =======================================================================
    #   ATAJOS DE TECLADO (SHORTCUTS) - CONFIGURACIÓN AVANZADA
    # =======================================================================

    # Configura los atajos de teclado globales de la aplicación.

    def setup_shortcuts(self):
        
        # --- 1. CONTROL DE REPRODUCCIÓN Y NAVEGACIÓN --- #
        
        # Espacio: Play/Pause (Con validación de escritura)
        self.sc_play = QShortcut(QKeySequence(Qt.Key.Key_Space), self)
        self.sc_play.activated.connect(lambda: self._safe_shortcut(self.player.toggle_play_pause))

        # Flechas Simples: Seek +/- 5 seg (Con validación)
        self.sc_seek_back = QShortcut(QKeySequence(Qt.Key.Key_Left), self)
        self.sc_seek_back.activated.connect(lambda: self._safe_shortcut(lambda: self.player.seek_relative(-5000)))
        
        self.sc_seek_fwd = QShortcut(QKeySequence(Qt.Key.Key_Right), self)
        self.sc_seek_fwd.activated.connect(lambda: self._safe_shortcut(lambda: self.player.seek_relative(5000)))

        # Alt + Flechas: Cambiar de Video (Anterior / Siguiente)
        QShortcut(QKeySequence("Alt+Right"), self).activated.connect(self.play_next)
        QShortcut(QKeySequence("Alt+Left"), self).activated.connect(self.play_previous)

        # --- 2. CONTROL DE VELOCIDAD (Ctrl +, -, *) --- #
        
        # Aumentar velocidad (Ctrl + +) teclado numérico
        QShortcut(QKeySequence("Ctrl++"), self).activated.connect(lambda: self.change_speed(0.1))
        
        # Disminuir velocidad (Ctrl + -)
        QShortcut(QKeySequence("Ctrl+-"), self).activated.connect(lambda: self.change_speed(-0.1))
        
        # Normalizar velocidad (Ctrl + *)
        QShortcut(QKeySequence("Ctrl+*"), self).activated.connect(lambda: self.change_speed(0, reset=True))


        # --- 3. MENÚS Y OPCIONES (Alt + Letra) --- #
        
        # Alt + V: Abrir Cursos (Video)
        QShortcut(QKeySequence("Alt+C"), self).activated.connect(self.change_course)
        
        # Alt + A: Abrir Audios
        QShortcut(QKeySequence("Alt+A"), self).activated.connect(self.change_audios)
        
        # Alt + O: Opciones
        QShortcut(QKeySequence("Alt+O"), self).activated.connect(self.show_options)
        
        # Alt + P: Ventana Configurar Pomodoro
        QShortcut(QKeySequence("Alt+P"), self).activated.connect(self.show_pomodoro)
        
        # Alt + T: Cambiar Tema (Oscuro/Claro)
        QShortcut(QKeySequence("Alt+T"), self).activated.connect(self.toggle_theme)


        # --- 4. FUNCIONES "F" (Teclas de Función) --- #
        
        # F1: Acerca de
        QShortcut(QKeySequence(Qt.Key.Key_F1), self).activated.connect(self.show_about)

        # F2: Información del Curso
        QShortcut(QKeySequence(Qt.Key.Key_F2), self).activated.connect(self.show_course_info)
        
        # F3: Iniciar Pomodoro (Valores por defecto)
        QShortcut(QKeySequence(Qt.Key.Key_F3), self).activated.connect(self._toggle_pomodoro_f3)
        
        # F4: Detener Pomodoro
        QShortcut(QKeySequence(Qt.Key.Key_F4), self).activated.connect(self._stop_pomodoro_and_notify)

        # F5: Marcar la Casilla de Verificación ¿Completado?
        QShortcut(QKeySequence(Qt.Key.Key_F5), self).activated.connect(self.chk_completed.click)

        # F8: Abrir en el IDE (Solo si existe un Directorio "Ejercicio" o "Ejercicios")
        QShortcut(QKeySequence(Qt.Key.Key_F8), self).activated.connect(self._open_current_exercise_shortcut)
        
        # F9: Habilitada/Deshabilita Repetir Indefinidamente.
        QShortcut(QKeySequence(Qt.Key.Key_F9), self).activated.connect(self.btn_repeat.toggle)

        # F10: Habilitada/Deshabilita Reproducción Continua.
        QShortcut(QKeySequence(Qt.Key.Key_F10), self).activated.connect(self.btn_continuous.toggle)

        # F11 para Pantalla Completa
        QShortcut(QKeySequence(Qt.Key.Key_F11), self).activated.connect(self.toggle_fullscreen)
        QShortcut(QKeySequence(Qt.Key.Key_Escape), self).activated.connect(self._exit_fullscreen)

        # --- 5. UTILIDADES EXTRAS --- #
        
        # Volumen (Flechas Arriba/Abajo)
        self.sc_vol_up = QShortcut(QKeySequence(Qt.Key.Key_Up), self)
        self.sc_vol_up.activated.connect(self._volume_up)
        
        self.sc_vol_down = QShortcut(QKeySequence(Qt.Key.Key_Down), self)
        self.sc_vol_down.activated.connect(self._volume_down)

        # Alt + S: Guardar apuntes
        QShortcut(QKeySequence("Alt+S"), self).activated.connect(self.save_notes)

        # Alt + E: Exportar Apuntes
        QShortcut(QKeySequence("Alt+E"), self).activated.connect(self.show_export_dialog)
    
    # =======================================================================
    #   LÓGICA DE GESTIÓN DE EJERCICIOS (COPIAR Y ABRIR)
    # =======================================================================

    def _get_work_target_path(self, chapter_dir_path):
        return FileManager.get_work_target_path(
            self.data_manager.get_work_dir(),
            self.course_path,
            chapter_dir_path
        )

    # ===========================================================================================
    # FUNCIÓN PARA COPIAR EL CONTENIDO DEL EJERCICIO AL DIRECTORIO DE TRABAJO
    # ===========================================================================================

    # Copia el CONTENIDO de la carpeta de ejercicios al destino estructurado. Incluye lógica de seguridad (Backup) si el destino ya existe.

    def _copy_exercises_to_work_dir(self, source_path, chapter_dir_path):
        # 1. Calcular ruta usando el FileManager.
        target_path = self._get_work_target_path(chapter_dir_path)
        
        if not target_path:
            QMessageBox.warning(self, "Configuración Faltante", 
                "No has definido un 'Directorio de Trabajo' válido en Opciones.\n"
                "Por favor configúralo antes de copiar.")
            return

        # 2. VERIFICACIÓN DE EXISTENCIA (Restaurada).        
        if FileManager.target_exists_and_not_empty(target_path):
            
            msg = QMessageBox(self)
            msg.setWindowTitle("Archivos existentes detectados")
            msg.setIcon(QMessageBox.Icon.Warning)
            msg.setText(f"Ya existen archivos en el directorio destino:\n\n{target_path}")
            msg.setInformativeText(
                "¿Qué desea hacer?\n\n"
                "• Sobrescribir (Crear Backup): Mueve tus archivos actuales a una carpeta de respaldo y copia los nuevos.\n"
                "• Cancelar: No hace nada."
            )
            
            # Forzar el Ancho.
            layout = msg.layout()
            spacer = QSpacerItem(600, 0, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)
            layout.addItem(spacer, layout.rowCount(), 0, 1, layout.columnCount())
            
            # Botones personalizados.
            btn_backup = msg.addButton("Sobrescribir (Con Backup)", QMessageBox.ButtonRole.AcceptRole)
            btn_cancel = msg.addButton("Cancelar", QMessageBox.ButtonRole.RejectRole)
            
            if self.dark_mode:
                msg.setStyleSheet("background-color: #353535; color: white;")
                
            msg.exec()
            
            if msg.clickedButton() == btn_cancel:
                return
                
            # 3. LÓGICA DE BACKUP (Delegada al FileManager pero llamada aquí).
            try:
                backup_name = FileManager.create_backup(target_path)
                # print(f"Backup creado: {backup_name}") # Opcional
                
            except OSError as e:
                QMessageBox.critical(self, "Error de Backup", 
                    f"No se pudo crear el respaldo de los archivos existentes.\n"
                    f"La operación se ha cancelado para proteger tus datos.\n\nError: {e}")
                return

        # 4. PROCESO DE COPIA (Usando FileManager).
        try:
            FileManager.copy_directory_content(source_path, target_path)
            
            final_msg = "Ejercicios copiados correctamente."
            if 'backup_name' in locals():
                final_msg += f"\n\n(Tus archivos anteriores se guardaron en la carpeta: '{backup_name}')"
                
            self._show_custom_info("Éxito", final_msg)
            
        except Exception as e:
            QMessageBox.critical(self, "Error de Copia", f"No se pudo copiar: {str(e)}")

    # =================================================
    # ABRIR EN IDE (_OPEN_IN_IDE_ENHANCED)
    # =================================================

    # Pregunta al usuario si quiere abrir la carpeta original o la de trabajo.

    def _open_in_ide_enhanced(self, original_exercises_path, chapter_dir_path):
        # 1. Crear el Diálogo Personalizado.
        dlg = QDialog(self)
        dlg.setWindowTitle("¿Qué directorio abrir?")
        dlg.setWindowFlags(dlg.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint)
        dlg.setMinimumWidth(450)

        layout = QVBoxLayout(dlg)
        layout.addWidget(QLabel("<b>Seleccione dónde quiere abrir los ejercicios del capítulo:</b>"))
        layout.addSpacing(10)
        
        # Radio Buttons.
        rb_original = QRadioButton("Abrir en el directorio original del curso.")
        rb_original.setChecked(True)
        
        rb_work = QRadioButton("Abrir en el directorio de trabajo definido.")
        
        layout.addWidget(rb_original)
        layout.addWidget(rb_work)
        layout.addSpacing(15)
        
        # Botones Aceptar / Cancelar.
        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        btns.accepted.connect(dlg.accept)
        btns.rejected.connect(dlg.reject)
        layout.addWidget(btns)
        
        # Estilos (si es Dark Mode).
        if self.dark_mode:
            dlg.setStyleSheet("QDialog { background-color: #353535; color: white; } QRadioButton { color: white; }")
            
        # 2. Ejecutar Diálogo.
        if dlg.exec() == QDialog.DialogCode.Accepted:
            if rb_original.isChecked():
                self._open_in_ide(original_exercises_path)
            else:
                # Lógica Directorio de Trabajo.
                target_path = self._get_work_target_path(chapter_dir_path)
                
                # A. Validar si existe el path configurado.
                if not target_path: # Significa que no hay WorkDir configurado.
                     QMessageBox.warning(self, "Aviso", "No has configurado un Directorio de Trabajo en Opciones.")
                     return

                # B. Validar si los archivos existen FÍSICAMENTE. Asumimos que si existe la carpeta del capítulo, ya se copió algo.
                if os.path.exists(target_path) and os.listdir(target_path):
                    self._open_in_ide(target_path)
                else:
                    # C. No existen: Preguntar si copiar.
                    msg_box = QMessageBox(self)
                    msg_box.setWindowTitle("Archivos no encontrados")
                    msg_box.setText("No ha copiado los ejercicios a su directorio de trabajo.")
                    msg_box.setInformativeText("¿Desea copiarlos ahora mismo?")
                    msg_box.setIcon(QMessageBox.Icon.Question)
                    
                    btn_yes = msg_box.addButton("Copiar", QMessageBox.ButtonRole.AcceptRole)
                    msg_box.addButton("Cancelar", QMessageBox.ButtonRole.RejectRole)
                    
                    if self.dark_mode:
                        msg_box.setStyleSheet("background-color: #353535; color: white;")
                        
                    msg_box.exec()
                    
                    if msg_box.clickedButton() == btn_yes:
                        # Copiar.
                        self._copy_exercises_to_work_dir(original_exercises_path, chapter_dir_path)
                        # Intentar abrir de nuevo si se copió.
                        if os.path.exists(target_path):
                            self._open_in_ide(target_path)