"""
Función: Motor de exámenes.

Carga un examen (.test), muestra las preguntas, valida las respuestas,
calcula el puntaje y muestra el resultado final.

"""

# =================================================
# IMPORTACIONES NECESARIAS
# =================================================

import os
import datetime
import random
from typing import Dict, List, Any, Optional

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QFrame, QTextEdit, QRadioButton, QButtonGroup, 
    QWidget, QMessageBox, QTableWidget, QTableWidgetItem, 
    QHeaderView, QSizePolicy, QScrollArea
)
from PyQt6.QtCore import Qt, QSize, QByteArray
from PyQt6.QtGui import QIcon, QFont, QPalette, QColor

from app.utils.paths import resource_path
from app.data.data_manager import DataManager

try:
    import vlc
except ImportError:
    vlc = None
    
# =================================================
# CLASE TESTEVALUATIONDIALOG (MOTOR DE EXÁMENES)
# =================================================


# Gestiona el ciclo completo de una evaluación:
# - Carga preguntas (aleatorias o fijas).
# - Muestra interfaz pregunta a pregunta.
# - Valida respuestas y muestra feedback.
# - Calcula puntaje final y guarda historial.

class TestEvaluationDialog(QDialog):
    
    # =================================================
    # CONSTRUCTOR (__INIT__)
    # =================================================
    
    def __init__(self, parent, test_data: Dict[str, Any], data_manager: DataManager, 
                 course_path: str, test_name: str, dark_mode_enabled: bool = False):
        super().__init__(parent)
        
        self.test_data = test_data
        self.data_manager = data_manager
        self.course_path = course_path
        self.test_name = test_name
        self.display_name = test_name or test_data.get("title") or "Test"
        self.dark_mode_enabled = dark_mode_enabled

        self.runtime_questions = self._build_runtime_questions()
        
        self.question_states = [
            {"selected_index": None, "checked": False, "correct": False}
            for _ in self.runtime_questions
        ]
        self.current_index = 0
        
        self.history_attempts = 0
        self.history_best_percent: Optional[float] = None
        self._load_history_local()

        self._sound_player = None 
        if vlc:
            self._vlc_instance = vlc.Instance()
            self._sound_player = self._vlc_instance.media_player_new()

        self.setup_ui()
        self._update_history_ui()
        self._load_current_question()
        
    # =================================================================
    # CONSTRUCCIÓN DE PREGUNTAS (_BUILD_RUNTIME_QUESTIONS)
    # =================================================================
    
    # Procesa las preguntas crudas: aplica aleatoriedad (shuffle) si está activada y selecciona la cantidad configurada para el examen.

    def _build_runtime_questions(self) -> List[Dict]:
        questions = self.test_data.get("questions", [])
        num_to_run = self.test_data.get("num_questions_to_run", len(questions))
        
        indices = list(range(len(questions)))
        if self.test_data.get("random_questions"):
            random.shuffle(indices)
        selected_indices = indices[:num_to_run]
        
        runtime_qs = []
        for idx in selected_indices:
            q = questions[idx]
            answers = list(q["answers"])
            correct_idx_original = q["correct_index"]
            
            if self.test_data.get("random_answers"):
                indexed_answers = list(enumerate(answers))
                random.shuffle(indexed_answers)
                answers = [text for _, text in indexed_answers]
                new_correct_idx = 0
                for i, (original_idx, _) in enumerate(indexed_answers):
                    if original_idx == correct_idx_original:
                        new_correct_idx = i
                        break
                
                q_copy = q.copy()
                q_copy["answers"] = answers
                q_copy["correct_index"] = new_correct_idx
                runtime_qs.append(q_copy)
            else:
                runtime_qs.append(q)
                
        return runtime_qs
    
    # =================================================
    # CARGA DE HISTORIAL (_LOAD_HISTORY_LOCAL)
    # =================================================

    def _load_history_local(self):
        attempts = self.data_manager.get_test_history(self.course_path, self.test_name)
        self.history_attempts = len(attempts)
        if attempts:
            self.history_best_percent = max(a["percent"] for a in attempts)
            
    # =================================================
    # CONFIGURACIÓN DE INTERFAZ (SETUP_UI)
    # =================================================

    def setup_ui(self):
        self.setWindowTitle("Test/Evaluación de Conocimiento (Reproductor de Cursos)")
        
        # --- LÓGICA DE RESTAURACIÓN DE GEOMETRÍA --- #
        
        saved_geometry = self.data_manager.get_setting("TestEvaluationDialog/geometry", None) # Restaurar geometría guardada
        geometry_restored = False
        
        if saved_geometry:
            try:
                if isinstance(saved_geometry, str):
                    geo_bytes = QByteArray.fromHex(saved_geometry.encode('utf-8'))
                    if not geo_bytes.isEmpty():
                        self.restoreGeometry(geo_bytes)
                        geometry_restored = True
            except Exception as e:
                print(f"Error restaurando geometría: {e}")

        # Si no se restauró (primera vez), usar tamaño por defecto.
        if not geometry_restored:
            self.resize(900, 960) # Primer valor es ancho, segundo alto.
        # -------------------------------------------

        self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint)

        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(5)
        main_layout.setContentsMargins(10, 10, 10, 10)

        # 1. HEADER (Botón Historial).
        
        header_row = QHBoxLayout()
        
        self.historyButton = QPushButton(" Historial")
        self.historyButton.setToolTip("Ver historial de intentos de esta evaluación.")
        self.historyButton.setCursor(Qt.CursorShape.PointingHandCursor)
        self.historyButton.setFixedWidth(90)
        self.historyButton.clicked.connect(self.show_history_dialog)
        
        suffix = "_dark.svg" if self.dark_mode_enabled else "_light.svg"
        icon_path = resource_path(os.path.join("assets", "images", f"history{suffix}"))
        if os.path.exists(icon_path):
            self.historyButton.setIcon(QIcon(icon_path))

        header_row.addWidget(self.historyButton)
        
        self.historyLabel = QLabel("")
        self.historyLabel.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.historyLabel.setStyleSheet("font-size: 10pt;")
        header_row.addWidget(self.historyLabel, 1)
        
        main_layout.addLayout(header_row)

        # 2. TÍTULO Y CONTADOR.
        
        self.titleLabel = QLabel(f">>>  >  {self.display_name}  <  <<<")
        self.titleLabel.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.titleLabel.setStyleSheet("font-size: 18px; font-weight: bold; margin: 0px;")
        main_layout.addWidget(self.titleLabel)

        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        main_layout.addWidget(line)

        self.counterLabel = QLabel("")
        self.counterLabel.setAlignment(Qt.AlignmentFlag.AlignCenter)
        # self.counterLabel.setStyleSheet("font-weight: bold; font-size: 12pt; margin-bottom: 5px;")
        self.counterLabel.setStyleSheet("font-weight: bold; font-size: 12pt; margin-top: 20px; margin-bottom: 5px;")
        main_layout.addWidget(self.counterLabel)

        # 3. ZONA DE CONTENIDO SCROLLABLE.
        
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        
        self.scroll_content_widget = QWidget()
        self.scroll_content_layout = QVBoxLayout(self.scroll_content_widget)
        
        self.scroll_content_layout.setContentsMargins(5, 0, 15, 0)
        self.scroll_content_layout.setSpacing(15)
        self.scroll_content_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # A. Texto Pregunta.
        
        self.qTextLabel = QLabel("")
        self.qTextLabel.setWordWrap(True)
        self.qTextLabel.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.qTextLabel.setStyleSheet("""
            font-size: 13pt; 
            border: 1px solid #888; 
            padding: 15px; 
            background-color: palette(base); 
            border-radius: 6px;
        """)
        self.qTextLabel.setMinimumHeight(80)
        self.scroll_content_layout.addWidget(self.qTextLabel)

        # Separador Pregunta.
        sep_q = QFrame()
        sep_q.setFrameShape(QFrame.Shape.HLine)
        sep_q.setFrameShadow(QFrame.Shadow.Sunken)
        sep_q.setStyleSheet("color: #999;")
        self.scroll_content_layout.addWidget(sep_q)

        # B. Contenedor Respuestas.
        
        self.answersContainer = QWidget()
        self.answersLayout = QVBoxLayout(self.answersContainer)
        self.answersLayout.setContentsMargins(5, 5, 5, 5)
        self.answersLayout.setSpacing(15)
        
        self.scroll_content_layout.addWidget(self.answersContainer)

        # 4. ÁREA DE FEEDBACK (Retroalimentación).
        
        self.feedbackContainer = QWidget()
        self.feedbackContainer.setMinimumHeight(170)
        
        fb_layout = QVBoxLayout(self.feedbackContainer)
        fb_layout.setContentsMargins(0, 0, 0, 0) 
        fb_layout.setSpacing(0) 
        
        # Header Feedback.
        fb_header = QHBoxLayout()
        fb_header.setContentsMargins(0, 10, 0, 2)
        fb_header.setAlignment(Qt.AlignmentFlag.AlignBottom) 
        
        # Izquierda: Título Explicación.
        self.explLabel = QLabel("Explicación de Pregunta/Respuesta:")
        self.explLabel.setStyleSheet("font-weight: bold; font-size: 12pt;")
        self.explLabel.setVisible(False)
        fb_header.addWidget(self.explLabel)
        
        fb_header.addStretch()
        
        # Derecha: Resultado.
        self.feedbackLabel = QLabel("")
        self.feedbackLabel.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignBottom)
        fb_header.addWidget(self.feedbackLabel)
        
        fb_layout.addLayout(fb_header)

        # Texto Explicación.
        self.explText = QTextEdit()
        self.explText.setReadOnly(True)
        self.explText.setFixedHeight(100) 
        self.explText.setStyleSheet("font-size: 12pt; border: 1px solid #777; padding: 5px;")
        self.explText.setVisible(False)
        fb_layout.addWidget(self.explText)
        
        fb_layout.addStretch()

        self.scroll_content_layout.addWidget(self.feedbackContainer)
        
        self.scroll_area.setWidget(self.scroll_content_widget)
        main_layout.addWidget(self.scroll_area)

        # --- ÁREA RESUMEN FINAL ---
        
        self.summaryArea = QWidget()
        self.summaryArea.setVisible(False)
        sa_layout = QVBoxLayout(self.summaryArea)
        
        lbl_sum = QLabel("Resumen de la Evaluación")
        lbl_sum.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_sum.setStyleSheet("font-size: 18px; font-weight: bold;")
        sa_layout.addWidget(lbl_sum)
        
        self.scoreLabel = QLabel()
        self.scoreLabel.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sa_layout.addWidget(self.scoreLabel)
        
        self.msgLabel = QLabel()
        self.msgLabel.setWordWrap(True)
        self.msgLabel.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sa_layout.addWidget(self.msgLabel)
        
        h_det_labels = QHBoxLayout()
        lbl_cor = QLabel("Respuestas Correctas:")
        lbl_cor.setStyleSheet("font-weight: bold;")
        lbl_inc = QLabel("Respuestas Incorrectas:")
        lbl_inc.setStyleSheet("font-weight: bold;")
        h_det_labels.addWidget(lbl_cor)
        h_det_labels.addWidget(lbl_inc)
        sa_layout.addLayout(h_det_labels)

        # Text areas para resumen
        h_det_text = QHBoxLayout()
        self.correctText = QTextEdit()
        self.correctText.setReadOnly(True)
        self.incorrectText = QTextEdit()
        self.incorrectText.setReadOnly(True)
        h_det_text.addWidget(self.correctText)
        h_det_text.addWidget(self.incorrectText)
        sa_layout.addLayout(h_det_text)
        
        self.finalMsgLabel = QLabel("Mensaje final de la Evaluación:")
        self.finalMsgLabel.setStyleSheet("font-weight: bold;")
        sa_layout.addWidget(self.finalMsgLabel)

        self.finalMsgText = QTextEdit()
        self.finalMsgText.setFixedHeight(90)
        self.finalMsgText.setReadOnly(True)
        self.finalMsgText.setStyleSheet("font-size: 13pt;")
        sa_layout.addWidget(self.finalMsgText)
        
        main_layout.addWidget(self.summaryArea)

        # --- BOTONES INFERIORES --- #
        
        line_bot = QFrame()
        line_bot.setFrameShape(QFrame.Shape.HLine)
        line_bot.setFrameShadow(QFrame.Shadow.Sunken)
        main_layout.addWidget(line_bot)

        btns_layout = QHBoxLayout()
        btns_layout.addStretch()
        
        self.prevBtn = QPushButton("Anterior pregunta")
        self.prevBtn.setFixedWidth(140)
        self.prevBtn.clicked.connect(self._on_prev)
        
        self.checkBtn = QPushButton("Comprobar respuesta")
        self.checkBtn.setFixedWidth(160)
        self.checkBtn.setStyleSheet("font-weight: bold;")
        self.checkBtn.clicked.connect(self._on_check)
        
        self.nextBtn = QPushButton("Siguiente pregunta")
        self.nextBtn.setFixedWidth(140)
        self.nextBtn.clicked.connect(self._on_next)
        
        self.cancelBtn = QPushButton("Cancelar Evaluación")
        self.cancelBtn.setFixedWidth(160)
        self.cancelBtn.clicked.connect(self._on_cancel)
        
        btns_layout.addWidget(self.prevBtn)
        btns_layout.addWidget(self.checkBtn)
        btns_layout.addWidget(self.nextBtn)
        btns_layout.addWidget(self.cancelBtn)
        
        btns_layout.addStretch()
        main_layout.addLayout(btns_layout)
        
        self.answerGroup = None
        self.apply_styles()

    # =================================================
    # EVENTO DE CIERRE (DONE)
    # =================================================
    
    # Sobrescribe el cierre del diálogo para guardar la posición de la ventana.
    
    def done(self, result):
        # 1. Guardar Geometría (Tamaño y Posición).
        try:
            geo_hex = self.saveGeometry().toHex().data().decode('utf-8')
            self.data_manager.set_setting("TestEvaluationDialog/geometry", geo_hex)
        except Exception as e:
            print(f"Error guardando geometría del test: {e}")

        # 2. Detener sonido si está sonando.
        if self._sound_player and self._sound_player.is_playing():
            self._sound_player.stop()

        # 3. Llamar al método padre para cerrar efectivamente.
        super().done(result)

    # =================================================
    # ESTILOS (APPLY_STYLES)
    # =================================================

    def apply_styles(self):
        if self.dark_mode_enabled:
            self.setStyleSheet("""
                QDialog { background-color: #353535; color: white; }
                QLabel { color: white; }
                QPushButton { background-color: #444; color: white; border: 1px solid #666; padding: 6px; border-radius: 3px; font-size: 10pt; }
                QPushButton:hover { background-color: #555; }
                QPushButton:disabled { color: #888; border-color: #555; }
                QTextEdit { background-color: #222; color: white; border: 1px solid #555; }
                QRadioButton { color: white; font-size: 12pt; }
                QScrollArea { background-color: transparent; border: none; }
                QWidget#scrollContent { background-color: transparent; }
            """)
        else:
            self.setStyleSheet("""
                QRadioButton { font-size: 12pt; }
                QPushButton { padding: 6px; font-size: 10pt; }
                QScrollArea { background-color: transparent; border: none; }
            """)

    # =================================================
    # ACTUALIZAR UI HISTORIAL (_UPDATE_HISTORY_UI)
    # =================================================

    def _update_history_ui(self):
        if self.history_attempts == 0:
            self.historyButton.setEnabled(False)
            self.historyLabel.setText("La evaluación permanece sin realizarse hasta el momento.")
            self.historyLabel.setStyleSheet("font-size: 10pt; color: #777;")
        else:
            self.historyButton.setEnabled(True)
            best = self.history_best_percent or 0.0
            color = "#008000" if best >= 60.0 else "#cc0000"
            if self.dark_mode_enabled:
                color = "#44ff44" if best >= 60.0 else "#ff5555"
            self.historyLabel.setText(f"Historial: {self.history_attempts} intento(s) | Mejor puntaje: {best:.2f}%")
            self.historyLabel.setStyleSheet(f"color: {color}; font-weight: bold; font-size: 10pt;")

    # =================================================
    # LIMPIEZA RESPUESTAS (_CLEAR_ANSWERS)
    # =================================================

    def _clear_answers(self):
        while self.answersLayout.count():
            child = self.answersLayout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

    # =================================================
    # CARGAR PREGUNTA ACTUAL (_LOAD_CURRENT_QUESTION)
    # =================================================
    
    # Renderiza la pregunta y sus opciones de respuesta (RadioButtons).

    def _load_current_question(self):
        self._clear_answers()
        
        self.explLabel.setVisible(False)
        self.explText.setVisible(False)
        self.feedbackLabel.setText("")

        if not self.runtime_questions:
            self.counterLabel.setText("Error: No hay preguntas.")
            return

        q = self.runtime_questions[self.current_index]
        state = self.question_states[self.current_index]
        
        self.counterLabel.setText(f"Pregunta {self.current_index + 1} de {len(self.runtime_questions)}")
        self.qTextLabel.setText(q["text"])
        
        # Gestión de estado de botones de navegación.
        self.prevBtn.setEnabled(self.current_index > 0)
        self.checkBtn.setEnabled(not state["checked"])
        
        # En la última pregunta, cambiamos el texto del botón Siguiente.
        if self.current_index == len(self.runtime_questions) - 1:
            self.nextBtn.setText("Finalizar Evaluación")
        else:
            self.nextBtn.setText("Siguiente pregunta")
        
        self.answerGroup = QButtonGroup(self)
        self.answerGroup.setExclusive(True)
        self.answerGroup.buttonClicked.connect(self._save_immediate)

        for i, ans_text in enumerate(q["answers"]):
            row = QWidget()
            row.setMinimumHeight(70) 
            
            h = QHBoxLayout(row)
            h.setContentsMargins(10, 5, 5, 5)
            h.setSpacing(15)
            
            rb = QRadioButton()
            rb.setStyleSheet("QRadioButton::indicator { width: 20px; height: 20px; }")
            rb.setCursor(Qt.CursorShape.PointingHandCursor)
            
            lbl_letter = QLabel(f"<b>{chr(65+i)}.</b>")
            lbl_letter.setStyleSheet("font-size: 12pt;")
            lbl_letter.setFixedWidth(25)
            
            lbl_text = QLabel(ans_text)
            lbl_text.setWordWrap(True)
            lbl_text.setStyleSheet("font-size: 12pt;")
            lbl_text.setCursor(Qt.CursorShape.PointingHandCursor)
            
            # Hack para hacer clic en el texto.
            
            def make_click_handler(button):
                def handler(event):
                    # 1. Marcamos visualmente el botón.
                    button.setChecked(True)
                    # 2. Forzamos el guardado lógico INMEDIATAMENTE (VAlidar funcionamiento).
                    self._save_immediate(button)
                return handler
            
            lbl_text.mousePressEvent = make_click_handler(rb)
            
            h.addWidget(rb)
            h.addWidget(lbl_letter)
            h.addWidget(lbl_text, 1)
            
            self.answersLayout.addWidget(row)
            self.answerGroup.addButton(rb, i)
            
            line = QFrame()
            line.setFrameShape(QFrame.Shape.HLine)
            line.setFrameShadow(QFrame.Shadow.Sunken)
            line.setStyleSheet("color: #cccccc;")
            self.answersLayout.addWidget(line)
            
            # Restaurar estado visual previo.
            if state["checked"]:
                rb.setEnabled(False)
            if state["selected_index"] == i:
                rb.setChecked(True)

        if state["checked"]:
            self._show_feedback(state["correct"], q.get("explanation", ""), play_sound=False)

    # =================================================
    # MOSTRAR FEEDBACK (_SHOW_FEEDBACK)
    # =================================================

    def _show_feedback(self, correct, explanation, play_sound=True):
        if correct:
            self.feedbackLabel.setText("¡Respuesta Correcta!")
            self.feedbackLabel.setStyleSheet("color: #00AA00; font-weight: bold; font-size: 16pt;")
            if play_sound: self._play_sound("correct")
        else:
            self.feedbackLabel.setText("¡Respuesta Incorrecta!")
            self.feedbackLabel.setStyleSheet("color: #CC0000; font-weight: bold; font-size: 16pt;")
            if play_sound: self._play_sound("wrong")
        
        if explanation:
            self.explLabel.setVisible(True)
            self.explText.setVisible(True)
            self.explText.setText(explanation)
        else:
            self.explLabel.setVisible(False)
            self.explText.setVisible(False)

    # =================================================
    # REPRODUCIR SONIDO (_PLAY_SOUND)
    # =================================================

    def _play_sound(self, sound_type):
        if not self._sound_player: return
        filename = "correct_answer.wav" if sound_type == "correct" else "Wrong_answer.wav"
        path = resource_path(os.path.join("assets", "audio", filename))
        if os.path.exists(path):
            media = self._vlc_instance.media_new(path)
            self._sound_player.set_media(media)
            self._sound_player.play()

    # =================================================
    # BOTÓN COMPROBAR (_ON_CHECK)
    # =================================================

    def _on_check(self):
        idx = self.answerGroup.checkedId()
        if idx == -1:
            QMessageBox.warning(self, "Atención", "Debes seleccionar una respuesta.")
            return

        state = self.question_states[self.current_index]
        q = self.runtime_questions[self.current_index]
        
        state["selected_index"] = idx
        state["checked"] = True
        state["correct"] = (idx == q["correct_index"])
        
        self._show_feedback(state["correct"], q.get("explanation", ""), play_sound=True)
        self.checkBtn.setEnabled(False)
        
        for btn in self.answerGroup.buttons():
            btn.setEnabled(False)

    # =================================================
    # GUARDADO INMEDIATO (_SAVE_IMMEDIATE)
    # =================================================
    
    # Guarda la selección apenas el usuario hace clic. Guarda la respuesta en tiempo real apenas se toca una opción. Se conecta a la señal del grupo de botones.

    def _save_immediate(self, button):
        # Obtenemos el ID del botón que acaba de ser presionado.
        idx = self.answerGroup.id(button)
        
        # Si el ID es válido (mayor a -1), guardamos.
        if idx > -1:
            # Solo guardamos si la pregunta no ha sido ya corregida/validada.
            if not self.question_states[self.current_index]["checked"]:
                self.question_states[self.current_index]["selected_index"] = idx
                # print(f"Guardado inmediato índice: {idx} en pregunta {self.current_index}")
                
    # Mira los botones en pantalla y fuerza el guardado en la memoria.            
    def _force_save_current(self):
        # 1. Si la pregunta ya fue corregida (verde/rojo), no sobrescribimos nada.
        if self.question_states[self.current_index]["checked"]:
            return

        # 2. Preguntamos al grupo de botones cuál está marcado AHORA MISMO.
        idx = self.answerGroup.checkedId()
        
        # 3. Si hay algo marcado, lo guardamos en la lista de estados.
        if idx != -1:
            self.question_states[self.current_index]["selected_index"] = idx

    # =================================================
    # NAVEGACIÓN (_ON_NEXT / _ON_PREV)
    # =================================================

    def _on_next(self):
        # 1. Guardar lo que esté marcado en pantalla antes de irnos.
        self._force_save_current()

        # 2. Ahora sí, avanzamos.
        if self.current_index < len(self.runtime_questions) - 1:
            self.current_index += 1
            self._load_current_question()
        else:
            self._finish_test()

    def _on_prev(self):
        self._force_save_current()

        if self.current_index > 0:
            self.current_index -= 1
            self._load_current_question()

    # =================================================
    # CANCELAR (_ON_CANCEL)
    # =================================================

    def _on_cancel(self):
        if self.summaryArea.isVisible():
            self.accept()
        else:
            res = QMessageBox.question(self, "Cancelar", "¿Deseas cancelar la evaluación?", 
                                       QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if res == QMessageBox.StandardButton.Yes:
                self.reject()

    # =================================================
    # FINALIZAR EXAMEN (_FINISH_TEST)
    # =================================================
    
    # Calcula resultados, guarda en historial y muestra pantalla de resumen.

    def _finish_test(self):
        self._force_save_current()
        # Validar si faltan respuestas.
        unanswered = any(s["selected_index"] is None for s in self.question_states)
        if unanswered:
            res = QMessageBox.warning(self, "Incompleto", 
                                      "Hay preguntas sin responder. ¿Finalizar de todas formas?",
                                      QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if res == QMessageBox.StandardButton.No:
                return

        total_score = 0
        max_score = 0
        correct_txt = []
        incorrect_txt = []

        for i, (q, st) in enumerate(zip(self.runtime_questions, self.question_states)):
            pts = q["score"]
            max_score += pts

            user_idx = st["selected_index"]
            correct_idx = q["correct_index"]

            is_answer_correct = (user_idx is not None) and (user_idx == correct_idx)

            if is_answer_correct:
                total_score += pts
                correct_txt.append(f"Pregunta {i+1}: {q['text']}")
            else:
                incorrect_txt.append(f"Pregunta {i+1}: {q['text']}")
        
        percent = (total_score / max_score * 100) if max_score > 0 else 0
        
        # Guardar en DataManager
        self.data_manager.add_test_attempt(self.course_path, self.test_name, {
            "date": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "score": total_score,
            "max": max_score,
            "percent": percent
        })

        # Cambiar a vista de resumen
        self.scroll_area.setVisible(False)
        self.titleLabel.setVisible(False)
        self.counterLabel.setVisible(False)
        self.feedbackContainer.setVisible(False)
        self.summaryArea.setVisible(True)
        
        # Definir mensaje final según puntaje.
        if percent <= 59.0:
            color = "#cc0000"
            msg = "La evaluación de conocimiento no fue superada."
            final_msg = self.test_data.get("final_message_fail", "")
        elif 60.0 <= percent <= 74.0:
            color = "#ff8800"
            msg = "La evaluación de conocimiento fue aprobada, aunque se evidencian varias falencias."
            final_msg = self.test_data.get("final_message_pass", "")
        elif 75.0 <= percent <= 95.0:
            color = "#008000"
            msg = "Has superado la evaluación de conocimiento, aunque aún puedes mejorar tus resultados."
            final_msg = self.test_data.get("final_message_pass", "")
        else: 
            color = "#008000"
            msg = "Has superado completamente la evaluación de conocimiento. ¡Excelente trabajo, eres un(a) Crack!"
            final_msg = self.test_data.get("final_message_pass", "")
            
        self.scoreLabel.setText(f"Puntaje: {total_score:.2f} / {max_score:.2f} ({percent:.2f}%)")
        self.scoreLabel.setStyleSheet(f"color: {color}; font-size: 14pt; font-weight: bold; margin: 10px;")
        self.msgLabel.setText(msg)
        self.msgLabel.setStyleSheet(f"color: {color}; font-size: 10pt; font-weight: bold;")
        
        self.correctText.setText("\n\n".join(correct_txt) if correct_txt else "Ninguna")
        self.incorrectText.setText("\n\n".join(incorrect_txt) if incorrect_txt else "Ninguna")
        self.finalMsgText.setText(final_msg)
        
        self.prevBtn.setVisible(False)
        self.checkBtn.setVisible(False)
        self.nextBtn.setVisible(False)
        self.cancelBtn.setText("Finalizar")
        
    # =================================================
    # MOSTRAR TABLA DE HISTORIAL (SHOW_HISTORY_DIALOG)
    # =================================================

    def show_history_dialog(self):
        attempts = self.data_manager.get_test_history(self.course_path, self.test_name)
        d = QDialog(self)
        d.setWindowTitle("Historial de intentos")
        d.setWindowFlags(d.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint)
        d.resize(500, 300)
        l = QVBoxLayout(d)
        l.addWidget(QLabel("Últimos intentos registrados:", styleSheet="font-weight: bold; font-size: 12pt;"))
        table = QTableWidget(len(attempts), 4)
        table.setHorizontalHeaderLabels(["Fecha", "Puntaje", "Máx", "%"])
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        table.verticalHeader().setVisible(False)
        for i, row in enumerate(attempts):
            table.setItem(i, 0, QTableWidgetItem(str(row["date"])))
            table.setItem(i, 1, QTableWidgetItem(f"{row['score']:.2f}"))
            table.setItem(i, 2, QTableWidgetItem(f"{row['max']:.2f}"))
            table.setItem(i, 3, QTableWidgetItem(f"{row['percent']:.2f}%"))
        l.addWidget(table)
        h_btn = QHBoxLayout()
        h_btn.addStretch()
        btn = QPushButton("Cerrar")
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.clicked.connect(d.accept)
        h_btn.addWidget(btn)
        h_btn.addStretch()
        l.addLayout(h_btn)
        if self.dark_mode_enabled:
            d.setStyleSheet("QDialog { background-color: #353535; color: white; } QLabel { color: white; } QTableWidget { background-color: #222; color: white; gridline-color: #555; } QHeaderView::section { background-color: #444; color: white; } QPushButton { background-color: #444; color: white; border: 1px solid #666; padding: 6px; }")
        d.exec()