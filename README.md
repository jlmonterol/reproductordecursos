# 🎓 Reproductor de Cursos

> Una herramienta de reproducción de video optimizada para estudiantes de programación, con gestión de notas, temporizador Pomodoro y control de playlists.

## 📄 Descripción

El **Reproductor de Cursos** es una aplicación de escritorio desarrollada en Python que busca mejorar la experiencia de aprendizaje autodidacta. A diferencia de los reproductores convencionales, esta herramienta integra funcionalidades específicas para el estudio, permitiendo al usuario mantener el foco, organizar su material de estudio y tomar notas sin salir de la aplicación.

## ✨ Características Principales

* **📺 Reproducción Multimedia Robusta:** Basado en el motor de VLC para una reproducción fluida de múltiples formatos. (https://www.videolan.org/vlc/)
* **🍅 Técnica Pomodoro:** Temporizador integrado para gestionar ciclos de estudio y descanso.
* **📝 Notas y Ejercicios:** Módulo para redactar y guardar notas asociadas a los cursos.
* **📂 Gestión de Playlists:** Visualización de cursos en estructura de árbol (carpetas y videos).
* **🎨 Interfaz Personalizable:** Soporte para modo Claro y Oscuro.
* **⚡ Control de Velocidad:** Ajuste de velocidad de reproducción para optimizar el tiempo de visualización.

## 🛠️ Tecnologías Utilizadas

Este proyecto ha sido construido utilizando las siguientes herramientas y librerías de Python:

* **[Python 3.x](https://www.python.org/):** Lenguaje base.
* **[PyQt6](https://pypi.org/project/PyQt6/):** Framework para la Interfaz Gráfica de Usuario (GUI).
* **[python-vlc](https://pypi.org/project/python-vlc/):** Binding de Python para la librería libVLC.
* **Sistema de Archivos:** Gestión nativa de rutas y archivos (`os`, `sys`, `pathlib`).
* **

## 📂 Estructura del Proyecto

A continuación se detalla la organización de los archivos fuente:

reproductordecursos/
├── app/
│   ├── data/                   # Gestión de datos (JSON) y modelos
│   ├── gui/                    # Interfaz Gráfica
│   │   ├── dialogs/            # Ventanas emergentes (Acerca de, Pomodoro, Exportar, Opciones y Test/Evaluación)
│   │   ├── widgets/            # Componentes reutilizables (Video, Notas)
│   │   ├── main_window.py      # Ventana principal
│   │   ├── styles.py           # Estilos visuales
│   │   └── tree_manager.py     # Gestor del árbol de navegación
│   ├── logic/                  # Lógica de Negocio (Controlador VLC, Archivos)
│   ├── utils/                  # Utilidades y configuración de rutas
│   ├── config.py               # Constantes y configuración global
│   └── __init__.py
├── assets/                     # Recursos Estáticos
│   ├── audio/                  # Sonidos de notificación
│   └── images/                 # Iconos y recursos gráficos
├── main.py                     # Punto de entrada de la aplicación
├── requirements.txt            # Lista de dependencias
├── ReproductorCursos.ico       # Icono del proyecto
└── README.md                   # Documentación del proyecto
