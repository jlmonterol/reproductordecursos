"""
Función: Lector de archivos de examen.

Lee archivos .test (que son JSON), valida que estén bien escritos y extrae
las preguntas y respuestas para que test_dialog.py las use.

"""

# =================================================
# IMPORTACIONES NECESARIAS
# =================================================

import os
import json
from typing import Optional, Dict, Any, List

# =================================================
# CLASE COURSESCANNER (LECTOR DE ESTRUCTURA/TESTS)
# =================================================

# Utilitario para escanear y leer archivos especiales del curso, principalmente los archivos .test (JSON) para las evaluaciones.

class CourseScanner:

    # =================================================
    # CARGAR ARCHIVO DE TEST (LOAD_TEST_FILE)
    # =================================================
    
    # Lee un archivo .test, valida su estructura JSON, normaliza los datos (asegurando que existan preguntas, respuestas y puntajes) y devuelve un diccionario limpio listo para ser usado por la interfaz gráfica.
    
    @staticmethod
    def load_test_file(test_path: str) -> Optional[Dict[str, Any]]:
        if not os.path.exists(test_path):
            return None

        try:
            with open(test_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError):
            return None

        # Validación básica.
        if not isinstance(data, dict) or "questions" not in data:
            return None

        questions_raw = data.get("questions", [])
        if not isinstance(questions_raw, list):
            return None

        # Normalización de datos (para evitar errores en la UI).
        normalized_questions = []
        for q in questions_raw:
            if not isinstance(q, dict):
                continue
            
            # Asegurar estructura de respuestas.
            answers_raw = q.get("answers", [])
            answers = []
            if isinstance(answers_raw, list):
                for a in answers_raw:
                    # Soporte para formato antiguo (string) o nuevo (dict).
                    if isinstance(a, dict):
                        answers.append(str(a.get("text", "")))
                    else:
                        answers.append(str(a))
            
            # Rellenar si faltan respuestas para evitar crash por índice.
            while len(answers) < 2:
                answers.append("")

            normalized_questions.append({
                "text": str(q.get("text", "")),
                "score": float(q.get("score", 1.0)),
                "answers": answers,
                "correct_index": int(q.get("correct_index", 0)),
                "explanation": str(q.get("explanation", ""))
            })

        if not normalized_questions:
            return None

        # Mensajes finales (lógica de legado).
        final_msg_pass = data.get("final_message_pass") or data.get("final_message", "")
        final_msg_fail = data.get("final_message_fail") or data.get("final_message", "")

        return {
            "title": data.get("title", "Evaluación"),
            "final_message_pass": final_msg_pass,
            "final_message_fail": final_msg_fail,
            "num_questions_to_run": int(data.get("num_questions_to_run", len(normalized_questions))),
            "random_questions": bool(data.get("random_questions", False)),
            "random_answers": bool(data.get("random_answers", False)),
            "questions": normalized_questions
        }