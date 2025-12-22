"""
Función: Operaciones de archivos del sistema.

Se encarga de copiar carpetas (para los ejercicios), crear copias
de seguridad (backups) y lanzar el editor de código (IDE, etc.).

"""

# =================================================
# IMPORTACIONES NECESARIAS
# =================================================

import os
import shutil
import datetime
import subprocess
import sys

# =================================================
# CLASE FILEMANAGER (GESTOR DE ARCHIVOS)
# =================================================

# Clase estática (sin estado) que agrupa utilidades para manipular archivos y carpetas.
# Se encarga de copiar ejercicios, crear backups seguros y abrir el IDE.

class FileManager:
    
    # =================================================
    # CALCULAR RUTA DESTINO (GET_WORK_TARGET_PATH)
    # =================================================
    
    # Genera la ruta completa donde se deben copiar los ejercicios, basada en la configuración del usuario y el capítulo actual.
    # Calcula la ruta de destino: WorkDir / NombreCurso / NombreCapítulo
    
    @staticmethod
    def get_work_target_path(work_dir_root: str, course_path: str, chapter_dir_path: str) -> str:
        if not work_dir_root or not os.path.exists(work_dir_root):
            return None

        course_name = os.path.basename(course_path)
        chapter_name = os.path.basename(chapter_dir_path)
        return os.path.join(work_dir_root, course_name, chapter_name)

    # =================================================
    # VERIFICAR SI DESTINO EXISTE (TARGET_EXISTS...)
    # =================================================
    
    # Comprueba si una carpeta ya existe y si tiene archivos dentro, para evitar sobrescribir trabajo del usuario accidentalmente.

    @staticmethod
    def target_exists_and_not_empty(target_path: str) -> bool:
        return os.path.exists(target_path) and len(os.listdir(target_path)) > 0

    # =================================================
    # CREAR RESPALDO (CREATE_BACKUP)
    # =================================================
    
    # Renombra una carpeta existente agregándole una fecha y hora (timestamp) para guardarla como copia de seguridad antes de una nueva copia.

    @staticmethod
    def create_backup(target_path: str) -> str:
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"{os.path.basename(target_path)}_BACKUP_{timestamp}"
        backup_path = os.path.join(os.path.dirname(target_path), backup_name)
        os.rename(target_path, backup_path)
        return backup_name

    # =================================================
    # COPIAR CONTENIDO (COPY_DIRECTORY_CONTENT)
    # =================================================
    
    # Realiza la copia física de archivos y subcarpetas desde el curso original hacia la carpeta de trabajo del usuario.

    @staticmethod
    def copy_directory_content(source: str, destination: str):
        # Aseguramos que el destino exista (os.rename pudo haberlo movido antes)
        os.makedirs(destination, exist_ok=True)
        
        for item in os.listdir(source):
            s = os.path.join(source, item)
            d = os.path.join(destination, item)
            if os.path.isdir(s):
                shutil.copytree(s, d, dirs_exist_ok=True)
            else:
                shutil.copy2(s, d)
                
    # =================================================
    # ABRIR EN IDE (OPEN_IN_IDE)
    # =================================================
    
    # Intenta abrir una carpeta con el editor de código configurado (ej. VS Code).
    # Si no hay configuración, intenta usar el comando 'code' por defecto.

    @staticmethod
    def open_in_ide(path: str, ide_path_config: str = ""):
        cmds = []
        if ide_path_config: 
            cmds.append(ide_path_config)
        cmds.append("code") # VS Code default

        use_shell = (sys.platform == "win32")

        for cmd in cmds:
            try:
                subprocess.Popen([cmd, path], shell=use_shell)
                return True
            except (FileNotFoundError, OSError):
                continue
        return False