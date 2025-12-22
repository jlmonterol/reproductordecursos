"""
Función: Motor del Pomodoro.

Un temporizador lógico. Cuenta el tiempo, controla los estados
(Trabajo -> Descanso Corto -> Descanso Largo) y emite señales
cuando el tiempo termina.

"""

# =================================================
# IMPORTACIONES NECESARIAS
# =================================================

from PyQt6.QtCore import QObject, QTimer, pyqtSignal

# =================================================
# CLASE POMODOROTIMER (LÓGICA DEL TEMPORIZADOR)
# =================================================

# Maneja la lógica de negocio de la técnica Pomodoro.
# Controla los ciclos de Estudio, Descanso Corto y Descanso Largo.
# Soporta pausa, reanudación y notificaciones de cambio de fase.

class PomodoroTimer(QObject):

    # Señales
    tick = pyqtSignal(str, str)  # (texto_tiempo, color_hex)
    phase_changed = pyqtSignal(str, bool) # (nombre_fase, es_trabajo)
    finished = pyqtSignal()      # Secuencia completa terminada
    stopped = pyqtSignal()       # Detenido manuelmente
    paused_status = pyqtSignal(bool)    # Estado de pausa (True=Pausado, False=Corriendo)

    # =================================================
    # CONSTRUCTOR (__INIT__)
    # =================================================

    def __init__(self):
        super().__init__()
        self._timer = QTimer()
        self._timer.setInterval(1000) # 1 segundo
        self._timer.timeout.connect(self._on_timeout)
        
        self.is_running = False
        self.is_paused = False
        
        # Configuración interna (Valores en minutos)
        self._study_min = 25
        self._short_break_min = 5
        self._long_break_min = 30
        self._total_cycles = 4
        
        # Estado interno
        self._current_cycle = 1
        self._seconds_left = 0
        self._state = "IDLE" 
        self._last_label_text = ""
        self._last_color = "#000000"
    
    # =================================================
    # INICIO DE SECUENCIA (START)
    # =================================================
    
    # Configura los tiempos personalizados e inicia el primer ciclo de trabajo.

    def start_sequence(self, study, short_brk, cycles, long_brk):
        self._study_min = study
        self._short_break_min = short_brk
        self._total_cycles = cycles
        self._long_break_min = long_brk
        
        self._current_cycle = 1
        self.is_running = True
        self.is_paused = False
        self._start_work()

    # =================================================
    # CONTROL DE PAUSA / REANUDAR (PAUSE/RESUME)
    # =================================================

    # Pausa el temporizador congelando el tiempo restante.
    def pause(self):
        if self.is_running and not self.is_paused:
            self._timer.stop()
            self.is_paused = True
            self.paused_status.emit(True)

    # Reanuda el temporizador desde el segundo exacto donde quedó.
    def resume(self):
        if self.is_running and self.is_paused:
            self._timer.start()
            self.is_paused = False
            self.paused_status.emit(False)
            # Emitir tick inmediato para restaurar texto
            self.tick.emit(self._last_label_text, self._last_color)

    # Alterna entre pausar y reanudar (útil para un solo botón).
    def toggle(self):
        if self.is_paused:
            self.resume()
        else:
            self.pause()

    # Detiene el timer manualmente y resetea todo a estado inicial.
    def stop(self):
        self._timer.stop()
        self.is_running = False
        self.is_paused = False
        self._state = "IDLE"
        self.tick.emit("", "#000000") 
        self.stopped.emit()

    # =================================================
    # MÉTODOS PRIVADOS DE GESTIÓN DE FASES
    # =================================================
    
    # Estos métodos configuran internamente cada etapa del ciclo Pomodoro.

    def _start_work(self):
        self._state = "WORK"
        self._seconds_left = self._study_min * 60
        self._emit_tick()
        self._timer.start()

    def _start_short_break(self):
        self._state = "SHORT_BREAK"
        self._seconds_left = self._short_break_min * 60
        self._emit_tick()
        self._timer.start()

    def _start_long_break(self):
        self._state = "LONG_BREAK"
        self._seconds_left = self._long_break_min * 60
        self._emit_tick()
        self._timer.start()
        
    # =================================================
    # EVENTO DE TIEMPO (TICK)
    # =================================================
    
    # Se ejecuta cada segundo. Resta tiempo y verifica si la fase terminó.

    def _on_timeout(self):
        if self._seconds_left > 0:
            self._seconds_left -= 1
            self._emit_tick()
        else:
            self._timer.stop()
            self._next_phase()
    
    # =================================================
    # TRANSICIÓN DE FASES (_NEXT_PHASE)
    # =================================================
    
    # Decide qué sigue al terminar un contador: ¿Descanso? ¿Trabajo? ¿Fin?

    def _next_phase(self):
        if self._state == "WORK":
            self.phase_changed.emit(f"Fin del Pomodoro {self._current_cycle}", True)
            if self._current_cycle < self._total_cycles:
                self._start_short_break()
            else:
                self._start_long_break()
        elif self._state == "SHORT_BREAK":
            self.phase_changed.emit("Fin del Descanso", False)
            self._current_cycle += 1
            self._start_work()
        elif self._state == "LONG_BREAK":
            self.is_running = False
            self.finished.emit()
    
    # =================================================
    # EMISIÓN DE SEÑAL TICK (_EMIT_TICK)
    # =================================================
    
    # Formatea el tiempo (MM:SS) y define el color según la fase (Rojo=Trabajo, Verde=Descanso).

    def _emit_tick(self):
        mins = self._seconds_left // 60
        secs = self._seconds_left % 60
        time_str = f"{mins:02d}:{secs:02d}"
        
        if self._state == "WORK":
            label_text = f"Pomodoro ({self._current_cycle}/{self._total_cycles}): {time_str}"
            color = "#aa0000" 
        elif self._state == "SHORT_BREAK":
            label_text = f"Descanso: {time_str}"
            color = "#00aa00" 
        elif self._state == "LONG_BREAK":
            label_text = f"Descanso Final: {time_str}"
            color = "#00aa00" 
        else:
            label_text = ""
            color = "#000000"
        
        self._last_label_text = label_text
        self._last_color = color
        self.tick.emit(label_text, color)