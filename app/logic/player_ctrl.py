"""
Función: Controlador del reproductor VLC.

Es un "wrapper" (envoltorio) para la librería python-vlc. Simplifica comandos como
play(), pause(), stop(), controlar volumen y velocidad. Tiene un reloj interno para
avisar a la interfaz cómo avanza el video.

"""

# =================================================
# IMPORTACIONES NECESARIAS
# =================================================

import sys
import vlc
from PyQt6.QtCore import QObject, QTimer, pyqtSignal
from PyQt6.QtWidgets import QWidget


# ============================================================
# CLASE PLAYERCONTROLLER (CONTROLADOR PRINCIPAL VLC)
# ============================================================

# Controlador lógico principal. Encapsula la instancia vlc.MediaPlayer, maneja el bucle de eventos/tiempo y emite señales de PyQt6 para que la UI se actualice reactivamente (barra de progreso, tiempo, etc.).

class PlayerController(QObject):
    
    # Señales para la UI
    
    # Emite (tiempo_actual_ms, duracion_total_ms)
    time_changed = pyqtSignal(int, int)
    # Emite (float entre 0.0 y 1.0) para la barra de progreso
    position_changed = pyqtSignal(float)
    # Emite cuando el estado de reproducción cambia (True=Playing, False=Paused/Stopped)
    play_state_changed = pyqtSignal(bool)
    # Emite cuando el video finaliza (End of Stream)
    finished = pyqtSignal()
    # Emite la velocidad actual (ej: 1.0, 1.5)
    rate_changed = pyqtSignal(float)

    # =================================================
    # CONSTRUCTOR (__INIT__)
    # =================================================
    
    # Inicializa la instancia de VLC, configura el timer interno para actualizaciones (polling) y prepara las variables de estado.
    
    def __init__(self):
        super().__init__()
        self._instance = vlc.Instance()
        self._player = self._instance.media_player_new()
        
        # Configuraciones base de VLC para evitar conflictos con la UI
        self._player.video_set_mouse_input(False)
        self._player.video_set_key_input(False)

        # Timer interno para consultar el estado de VLC (Polling)
        self._timer = QTimer(self)
        self._timer.setInterval(200) # Actualizar cada 200ms
        self._timer.timeout.connect(self._update_state)
        
        # Estado interno
        self._is_finished_emitted = False
        
    # ==============================================================
    # VINCULACIÓN DE SALIDA DE VIDEO (SET_VIDEO_OUTPUT)
    # ==============================================================
    
    # Conecta el reproductor VLC con un widget de PyQt (normalmente un QFrame negro) utilizando el identificador de ventana (winId) del sistema operativo.
    
    def set_video_output(self, widget: QWidget):
        """Asocia el reproductor VLC al ID de ventana (handle) del Widget negro."""
        win_id = int(widget.winId())
        
        if sys.platform.startswith("linux"):
            self._player.set_xwindow(win_id)
        elif sys.platform.startswith("win"):
            self._player.set_hwnd(win_id)
        elif sys.platform.startswith("darwin"):
            self._player.set_nsobject(win_id)

    # =================================================
    # CARGAR MEDIO (LOAD_MEDIA)
    # =================================================
    
    # Prepara un archivo de video o audio para ser reproducido.
    # Reinicia los estados internos de finalización.
    
    def load_media(self, file_path: str):
        """Carga un archivo de video/audio."""
        media = self._instance.media_new(file_path)
        self._player.set_media(media)
        self._is_finished_emitted = False
        
    # ===================================================================
    # CONTROLES DE REPRODUCCIÓN (PLAY, PAUSE, STOP)
    # ===================================================================

    # Inicia la reproducción y arranca el timer de actualización de la barra de progreso.
    
    def play(self):
        if not self._player.get_media():
            return
        
        if self._player.play() == -1:
            print("Error al iniciar reproducción VLC")
            return
            
        self._timer.start()
        self.play_state_changed.emit(True)
        
    # Pausa el video manteniendo la posición actual.
    def pause(self):
        self._player.pause()
        self.play_state_changed.emit(False)

    # Alterna entre reproducir y pausar dependiendo del estado actual.
    def toggle_play_pause(self):
        if self.is_playing():
            self.pause()
        else:
            self.play()
            
    # Detiene el video por completo, reinicia el timer y resetea la barra de progreso a cero.
    def stop(self):
        self._player.stop()
        self._timer.stop()
        self.play_state_changed.emit(False)
        # Resetear UI
        self.time_changed.emit(0, 0)
        self.position_changed.emit(0.0)
        
    # Devuelve True si el video se está reproduciendo activamente.
    def is_playing(self) -> bool:
        return self._player.is_playing() == 1
    
    # =================================================
    # NAVEGACIÓN Y AUDIO (SEEK, VOLUME, RATE)
    # =================================================

    # Mueve el video a una posición específica (valor flotante de 0.0 a 1.0). Establece la posición absoluta (0.0 a 1.0) desde la barra de progreso.
    def set_position(self, pos: float):
        # VLC a veces falla si el media no está parseado, proteccion simple.
        if self._player.get_media():
            self._player.set_position(pos)

    # Salta hacia adelante o atrás una cantidad de milisegundos (ej: +5s, -5s).
    def seek_relative(self, offset_ms: int):
        current = self._player.get_time()
        if current == -1: 
            return
        
        new_time = max(0, current + offset_ms)
        self._player.set_time(new_time)
        
    # Ajusta el volumen del audio (0-100) (Nota: VLC permite valores mayores a 100)
    def set_volume(self, volume: int):
        self._player.audio_set_volume(volume)

    def get_volume(self) -> int:
        return self._player.audio_get_volume()

    # Cambia la velocidad de reproducción (ej: 1.5x, 2.0x).
    def set_rate(self, rate: float):
        if self._player.set_rate(rate) == 0:
            self.rate_changed.emit(rate)

    def get_rate(self) -> float:
        return self._player.get_rate()

    # =================================================
    # ACTUALIZACIÓN DE ESTADO (BUCLE INTERNO)
    # =================================================
    
    # Método llamado periódicamente por QTimer (cada 200ms).
    # Consulta a VLC el tiempo actual y emite las señales para actualizar la UI.
    
    def _update_state(self):
        # 1. Verificar si terminó
        if self._player.get_state() == vlc.State.Ended:
            if not self._is_finished_emitted:
                self._is_finished_emitted = True
                self.stop() # Detener timer interno
                self.finished.emit()
            return

        self._is_finished_emitted = False

        # 2. Emitir tiempo y posición para la barra
        current_ms = self._player.get_time()
        total_ms = self._player.get_length()
        position = self._player.get_position()

        if current_ms >= 0:
            self.time_changed.emit(current_ms, total_ms)
            self.position_changed.emit(position)