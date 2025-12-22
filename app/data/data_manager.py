"""
Función: El "cerebro" de la memoria. Gestiona el guardado y carga de datos.

Crea y lee un archivo JSON (user_data.data) en la carpeta del usuario.
Guarda qué videos has visto, tus apuntes, la configuración del tema
(oscuro/claro), historiales de exámenes y rutas preferidas.

"""

# =================================================
# IMPORTACIONES NECESARIAS
# =================================================

import os
import json

from typing import Dict, List, Any, Optional
from app.config import DATA_FOLDER_NAME, DATA_FILE_NAME, DEFAULT_THEME


# =================================================
# CLASE DATAMANAGER (GESTIÓN DE DATOS)
# =================================================

# Se encarga de manejar la persistencia de datos (progreso, notas, configuración) guardando y leyendo la información en un archivo JSON local (user_data.data).

class DataManager:
# Busca el archivo de datos en la carpeta AppData del usuario. Si no existe, crea uno nuevo.

    # =================================================
    # CONSTRUCTOR DE LA CLASE
    # =================================================
    
    # Inicializa las rutas donde se guardará el archivo de datos (AppData) y carga los datos existentes al instanciar la clase.
    
    def __init__(self):
        # %UserProfile%\AppData\Local\JLMLSoft\user_data.data
        self.app_data_dir = os.path.join(os.getenv('LOCALAPPDATA', os.path.expanduser('~')), DATA_FOLDER_NAME)
        self.data_file_path = os.path.join(self.app_data_dir, DATA_FILE_NAME)
        
        self.data: Dict[str, Any] = {}
        self._load_data()
    
    # =================================================
    # FUNCIÓN CARGAR DATOS (_LOAD_DATA)
    # =================================================
    
    # Lee el archivo JSON del disco. Si no existe o está corrupto, inicializa una estructura de diccionario vacía con valores por defecto.

    def _load_data(self) -> None:
        """Carga los datos del archivo JSON o inicializa la estructura base."""
        if not os.path.exists(self.app_data_dir):
            try:
                os.makedirs(self.app_data_dir)
            except OSError:
                pass 

        if os.path.exists(self.data_file_path):
            try:
                with open(self.data_file_path, 'r', encoding='utf-8') as f:
                    self.data = json.load(f)
            except (json.JSONDecodeError, IOError):
                self.data = {}
        else:
            self.data = {}

    # Asegurar estructura base
        if "config" not in self.data:
            self.data["config"] = {"theme": DEFAULT_THEME, "ide_path": ""}
        if "courses" not in self.data:
            self.data["courses"] = {}

    # =================================================
    # FUNCIÓN GUARDAR DATOS (SAVE_DATA)
    # =================================================
    
    # Escribe el estado actual del diccionario 'self.data' en el archivo físico JSON.
    # Se debe llamar cada vez que se modifica algún dato importante.

    def save_data(self) -> None:
        """Escribe el estado actual en el disco."""
        try:
            with open(self.data_file_path, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, ensure_ascii=False, indent=4)
        except IOError as e:
            print(f"Error crítico guardando datos: {e}")

    # =================================================
    # GESTIÓN DEL TEMA (GET/SET THEME)
    # =================================================
    
    # Recupera o actualiza la preferencia visual (Oscuro/Claro).

    def get_theme(self) -> str:
        return self.data["config"].get("theme", DEFAULT_THEME)

    def set_theme(self, theme_mode: str) -> None:
        self.data["config"]["theme"] = theme_mode
        self.save_data()

    # =================================================
    # GESTIÓN RUTA IDE (GET/SET IDE PATH)
    # =================================================
    
    # Gestiona la ruta del ejecutable del editor de código (ej. VS Code) para abrir los ejercicios.

    def get_ide_path(self) -> str:
        return self.data["config"].get("ide_path", "")

    def set_ide_path(self, path: str) -> None:
        self.data["config"]["ide_path"] = path
        self.save_data()
        
    # =================================================
    # GESTIÓN ÚLTIMO DIRECTORIO (LAST OPEN DIR)
    # =================================================
    
    # Recuerda la última carpeta que el usuario abrió para que, al reiniciar la app, el diálogo de "Abrir" comience allí.

    def get_last_open_dir(self) -> str:
        """Devuelve la última ruta abierta o el directorio home si no existe."""
        path = self.data["config"].get("last_open_dir", "")
        if path and os.path.exists(path):
            return path
        return os.path.expanduser("~")

    def set_last_open_dir(self, path: str) -> None:
        """Guarda la ruta del directorio para futuras sesiones."""
    # Guardamos el directorio padre si es un archivo, o el mismo si es carpeta.
        if os.path.isfile(path):
            path = os.path.dirname(path)
        self.data["config"]["last_open_dir"] = path
        self.save_data()
        
    # =================================================
    # CONFIGURACIÓN GENÉRICA (GET/SET SETTING)
    # =================================================
    
    # Métodos auxiliares para guardar cualquier par clave-valor en la configuración.

    def get_setting(self, key: str, default: Any = None) -> Any:
        """Recupera un valor arbitrario de la configuración."""
        return self.data["config"].get(key, default)

    def set_setting(self, key: str, value: Any) -> None:
        """Guarda un valor arbitrario en la configuración."""
        self.data["config"][key] = value
        self.save_data()

    # =================================================
    # GESTIÓN DIRECTORIO DE TRABAJO (WORK DIR)
    # =================================================
    
    # Gestiona la carpeta donde el usuario quiere copiar y realizar sus ejercicios.
    
    def get_work_dir(self) -> str:
        """Devuelve la ruta del directorio de trabajo del usuario."""
        return self.data["config"].get("work_dir", "")

    def set_work_dir(self, path: str) -> None:
        """Guarda la ruta del directorio de trabajo."""
        self.data["config"]["work_dir"] = path
        self.save_data()

    # =================================================
    # PERSISTENCIA DE VENTANA (GEOMETRÍA)
    # =================================================
    
    # Guarda y recupera el tamaño y posición de la ventana principal.
    
    def set_window_geometry(self, geometry_hex: str) -> None:
        self.data["config"]["window_geometry"] = geometry_hex
        self.save_data()

    def get_window_geometry(self) -> str:
        return self.data["config"].get("window_geometry", "")

    # =================================================
    # PERSISTENCIA DE PANELES (SPLITTERS)
    # =================================================
    
    # Guarda y recupera la posición de las barras divisorias (paneles ajustables).
    
    def set_splitter_state(self, splitter_name: str, state_hex: str) -> None:
        if "ui_states" not in self.data["config"]:
            self.data["config"]["ui_states"] = {}
        self.data["config"]["ui_states"][splitter_name] = state_hex
        self.save_data()

    def get_splitter_state(self, splitter_name: str) -> str:
        if "ui_states" not in self.data["config"]:
            return ""
        return self.data["config"]["ui_states"].get(splitter_name, "")

    # =================================================
    # LÓGICA DE CURSOS (MÉTODOS PRIVADOS)
    # =================================================
    
    # Genera claves únicas para identificar cada curso y asegura que existan en la BD (.JSON).

    def _get_course_key(self, course_path: str) -> str:
        return os.path.abspath(course_path)

    def _ensure_course_exists(self, course_path: str) -> str:
        key = self._get_course_key(course_path)
        if key not in self.data["courses"]:
            self.data["courses"][key] = {
                "history": [], 
                "notes": {},
                "tests": {}
            }
        return key

    # =================================================
    # GESTIÓN DE VIDEO COMPLETADO
    # =================================================
    
    # Verifica o marca si un video específico ha sido visto (check verde).
    
    def is_video_completed(self, course_path: str, rel_video_path: str) -> bool:
        key = self._get_course_key(course_path)
        if key not in self.data["courses"]:
            return False
        return rel_video_path in self.data["courses"][key]["history"]

    def set_video_completed(self, course_path: str, rel_video_path: str, completed: bool) -> None:
        key = self._ensure_course_exists(course_path)
        history_list = self.data["courses"][key]["history"]
        
        if completed:
            if rel_video_path not in history_list:
                history_list.append(rel_video_path)
        else:
            if rel_video_path in history_list:
                history_list.remove(rel_video_path)
        self.save_data()

    # =================================================
    # GESTIÓN DE APUNTES (NOTES)
    # =================================================
    
    # Guarda o recupera el texto de los apuntes para un video específico.

    def get_notes(self, course_path: str, rel_video_path: str) -> str:
        key = self._get_course_key(course_path)
        if key not in self.data["courses"]:
            return ""
        return self.data["courses"][key]["notes"].get(rel_video_path, "")

    def set_notes(self, course_path: str, rel_video_path: str, text: str) -> None:
        key = self._ensure_course_exists(course_path)
        self.data["courses"][key]["notes"][rel_video_path] = text
        self.save_data()

    # =================================================
    # GESTIÓN DE TEST Y EVALUACIONES
    # =================================================
    
    # Recupera el historial de exámenes y añade nuevos intentos.

    def get_test_history(self, course_path: str, test_name: str) -> List[Dict[str, Any]]:
        key = self._get_course_key(course_path)
        if key not in self.data["courses"]:
            return []
        return self.data["courses"][key]["tests"].get(test_name, [])
    
    # Registra el resultado de una evaluación realizada por el usuario.
    
    def add_test_attempt(self, course_path: str, test_name: str, attempt_data: Dict[str, Any]) -> None:
        key = self._ensure_course_exists(course_path)
        if test_name not in self.data["courses"][key]["tests"]:
            self.data["courses"][key]["tests"][test_name] = []
        
        self.data["courses"][key]["tests"][test_name].append(attempt_data)
        self.save_data()

    # =================================================
    # GESTIÓN DE DATOS (RESET Y LIMPIEZA)
    # =================================================
    
    # Funciones para borrar apuntes, historial o reiniciar la app de fábrica.

    # Borra/limpia todos los apuntes que ha realizado el usuario.
    def clear_all_notes(self) -> None:
        for course_key in self.data["courses"]:
            self.data["courses"][course_key]["notes"] = {}
        self.save_data()

    # Borra/limpia todo el historial de vídeos/audios completados que ha realizado el usuario.
    def clear_all_history(self) -> None:
        for course_key in self.data["courses"]:
            self.data["courses"][course_key]["history"] = []
        self.save_data()

    # Borra/limpia todo el historial de puntajes de evaluaciones que ha realizado el usuario.
    def clear_all_tests(self) -> None:
        for course_key in self.data["courses"]:
            self.data["courses"][course_key]["tests"] = {}
        self.save_data()

    # Borra/limpia todo los datos almacenados en USER_DATA.DATA.
    def reset_all_data(self) -> None:
        current_theme = self.get_theme()
        self.data = {
            "config": {"theme": current_theme, "ide_path": ""},
            "courses": {}
        }
        self.save_data()
    
    