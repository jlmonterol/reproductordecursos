"""
Función: Funciones auxiliares de texto.

Convierte milisegundos a formato de tiempo "MM:SS", limpia nombres de archivos
(quita "01 - "), formatea fechas y convierte texto con enlaces a HTML clicable.

"""

# =================================================
# IMPORTACIONES NECESARIAS
# =================================================

import os
import re
import html

# =================================================
# FUNCIÓN FORMAT_MS_TO_TIME (FORMATO DE TIEMPO)
# =================================================

# Recibe una cantidad de milisegundos (int) y la convierte en una cadena legible tipo reloj: "MM:SS" (ej: 05:30) o "HH:MM:SS" (ej: 01:15:20) si supera la hora.

def format_ms_to_time(ms: int) -> str:
    """Convierte milisegundos a formato MM:SS o HH:MM:SS"""
    if ms < 0: 
        ms = 0
    
    total_seconds = int(ms / 1000)
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60
    
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    
    return f"{minutes:02d}:{seconds:02d}"

# =================================================
# FUNCIÓN FORMAT_PLAYBACK_RATE (VELOCIDAD)
# =================================================

# Formatea el valor flotante de la velocidad de reproducción para mostrarlo en la interfaz (ej: convierte 1.0 en "x1.0").

def format_playback_rate(rate: float) -> str:
    """Formatea la velocidad de reproducción (ej. 1.0 -> x1.0)"""
    return f"x{rate:.1f}"

# =================================================
# FUNCIÓN CLEAN_TITLE_TEXT (LIMPIEZA DE TÍTULOS)
# =================================================

# Elimina los prefijos numéricos de los nombres de archivos o carpetas para mostrar un título más limpio en la interfaz.
# Ej: Transforma "01 - Introducción" en "Introducción".

def clean_title_text(text: str) -> str:
    """Elimina la numeración 'XX - ' del inicio si existe."""
    parts = text.split(" - ", 1)
    if len(parts) > 1 and parts[0].strip().isdigit():
        return parts[1].strip()
    return text

# =================================================
# FUNCIÓN FORMAT_DATE_NAME (FORMATO DE FECHAS)
# =================================================

# Detecta nombres de archivos que contienen fechas (DD-MM-AAAA) y los convierte a un formato de texto largo y elegante en español.
# Ej: "23-01-2025" -> "23 de Enero del 2025".

def format_date_name(filename: str, include_index: bool = True) -> str:
    name_no_ext = os.path.splitext(filename)[0]
    
    # Regex: Detecta
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

# =================================================
# FUNCIÓN TEXT_TO_HTML_LINK (ENLACES CLICABLES)
# =================================================

# Convierte texto plano que contenga URLs (http://...) en código HTML válido con etiquetas <a> para que sean clicables dentro de los widgets de PyQt.
# También aplica estilos de color personalizados (para modo oscuro/claro).

def text_to_html_link(text: str, link_color: str) -> str:
    safe_text = html.escape(text)
    url_pattern = re.compile(r'((?:https?://|www\.)[^\s]+)')
    
    def link_wrap(match):
        url = match.group(1)
        href = "http://" + url if url.startswith("www.") else url
        return f'<a href="{href}">{url}</a>'
        
    linked_text = url_pattern.sub(link_wrap, safe_text)
    return f"""
    <html>
    <head><style>a {{ color: {link_color}; text-decoration: underline; }}</style></head>
    <body>{linked_text.replace("\n", "<br>")}</body>
    </html>
    """