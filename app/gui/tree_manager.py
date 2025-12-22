"""
Función: Gestor del árbol de navegación (panel izquierdo).

Escanea la carpeta del curso y "dibuja" la lista de capítulos y videos en el panel
lateral. Se encarga de pintar de verde los videos vistos y manejar los iconos.

"""

# =================================================
# IMPORTACIONES NECESARIAS
# =================================================

import os
from PyQt6.QtWidgets import QTreeWidget, QTreeWidgetItem, QTreeWidgetItemIterator
from PyQt6.QtGui import QIcon, QBrush, QColor, QFont
from PyQt6.QtCore import Qt

from app.config import VIDEO_EXTS, AUDIO_EXTS
from app.utils.paths import resource_path
from app.utils.helpers import format_date_name
from app.data.data_manager import DataManager

# =================================================
# CLASE COURSETREEMANAGER (GESTOR DEL ÁRBOL)
# =================================================

# Se encarga de construir, poblar y actualizar el árbol de contenidos (QTreeWidget) situado en el panel izquierdo de la aplicación.
# Maneja la lógica de iconos, colores (visto/no visto) y estructura de carpetas.

class CourseTreeManager:
    
    # =================================================
    # CONSTRUCTOR (__INIT__)
    # =================================================
    
    def __init__(self, tree_widget: QTreeWidget, data_manager: DataManager, dark_mode: bool):
        self.tree = tree_widget
        self.data_manager = data_manager
        self.dark_mode = dark_mode
        self.course_path = ""

        # Cargar iconos en memoria al iniciar
        self._load_icons()

    # =================================================
    # CARGA DE ICONOS (_LOAD_ICONS)
    # =================================================
    
    # Carga los iconos necesarios (como el del Test) según el tema actual (Dark/Light).

    def _load_icons(self):
        suffix = "_dark.svg" if self.dark_mode else "_light.svg"
        test_path = resource_path(os.path.join("assets", "images", f"test{suffix}"))
        self.icon_test = QIcon(test_path) if os.path.exists(test_path) else QIcon()

    # =================================================
    # ESTABLECER RUTA (SET_COURSE_PATH)
    # =================================================

    def set_course_path(self, path):
        self.course_path = path

    # =================================================
    # ACTUALIZAR TEMA (UPDATE_THEME)
    # =================================================
    
    # Se llama cuando el usuario cambia el tema en la ventana principal.
    # Recarga los iconos y repinta todo el árbol para asegurar contraste correcto. (OJO aún falla al cambiar el tema en el árbol, se actualiza a presionar otra rama (contenido)).

    def update_theme(self, is_dark: bool):
        self.dark_mode = is_dark
        self._load_icons()
        
        # Iterar sobre todos los elementos para repintar el texto y cambiar iconos.
        iterator = QTreeWidgetItemIterator(self.tree)
        while iterator.value():
            item = iterator.value()
            self.update_item_color(item)
            # Actualizar icono test si corresponde
            data = item.data(0, Qt.ItemDataRole.UserRole)
            if data and data.get("type") == "test":
                item.setIcon(0, self.icon_test)
            iterator += 1

    # =================================================
    # CONSTRUIR ÁRBOL DE VIDEOS (BUILD_VIDEO_TREE)
    # =================================================
    
    # Lógica principal para cursos de video.
    # Estructura: Raíz -> Capítulos (Carpetas) -> Videos/Tests

    def build_video_tree(self, root_path: str):
        self.tree.clear()
        try:
            entries = sorted(os.listdir(root_path))
        except OSError:
            return

        # 1. Archivos sueltos en raíz (sin capítulo).
        for f in entries:
            full_path = os.path.join(root_path, f)
            if os.path.isfile(full_path):
                ext = os.path.splitext(f)[1].lower()
                if ext in VIDEO_EXTS or ext in AUDIO_EXTS:
                    self._create_media_item(self.tree, f, full_path, root_path)

        # 2. Carpetas (Capítulos).
        for entry in entries:
            full_path = os.path.join(root_path, entry)
            if not os.path.isdir(full_path):
                continue
            
            # Crear nodo padre (Capítulo).
            chapter_item = QTreeWidgetItem(self.tree)
            chapter_item.setText(0, entry)
            # Poner en negrita.
            f_bold = chapter_item.font(0)
            f_bold.setBold(True)
            chapter_item.setFont(0, f_bold)
            
            try:
                sub_files = sorted(os.listdir(full_path))
            except OSError:
                continue

            # Agregar Videos dentro del capítulo.
            for f in sub_files:
                ext = os.path.splitext(f)[1].lower()
                if ext in VIDEO_EXTS or ext in AUDIO_EXTS:
                    media_path = os.path.join(full_path, f)
                    self._create_media_item(chapter_item, f, media_path, full_path)

            # Buscar y agregar Tests dentro del capítulo.
            self._scan_tests(chapter_item, full_path)

    # =================================================
    # CONSTRUIR ÁRBOL DE AUDIOS (BUILD_AUDIO_TREE)
    # =================================================
    
    # Lógica especializada para cursos de audio. 
    # Utiliza recursividad para navegar subcarpetas anidadas.

    def build_audio_tree(self, root_path: str):
        self.tree.clear()
        root_name = os.path.basename(root_path.rstrip(os.sep))
        # Nodo raíz del curso
        root_item = QTreeWidgetItem(self.tree)
        root_item.setText(0, root_name)
        f_root = root_item.font(0); f_root.setBold(True); root_item.setFont(0, f_root)
        
        self._build_audio_recursive(root_item, root_path)
        self.tree.expandItem(root_item)

    # =================================================
    # RECURSIVIDAD AUDIOS (_BUILD_AUDIO_RECURSIVE)
    # =================================================
    
    # Navega carpetas. Si encuentra una carpeta que contiene UN solo archivo de audio con el mismo nombre, la "aplana" (muestra la carpeta como si fuera el archivo).

    def _build_audio_recursive(self, parent_item, current_path):
        try:
            entries = sorted(os.listdir(current_path))
        except OSError:
            return

        dirs = [e for e in entries if os.path.isdir(os.path.join(current_path, e))]
        files = [e for e in entries if os.path.isfile(os.path.join(current_path, e))]

        # Procesar Carpetas
        for d_name in dirs:
            full_dir_path = os.path.join(current_path, d_name)
            
            # Lógica de aplanamiento (Smart Flatten).
            target_file = None
            try:
                sub_entries = os.listdir(full_dir_path)
                for sub_f in sub_entries:
                    s_name, s_ext = os.path.splitext(sub_f)
                    # Si el archivo se llama igual a la carpeta y es audio.
                    if s_name == d_name and s_ext.lower() in AUDIO_EXTS:
                        target_file = sub_f
                        break
            except OSError:
                pass

            if target_file:
                # Caso especial: Carpeta se visualiza como un nodo reproducible.
                chapter_display = parent_item.text(0)
                self._add_audio_node(parent_item, full_dir_path, target_file, chapter_display)
            else:
                # Caso normal: Es una carpeta contenedora, seguimos bajando.
                display_text = format_date_name(d_name)
                dir_item = QTreeWidgetItem(parent_item)
                dir_item.setText(0, display_text)
                font = dir_item.font(0); font.setBold(True); dir_item.setFont(0, font)
                # Llamada recursiva
                self._build_audio_recursive(dir_item, full_dir_path)

        # Procesar Archivos sueltos
        for f_name in files:
            if f_name.lower().endswith(AUDIO_EXTS):
                chapter_display = parent_item.text(0)
                self._add_audio_node(parent_item, current_path, f_name, chapter_display)

    # =================================================
    # CREAR ITEM DE MEDIA (_CREATE_MEDIA_ITEM)
    # =================================================
    
    # Crea el nodo visual (QTreeWidgetItem) para un video y adjunta sus datos.

    def _create_media_item(self, parent, filename, full_path, parent_dir):
        item = QTreeWidgetItem(parent)
        item.setText(0, os.path.splitext(filename)[0])
        # Guardamos la metadata crítica en UserRole.
        data = {"type": "media", "path": full_path, "parent_dir": parent_dir}
        item.setData(0, Qt.ItemDataRole.UserRole, data)
        # Aplicamos color si ya fue visto.
        self.update_item_color(item)

    # =================================================
    # ESCANEAR TESTS (_SCAN_TESTS)
    # =================================================
    
    # Busca una carpeta llamada "Tests" dentro del capítulo y agrega los exámenes al árbol.

    def _scan_tests(self, parent_item, folder_path):
        tests_path = os.path.join(folder_path, "Tests")
        if os.path.exists(tests_path) and os.path.isdir(tests_path):
            test_files = [f for f in os.listdir(tests_path) if f.endswith(".test")]
            if test_files:
                # Crear sub-nodo "Test/Evaluaciones"
                root_t = QTreeWidgetItem(parent_item)
                root_t.setText(0, "Test/Evaluaciones")
                f = root_t.font(0); f.setItalic(True); root_t.setFont(0, f)
                
                for t_file in sorted(test_files):
                    t_item = QTreeWidgetItem(root_t)
                    t_item.setText(0, os.path.splitext(t_file)[0])
                    t_item.setIcon(0, self.icon_test)
                    t_data = {"type": "test", "path": os.path.join(tests_path, t_file)}
                    t_item.setData(0, Qt.ItemDataRole.UserRole, t_data)

    # =================================================
    # AGREGAR NODO AUDIO (_ADD_AUDIO_NODE)
    # =================================================
    
    # Helper específico para agregar nodos de audio con el formato de nombre correcto.

    def _add_audio_node(self, parent_item, folder_path, filename, chapter_display):
        base_name, _ = os.path.splitext(filename)
        display_text = format_date_name(base_name)
        
        item = QTreeWidgetItem(parent_item)
        item.setText(0, display_text)
        
        info = {
            "type": "audio",
            "chapter_title": chapter_display,
            "audio_title": base_name,
            "audio_path": os.path.join(folder_path, filename),
            "parent_dir": folder_path
        }
        item.setData(0, Qt.ItemDataRole.UserRole, info)
        self.update_item_color(item)

    # =================================================
    # ACTUALIZAR COLOR ITEM (UPDATE_ITEM_COLOR)
    # =================================================
    
    # Consulta al DataManager si el archivo está "Completado" y cambia el color del texto.
    # Verde = Visto. Blanco/Negro = No visto (según tema).

    def update_item_color(self, item):
        """Pinta verde si está completado."""
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if not data: return
        
        path = data.get("path") or data.get("audio_path") or data.get("video_path")
        if not path: return

        try:
            rel_path = os.path.relpath(path, self.course_path)
        except ValueError:
            rel_path = path
            
        is_done = self.data_manager.is_video_completed(self.course_path, rel_path)
        
        base_color = QColor("white") if self.dark_mode else QColor("black")
        color = QColor("#00AA00") if is_done else base_color
        item.setForeground(0, QBrush(color))