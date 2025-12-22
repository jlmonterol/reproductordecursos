"""
Función: Ventana dpara configurar los tiempos del temporizador Pomodoro (estudio, descanso, ciclos).

"""

# =================================================
# IMPORTACIONES NECESARIAS
# =================================================

from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QSpinBox, QPushButton, QCheckBox, QFrame)
from PyQt6.QtCore import Qt

# =================================================
# CLASE POMODORODIALOG (CONFIGURACIÓN TIMER)
# =================================================

# Diálogo modal para ajustar los tiempos de estudio y descanso.
# También permite Pausar, Reanudar o Detener el timer si ya está corriendo.

class PomodoroDialog(QDialog):
    
    # =================================================
    # CONSTRUCTOR (__INIT__)
    # =================================================
    
    def __init__(self, parent=None, dark_mode=False, is_running=False):
        super().__init__(parent)
        self.dark_mode = dark_mode
        self.is_running = is_running
        self.result_data = None
        self.stop_requested = False
        self.setup_ui()

    # =================================================
    # CONFIGURACIÓN DE INTERFAZ (SETUP_UI)
    # =================================================

    def setup_ui(self):
        self.setWindowTitle("Configurar Pomodoro")
        self.setFixedWidth(320)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint)

        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        # 1. Minutos Estudio
        self.spin_study = self._create_row(layout, "Minutos de Estudio:", 25)
        
        # 2. Minutos Descanso
        self.spin_short = self._create_row(layout, "Minutos de Descanso:", 5)
        
        # 3. Cantidad Ciclos
        self.spin_cycles = self._create_row(layout, "Cantidad de Ciclos:", 4)
        
        # 4. Descanso Final
        self.spin_long = self._create_row(layout, "Descanso Final:", 30)

        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        layout.addWidget(line)

        # 5. Checkbox Detener Reproducción
        self.chk_pause = QCheckBox("Detener reproducción al finalizar Pomodoro")
        self.chk_pause.setChecked(True)
        layout.addWidget(self.chk_pause)

        layout.addSpacing(10)

        # 6. Botones
        btn_layout = QHBoxLayout()
        
        # Botón dinámico (Iniciar o Pausar/Reanudar)
        btn_text = "Pausar / Reanudar" if self.is_running else "Iniciar"
        self.btn_start = QPushButton(btn_text)
        self.btn_start.setToolTip("Iniciar/Pausar Pomodoro. (F3)")
        self.btn_start.clicked.connect(self.on_start)
        
        self.btn_stop = QPushButton("Detener")
        self.btn_stop.setToolTip("Detiene Pomodoro. (F4)")
        self.btn_stop.clicked.connect(self.on_stop)
        # Solo habilitamos "Detener" si realmente hay algo corriendo
        self.btn_stop.setEnabled(self.is_running)
        
        self.btn_cancel = QPushButton("Cancelar")
        self.btn_cancel.clicked.connect(self.reject)

        btn_layout.addWidget(self.btn_start)
        btn_layout.addWidget(self.btn_stop)
        btn_layout.addWidget(self.btn_cancel)
        
        layout.addLayout(btn_layout)
        self.apply_styles()

    # =================================================
    # AUXILIAR CREAR FILA (_CREATE_ROW)
    # =================================================

    def _create_row(self, layout, text, default_val):
        h = QHBoxLayout()
        lbl = QLabel(text)
        spin = QSpinBox()
        spin.setRange(1, 120)
        spin.setValue(default_val)
        spin.setFixedWidth(70)

        # Si está corriendo, bloqueamos la edición de tiempos para no romper la lógica
        if self.is_running:
            spin.setEnabled(False)
        
        h.addWidget(lbl)
        h.addStretch()
        h.addWidget(spin)
        layout.addLayout(h)
        return spin

    # =================================================
    # SLOT BOTÓN INICIAR/ACEPTAR (ON_START)
    # =================================================

    def on_start(self):
        self.result_data = {
            "study": self.spin_study.value(),
            "short": self.spin_short.value(),
            "cycles": self.spin_cycles.value(),
            "long": self.spin_long.value(),
            "pause_video": self.chk_pause.isChecked()
        }
        self.accept()

    # =================================================
    # SLOT BOTÓN DETENER (ON_STOP)
    # =================================================

    def on_stop(self):
        self.stop_requested = True
        self.reject()

    # =================================================
    # APLICAR ESTILOS (APPLY_STYLES)
    # =================================================

    def apply_styles(self):
        if self.dark_mode:
            self.setStyleSheet("""
                QDialog { background-color: #353535; color: white; }
                QLabel, QCheckBox { color: white; }
                QSpinBox { background-color: #555; color: white; border: 1px solid #777; padding: 2px; }
                QPushButton { background-color: #444; color: white; border: 1px solid #666; padding: 5px; }
                QPushButton:hover { background-color: #555; }
            """)