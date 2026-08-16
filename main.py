#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
The Big Fish - Cuartel General del Analista
Punto de entrada principal para la aplicación.
"""

import sys
import os
import json
import argparse
from pathlib import Path

# Añadir el directorio raíz al path para importar módulos
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Intentar importar Flask
try:
    from flask import Flask, render_template, jsonify
    FLASK_AVAILABLE = True
except ImportError:
    FLASK_AVAILABLE = False
    print("[!] Flask no está instalado. Ejecuta: pip install flask")

# Configuración global
CONFIG_PATH = Path("config/settings.json")
DATA_DIR = Path("data")
DB_PATH = DATA_DIR / "fish.db"

# Crear directorios necesarios
DATA_DIR.mkdir(exist_ok=True)

def load_config():
    """Carga la configuración desde el archivo JSON."""
    default_config = {
        "app_name": "The Big Fish",
        "version": "1.0.0",
        "debug": True,
        "host": "127.0.0.1",
        "port": 5000,
        "database": str(DB_PATH),
        "modules": {
            "fish_recon": {"enabled": True},
            "wifi_cannon": {"enabled": True},
            "fish_track": {"enabled": True},
            "fish_nmap": {"enabled": True}
        }
    }
    
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH, 'r') as f:
            try:
                config = json.load(f)
                # Actualizar con valores por defecto si faltan
                for key, value in default_config.items():
                    if key not in config:
                        config[key] = value
                return config
            except json.JSONDecodeError:
                print("[!] Error al decodificar config/settings.json. Usando configuración por defecto.")
                return default_config
    else:
        print("[!] Archivo config/settings.json no encontrado. Creando uno con valores por defecto.")
        CONFIG_PATH.parent.mkdir(exist_ok=True)
        with open(CONFIG_PATH, 'w') as f:
            json.dump(default_config, f, indent=4)
        return default_config

# Cargar configuración al iniciar
config = load_config()

def create_web_app():
    """Crea y configura la aplicación web Flask."""
    if not FLASK_AVAILABLE:
        print("[!] Flask no está disponible. No se puede iniciar el modo web.")
        return None

    app = Flask(__name__,
                template_folder='web/templates',
                static_folder='web/static')
    app.config['SECRET_KEY'] = 'the-big-fish-secret-key'

    @app.route('/')
    def index():
        """Página principal del dashboard."""
        return render_template('index.html', config=config)

    @app.route('/api/status')
    def api_status():
        """API simple para verificar el estado."""
        return jsonify({
            "status": "online",
            "app": config.get("app_name"),
            "version": config.get("version")
        })

    @app.route('/api/modules')
    def api_modules():
        """API para listar los módulos disponibles."""
        return jsonify(config.get("modules", {}))

    return app

def run_web_mode():
    """Ejecuta la interfaz web."""
    if not FLASK_AVAILABLE:
        print("[!] No se puede iniciar el modo web. Flask no está instalado.")
        return

    app = create_web_app()
    if app:
        host = config.get("host", "127.0.0.1")
        port = config.get("port", 5000)
        debug = config.get("debug", True)
        
        print(f"""
  🐟 The Big Fish v{config.get('version')}
  ============================================
  ▶ Panel web iniciado en: http://{host}:{port}
  ▶ Modo debug: {debug}
  ▶ Presiona CTRL+C para detener
  ============================================
        """)
        app.run(host=host, port=port, debug=debug)

def run_cli_mode():
    """Ejecuta el modo CLI (por implementar)."""
    print("  🐟 The Big Fish v{}".format(config.get('version')))
    print("  ============================================")
    print("  ▶ Modo CLI en desarrollo. Próximamente...")
    print("  ============================================")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="The Big Fish - Cuartel General del Analista")
    parser.add_argument("--web", action="store_true", help="Iniciar interfaz web")
    parser.add_argument("--cli", action="store_true", help="Iniciar modo CLI")
    parser.add_argument("--desktop", action="store_true", help="Iniciar aplicación de escritorio (próximamente)")

    args = parser.parse_args()

    # Si no se especifica modo, mostrar ayuda
    if not (args.web or args.cli or args.desktop):
        parser.print_help()
        print("\n  Usa --web para iniciar el panel web.")
        sys.exit(0)

    if args.web:
        run_web_mode()
    elif args.cli:
        run_cli_mode()
    elif args.desktop:
        print("[!] Modo escritorio aún no implementado.")
        print("    Usa --web para la interfaz web.")
