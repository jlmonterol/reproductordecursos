"""
Función: El lienzo del video.

Es el cuadro negro donde VLC "pinta" el video. También maneja la lógica
para mostrar una imagen de fondo (día/noche :D) cuando se reproduce solo audio.

"""

# =================================================
# IMPORTACIONES NECESARIAS
# =================================================

import os
import datetime
from PyQt6.QtWidgets import QWidget, QLabel, QVBoxLayout
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QPixmap
from app.utils.paths import resource_path

# =================================================
# CLASE VIDEOWIDGET (LIENZO DE VIDEO)
# =================================================

# Widget inteligente que sirve de contenedor para la salida de VLC.
# Características principales:

# - Fondo negro por defecto.
# - Detección de clics para pausar/reproducir.
# - Modo Audio: Muestra una imagen de fondo (Día/Noche) si el archivo no tiene video.
# - Redimensionado automático de la imagen de fondo.

class VideoWidget(QWidget):
    # Señales para comunicar interacción del usuario
    clicked = pyqtSignal()
    doubleClicked = pyqtSignal()

    # =================================================
    # CONSTRUCTOR (__INIT__)
    # =================================================

    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Configuración visual base (Fondo Negro)
        self.setStyleSheet("background-color: black;")
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        
        # --- OVERLAY PARA MODO AUDIO --- #
        
        # Label interno que contendrá la imagen de fondo.
        # Se inicia oculto y se muestra solo cuando es un MP3/Audio.
        
        self._overlay_label = QLabel(self)
        self._overlay_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._overlay_label.setStyleSheet("background-color: black;")
        self._overlay_label.hide()
        self._is_audio_mode = False

    # =================================================
    # ACTIVAR MODO AUDIO (SET_AUDIO_MODE)
    # =================================================
    
    # Activa o desactiva la capa de imagen superpuesta.
    # Si es True, carga la imagen adecuada y la muestra sobre el video negro.

    def set_audio_mode(self, enabled: bool):
        self._is_audio_mode = enabled
        if enabled:
            self._update_overlay_image()
            self._overlay_label.show()
            self._overlay_label.raise_()
            self._fit_overlay()
        else:
            self._overlay_label.hide()

    # =================================================
    # ACTUALIZAR IMAGEN (_UPDATE_OVERLAY_IMAGE)
    # =================================================
    
    # Decide qué imagen mostrar basándose en la hora actual del sistema.
    # Día (06:00 - 17:59) / Noche (18:00 - 05:59).

    def _update_overlay_image(self):
        current_hour = datetime.datetime.now().hour
        img_name = "BackgroundAudioImage_Day.png" if 6 <= current_hour < 18 else "BackgroundAudioImage_Night.png"
        path = resource_path(os.path.join("assets", "images", img_name))
        
        if os.path.exists(path):
            self._current_pixmap = QPixmap(path)
        else:
            self._current_pixmap = None

    # =================================================
    # AJUSTAR TAMAÑO OVERLAY (_FIT_OVERLAY)
    # =================================================
    # Escala la imagen cargada para que cubra todo el widget sin deformarse (mantiene relación de aspecto).

    def _fit_overlay(self):
        if not self._is_audio_mode or not self._overlay_label.isVisible():
            return
            
        # El label debe ocupar todo el espacio del widget contenedor
        self._overlay_label.resize(self.size())
        
        if hasattr(self, '_current_pixmap') and self._current_pixmap:
            # Escalado suave de la imagen
            scaled = self._current_pixmap.scaled(
                self.size(), 
                Qt.AspectRatioMode.KeepAspectRatio, 
                Qt.TransformationMode.SmoothTransformation
            )
            self._overlay_label.setPixmap(scaled)

    # =================================================
    # EVENTO DE REDIMENSIONADO (RESIZEEVENT)
    # =================================================
    
    # Se dispara automáticamente cuando el usuario cambia el tamaño de la ventana.
    # Asegura que la imagen de fondo se adapte al nuevo tamaño.

    def resizeEvent(self, event):
        if self._is_audio_mode:
            self._fit_overlay()
        super().resizeEvent(event)

    # =================================================
    # EVENTOS DE RATÓN (CLIC / DOBLE CLIC)
    # =================================================
    
    # Captura los clics sobre el área de video y emite señales personalizadas.

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.doubleClicked.emit()
        super().mouseDoubleClickEvent(event)