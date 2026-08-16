# 🐟 The Big Fish

> **El cuartel general del analista de seguridad.**

[![Version](https://img.shields.io/badge/version-1.0.0-blue.svg)](https://github.com/Falconmx1/-The-Big-Fish---Cuartel-General-del-Analista)
[![Python](https://img.shields.io/badge/python-3.8+-green.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-red.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/platform-Linux%20%7C%20macOS%20%7C%20Windows-lightgrey)]()

**The Big Fish** es una herramienta central que unifica todo tu arsenal de seguridad en una sola interfaz. Olvídate de recordar comandos complejos: todo está a un clic de distancia.

---

## 📋 Tabla de Contenidos

- [Características Principales](#-características-principales)
- [Herramientas Integradas](#-herramientas-integradas)
- [Requisitos](#-requisitos)
- [Instalación](#-instalación)
- [Uso](#-uso)
  - [Interfaz Web](#-interfaz-web-recomendada)
  - [Interfaz de Escritorio](#-interfaz-de-escritorio)
  - [Modo CLI](#-modo-cli)
- [Estructura del Proyecto](#-estructura-del-proyecto)
- [Módulos](#-módulos)
  - [Fish-recon](#-fish-recon)
  - [WifiCannon](#-wificannon)
  - [Fish-track](#-fish-track)
  - [Fish-nmap](#-fish-nmap)
- [Base de Datos](#-base-de-datos)
- [Seguridad y Ética](#-seguridad-y-ética)
- [Roadmap](#-roadmap)
- [Contribuciones](#-contribuciones)
- [Licencia](#-licencia)
- [Agradecimientos](#-agradecimientos)

---

## 🎯 Características Principales

### 📊 Dashboard de Misión
- Vista centralizada del estado de todos tus escaneos
- Monitoreo en tiempo real de tareas activas
- Resumen de resultados históricos con gráficas interactivas
- Estadísticas globales de todas las herramientas

### 🚀 Lanzador de Herramientas
- **Fish-recon**: Descubrimiento de subdominios con visualización interactiva
- **WifiCannon**: Captura de handshakes y ataques WiFi con progreso en tiempo real
- **Fish-track**: Georreferenciación y seguimiento con mapa interactivo
- **Fish-nmap**: Escaneo de puertos con visualización gráfica de resultados

### 📈 Visor de Resultados
- Gráficas y tablas interactivas para reportes
- Visualización de subdominios encontrados (mapa o lista)
- Handshakes capturados organizados y filtrables
- Historial completo de todas las operaciones
- Exportación de reportes en JSON y HTML

### 💾 Centralización de Datos
- Base de datos local (SQLite) para almacenar todos los resultados
- Historial completo de operaciones
- Fácil exportación y consulta de datos históricos
- Sin dependencias externas ni APIs de terceros

---

## 🛠️ Herramientas Integradas

| Herramienta | Rol | Función en The Big Fish |
|------------|-----|------------------------|
| **Fish-recon** | 🎣 Red de pesca | Recolecta datos, muestra subdominios en mapa interactivo |
| **WifiCannon** | 🔱 Arpón | Botones "Iniciar Captura" y "Ejecutar Ataque" con progreso en tiempo real |
| **Fish-track** | 🕵️ Rastreador | Ubicación estimada y historial de movimientos en mapa |
| **Fish-nmap** | 📡 Sonar | Selección de objetivo y visualización gráfica de puertos abiertos |

---

## 📋 Requisitos

### Sistema Operativo
- **Linux** (recomendado para funcionalidades WiFi)
- **macOS** (soporte limitado para WiFi)
- **Windows** (con WSL para funcionalidades WiFi)

### Dependencias
- **Python 3.8 o superior**
- **Nmap** (para Fish-nmap)
- **Aircrack-ng** (para WifiCannon)
- **iw** (para WifiCannon en Linux)

### Dependencias Python
Flask>=2.0.0 # Interfaz web
PyQt5>=5.15.0 # Interfaz de escritorio (opcional)
python-dateutil>=2.8.0 # Manipulación de fechas
dnspython>=2.0.0 # Consultas DNS
requests>=2.25.0 # Peticiones HTTP

text

**No requiere Docker ni dependencias externas como Shodan.**

---

## ⚡ Instalación

### 1. Clonar el repositorio

```bash
git clone https://github.com/Falconmx1/-The-Big-Fish---Cuartel-General-del-Analista.git
cd -The-Big-Fish---Cuartel-General-del-Analista
2. Crear entorno virtual (recomendado)

# Linux / macOS
python3 -m venv venv
source venv/bin/activate

# Windows
python -m venv venv
venv\Scripts\activate
3. Instalar dependencias
bash
pip install -r requirements.txt
4. Instalar dependencias del sistema (Linux)

# Para WifiCannon
sudo apt-get install aircrack-ng iw

# Para Fish-nmap
sudo apt-get install nmap

# Para Fish-track (traceroute)
sudo apt-get install traceroute
5. Verificar instalación

python main.py --web
# Deberías ver el servidor iniciado en http://127.0.0.1:5000
🖥️ Uso
🌐 Interfaz Web (Recomendada)
La interfaz web es la forma más completa y visual de usar The Big Fish.


python main.py --web
Accede a http://127.0.0.1:5000 en tu navegador.

Características de la interfaz web:

Dashboard en tiempo real

Lanzamiento de herramientas con un clic

Visualización de resultados con gráficas

Historial completo

Atajos de teclado:

Ctrl+1 a Ctrl+5: Navegación entre secciones

Ctrl+R: Actualizar datos

ESC: Cerrar modal

🖥️ Interfaz de Escritorio
Para quienes prefieren una aplicación nativa:


python desktop/ui/main_window.py
Requisitos adicionales:


pip install PyQt5
💻 Modo CLI
Para servidores sin interfaz gráfica o automatización:


# Ejecutar Fish-recon
python modules/fish_recon/recon.py --target ejemplo.com

# Ejecutar WifiCannon
sudo python modules/wifi_cannon/cannon.py --mode scan --interface wlan0

# Ejecutar Fish-track
python modules/fish_track/track.py --target 8.8.8.8

# Ejecutar Fish-nmap
python modules/fish_nmap/nmap_scan.py --target ejemplo.com --type basic
