#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
The Big Fish - Desktop UI
Interfaz de escritorio usando PyQt5
"""

import sys
import os
import json
from datetime import datetime
from pathlib import Path

# Añadir directorio raíz al path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from PyQt5.QtWidgets import *
    from PyQt5.QtCore import *
    from PyQt5.QtGui import *
    QT_AVAILABLE = True
except ImportError:
    QT_AVAILABLE = False
    print("[!] PyQt5 no instalado. Ejecuta: pip install PyQt5")

from core.database import FishDatabase
from core.launcher import ToolLauncher
from core.dashboard import FishDashboard

class MainWindow(QMainWindow):
    """Ventana principal de The Big Fish Desktop."""
    
    def __init__(self):
        super().__init__()
        self.db = FishDatabase()
        self.launcher = ToolLauncher(self.db)
        self.dashboard = FishDashboard(self.db, self.launcher)
        
        self.init_ui()
        self.load_data()
    
    def init_ui(self):
        """Inicializa la interfaz de usuario."""
        self.setWindowTitle("The Big Fish - Cuartel General")
        self.setGeometry(100, 100, 1200, 700)
        self.setStyleSheet("""
            QMainWindow {
                background-color: #0a0e17;
            }
            QTabWidget::pane {
                border: 1px solid #1e2d42;
                background-color: #111927;
            }
            QTabBar::tab {
                background-color: #1a2332;
                color: #8899bb;
                padding: 10px 20px;
                margin-right: 2px;
            }
            QTabBar::tab:selected {
                background-color: #4a9eff;
                color: white;
            }
            QLabel {
                color: #e8edf5;
            }
            QPushButton {
                background-color: #4a9eff;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 6px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #3a8ae5;
            }
            QPushButton#btn-success {
                background-color: #4ae0a0;
                color: #0a0e17;
            }
            QPushButton#btn-success:hover {
                background-color: #3acf90;
            }
            QLineEdit, QTextEdit {
                background-color: #1a2332;
                border: 1px solid #1e2d42;
                color: #e8edf5;
                padding: 8px;
                border-radius: 6px;
            }
            QListWidget, QTableWidget {
                background-color: #1a2332;
                border: 1px solid #1e2d42;
                color: #e8edf5;
                gridline-color: #1e2d42;
            }
            QHeaderView::section {
                background-color: #111927;
                color: #8899bb;
                padding: 8px;
                border: 1px solid #1e2d42;
            }
            QStatusBar {
                color: #8899bb;
                background-color: #111927;
            }
        """)
        
        # Widget central
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Tabs
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)
        
        # Dashboard Tab
        self.dashboard_tab = QWidget()
        self.tabs.addTab(self.dashboard_tab, "📊 Dashboard")
        self.setup_dashboard_tab()
        
        # Recon Tab
        self.recon_tab = QWidget()
        self.tabs.addTab(self.recon_tab, "🌐 Fish-recon")
        self.setup_recon_tab()
        
        # WiFi Tab
        self.wifi_tab = QWidget()
        self.tabs.addTab(self.wifi_tab, "📶 WifiCannon")
        self.setup_wifi_tab()
        
        # Track Tab
        self.track_tab = QWidget()
        self.tabs.addTab(self.track_tab, "📍 Fish-track")
        self.setup_track_tab()
        
        # Nmap Tab
        self.nmap_tab = QWidget()
        self.tabs.addTab(self.nmap_tab, "📡 Fish-nmap")
        self.setup_nmap_tab()
        
        # History Tab
        self.history_tab = QWidget()
        self.tabs.addTab(self.history_tab, "📜 Historial")
        self.setup_history_tab()
        
        # Status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("🐟 The Big Fish listo")
    
    def setup_dashboard_tab(self):
        """Configura el tab del dashboard."""
        layout = QVBoxLayout(self.dashboard_tab)
        
        # Stats grid
        stats_layout = QGridLayout()
        
        stats_data = [
            ("Escaneos Totales", "0", "🔍"),
            ("Handshakes", "0", "📶"),
            ("Subdominios", "0", "🌐"),
            ("Ubicaciones", "0", "📍")
        ]
        
        for i, (label, value, icon) in enumerate(stats_data):
            group = QGroupBox()
            group.setStyleSheet("""
                QGroupBox {
                    border: 1px solid #1e2d42;
                    border-radius: 8px;
                    padding: 10px;
                    background-color: #1a2332;
                }
            """)
            vbox = QVBoxLayout()
            vbox.addWidget(QLabel(f"{icon} {label}"))
            val_label = QLabel(value)
            val_label.setStyleSheet("font-size: 24px; font-weight: bold; color: #4a9eff;")
            val_label.setObjectName(f"stat_{i}")
            vbox.addWidget(val_label)
            group.setLayout(vbox)
            stats_layout.addWidget(group, i // 2, i % 2)
        
        layout.addLayout(stats_layout)
        
        # Refresh button
        refresh_btn = QPushButton("🔄 Actualizar")
        refresh_btn.clicked.connect(self.load_data)
        layout.addWidget(refresh_btn)
        
        # Activity log
        self.activity_log = QTextEdit()
        self.activity_log.setReadOnly(True)
        self.activity_log.setMaximumHeight(150)
        layout.addWidget(QLabel("Actividad Reciente:"))
        layout.addWidget(self.activity_log)
        
        layout.addStretch()
    
    def setup_recon_tab(self):
        """Configura el tab de Fish-recon."""
        layout = QVBoxLayout(self.recon_tab)
        
        # Input
        input_layout = QHBoxLayout()
        self.recon_target = QLineEdit()
        self.recon_target.setPlaceholderText("ejemplo.com")
        input_layout.addWidget(self.recon_target)
        
        launch_btn = QPushButton("🚀 Iniciar Escaneo")
        launch_btn.clicked.connect(self.launch_recon)
        input_layout.addWidget(launch_btn)
        layout.addLayout(input_layout)
        
        # Options
        options_layout = QHBoxLayout()
        self.recon_dns = QCheckBox("DNS")
        self.recon_dns.setChecked(True)
        self.recon_bruteforce = QCheckBox("Fuerza Bruta")
        self.recon_bruteforce.setChecked(True)
        options_layout.addWidget(self.recon_dns)
        options_layout.addWidget(self.recon_bruteforce)
        options_layout.addStretch()
        layout.addLayout(options_layout)
        
        # Results
        layout.addWidget(QLabel("Resultados:"))
        self.recon_results = QTextEdit()
        self.recon_results.setReadOnly(True)
        layout.addWidget(self.recon_results)
    
    def setup_wifi_tab(self):
        """Configura el tab de WifiCannon."""
        layout = QVBoxLayout(self.wifi_tab)
        
        # Inputs
        input_layout = QHBoxLayout()
        self.wifi_bssid = QLineEdit()
        self.wifi_bssid.setPlaceholderText("BSSID (XX:XX:XX:XX:XX:XX)")
        input_layout.addWidget(self.wifi_bssid)
        
        self.wifi_channel = QLineEdit()
        self.wifi_channel.setPlaceholderText("Canal")
        self.wifi_channel.setMaximumWidth(80)
        input_layout.addWidget(self.wifi_channel)
        
        self.wifi_interface = QLineEdit("wlan0")
        self.wifi_interface.setMaximumWidth(100)
        input_layout.addWidget(self.wifi_interface)
        layout.addLayout(input_layout)
        
        # Buttons
        btn_layout = QHBoxLayout()
        scan_btn = QPushButton("🔍 Escanear")
        scan_btn.clicked.connect(lambda: self.launch_wifi("scan"))
        btn_layout.addWidget(scan_btn)
        
        capture_btn = QPushButton("🎯 Capturar")
        capture_btn.setObjectName("btn-success")
        capture_btn.clicked.connect(lambda: self.launch_wifi("capture"))
        btn_layout.addWidget(capture_btn)
        
        wps_btn = QPushButton("🔑 WPS")
        wps_btn.clicked.connect(lambda: self.launch_wifi("wps"))
        btn_layout.addWidget(wps_btn)
        
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
        
        # Results
        layout.addWidget(QLabel("Resultados:"))
        self.wifi_results = QTextEdit()
        self.wifi_results.setReadOnly(True)
        layout.addWidget(self.wifi_results)
    
    def setup_track_tab(self):
        """Configura el tab de Fish-track."""
        layout = QVBoxLayout(self.track_tab)
        
        # Input
        input_layout = QHBoxLayout()
        self.track_target = QLineEdit()
        self.track_target.setPlaceholderText("IP, dominio o URL")
        input_layout.addWidget(self.track_target)
        
        launch_btn = QPushButton("🚀 Rastrear")
        launch_btn.clicked.connect(self.launch_track)
        input_layout.addWidget(launch_btn)
        layout.addLayout(input_layout)
        
        # Options
        options_layout = QHBoxLayout()
        self.track_ip = QCheckBox("IP")
        self.track_ip.setChecked(True)
        self.track_url = QCheckBox("URL")
        self.track_url.setChecked(True)
        options_layout.addWidget(self.track_ip)
        options_layout.addWidget(self.track_url)
        options_layout.addStretch()
        layout.addLayout(options_layout)
        
        # Results
        layout.addWidget(QLabel("Resultados:"))
        self.track_results = QTextEdit()
        self.track_results.setReadOnly(True)
        layout.addWidget(self.track_results)
    
    def setup_nmap_tab(self):
        """Configura el tab de Fish-nmap."""
        layout = QVBoxLayout(self.nmap_tab)
        
        # Input
        input_layout = QHBoxLayout()
        self.nmap_target = QLineEdit()
        self.nmap_target.setPlaceholderText("IP o dominio")
        input_layout.addWidget(self.nmap_target)
        
        self.nmap_type = QComboBox()
        self.nmap_type.addItems(["Básico", "Completo", "Sigiloso", "Vulnerabilidades"])
        input_layout.addWidget(self.nmap_type)
        
        self.nmap_ports = QLineEdit()
        self.nmap_ports.setPlaceholderText("Puertos")
        self.nmap_ports.setMaximumWidth(150)
        input_layout.addWidget(self.nmap_ports)
        
        launch_btn = QPushButton("🚀 Escanear")
        launch_btn.clicked.connect(self.launch_nmap)
        input_layout.addWidget(launch_btn)
        layout.addLayout(input_layout)
        
        # Results
        layout.addWidget(QLabel("Resultados:"))
        self.nmap_results = QTextEdit()
        self.nmap_results.setReadOnly(True)
        layout.addWidget(self.nmap_results)
    
    def setup_history_tab(self):
        """Configura el tab de historial."""
        layout = QVBoxLayout(self.history_tab)
        
        # Controls
        controls_layout = QHBoxLayout()
        self.history_filter = QLineEdit()
        self.history_filter.setPlaceholderText("Filtrar...")
        self.history_filter.textChanged.connect(self.filter_history)
        controls_layout.addWidget(self.history_filter)
        
        refresh_btn = QPushButton("🔄 Refrescar")
        refresh_btn.clicked.connect(self.load_history)
        controls_layout.addWidget(refresh_btn)
        
        clear_btn = QPushButton("🗑️ Limpiar")
        clear_btn.clicked.connect(self.clear_history)
        controls_layout.addWidget(clear_btn)
        layout.addLayout(controls_layout)
        
        # Table
        self.history_table = QTableWidget()
        self.history_table.setColumnCount(5)
        self.history_table.setHorizontalHeaderLabels(["ID", "Herramienta", "Objetivo", "Estado", "Inicio"])
        self.history_table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.history_table)
    
    # ===== ACTIONS =====
    
    def load_data(self):
        """Carga datos actualizados del dashboard."""
        data = self.dashboard.get_dashboard_data()
        
        if data.get('error'):
            self.status_bar.showMessage(f"❌ Error: {data['error']}")
            return
        
        # Update stats
        stats = data.get('stats', {})
        self.findChild(QLabel, "stat_0").setText(str(stats.get('total_scans', 0)))
        self.findChild(QLabel, "stat_1").setText(str(stats.get('total_handshakes', 0)))
        self.findChild(QLabel, "stat_2").setText(str(stats.get('total_subdomains', 0)))
        self.findChild(QLabel, "stat_3").setText(str(stats.get('total_locations', 0)))
        
        # Update activity log
        activity = data.get('recent_scans', [])
        self.activity_log.clear()
        for scan in activity[:10]:
            self.activity_log.append(
                f"[{scan.get('tool', 'unknown')}] {scan.get('target', 'N/A')} - "
                f"{scan.get('status', 'unknown')} - "
                f"{scan.get('start_time', '')[:19]}"
            )
        
        self.status_bar.showMessage(f"✅ Datos actualizados - {datetime.now().strftime('%H:%M:%S')}")
    
    def load_history(self):
        """Carga el historial completo."""
        scans = self.db.get_scans(limit=100)
        self.history_table.setRowCount(len(scans))
        
        for i, scan in enumerate(scans):
            self.history_table.setItem(i, 0, QTableWidgetItem(str(scan.get('id', ''))))
            self.history_table.setItem(i, 1, QTableWidgetItem(scan.get('tool', '')))
            self.history_table.setItem(i, 2, QTableWidgetItem(scan.get('target', '')))
            
            status = scan.get('status', 'unknown')
            status_item = QTableWidgetItem(status)
            if status == 'completed':
                status_item.setForeground(QColor('#4ae0a0'))
            elif status == 'running':
                status_item.setForeground(QColor('#4a9eff'))
            elif status == 'failed':
                status_item.setForeground(QColor('#f87171'))
            self.history_table.setItem(i, 3, status_item)
            
            start_time = scan.get('start_time', '')[:19]
            self.history_table.setItem(i, 4, QTableWidgetItem(start_time))
        
        self.history_table.resizeColumnsToContents()
    
    def filter_history(self):
        """Filtra el historial."""
        filter_text = self.history_filter.text().lower()
        for i in range(self.history_table.rowCount()):
            visible = False
            for j in range(self.history_table.columnCount()):
                item = self.history_table.item(i, j)
                if item and filter_text in item.text().lower():
                    visible = True
                    break
            self.history_table.setRowHidden(i, not visible)
    
    def clear_history(self):
        """Limpia el historial."""
        reply = QMessageBox.question(
            self, 'Confirmar', '¿Eliminar todo el historial?',
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            # Limpiar base de datos (implementar)
            self.status_bar.showMessage("🗑️ Historial limpiado")
            self.load_history()
    
    # ===== TOOL LAUNCHERS =====
    
    def launch_recon(self):
        target = self.recon_target.text().strip()
        if not target:
            QMessageBox.warning(self, "Error", "Ingresa un dominio")
            return
        
        options = {
            'use_dns': self.recon_dns.isChecked(),
            'use_bruteforce': self.recon_bruteforce.isChecked(),
            'threads': 10
        }
        
        result = self.launcher.launch_tool('fish_recon', target, options)
        if result.get('success'):
            self.status_bar.showMessage(f"✅ Fish-recon iniciado (ID: {result['scan_id']})")
            self.recon_results.append(f"[{datetime.now().strftime('%H:%M:%S')}] "
                                     f"Iniciado escaneo para {target}")
        else:
            QMessageBox.critical(self, "Error", result.get('error', 'Error desconocido'))
    
    def launch_wifi(self, mode):
        bssid = self.wifi_bssid.text().strip()
        if mode != 'scan' and not bssid:
            QMessageBox.warning(self, "Error", "Ingresa un BSSID")
            return
        
        options = {
            'mode': mode,
            'interface': self.wifi_interface.text().strip() or 'wlan0'
        }
        if self.wifi_channel.text().strip():
            options['channel'] = int(self.wifi_channel.text())
        
        result = self.launcher.launch_tool('wifi_cannon', bssid or 'all', options)
        if result.get('success'):
            self.status_bar.showMessage(f"✅ WifiCannon iniciado (ID: {result['scan_id']})")
            self.wifi_results.append(f"[{datetime.now().strftime('%H:%M:%S')}] "
                                    f"Iniciado modo: {mode}")
        else:
            QMessageBox.critical(self, "Error", result.get('error', 'Error desconocido'))
    
    def launch_track(self):
        target = self.track_target.text().strip()
        if not target:
            QMessageBox.warning(self, "Error", "Ingresa un objetivo")
            return
        
        options = {
            'use_ip': self.track_ip.isChecked(),
            'use_url': self.track_url.isChecked()
        }
        
        result = self.launcher.launch_tool('fish_track', target, options)
        if result.get('success'):
            self.status_bar.showMessage(f"✅ Fish-track iniciado (ID: {result['scan_id']})")
            self.track_results.append(f"[{datetime.now().strftime('%H:%M:%S')}] "
                                     f"Iniciado rastreo para {target}")
        else:
            QMessageBox.critical(self, "Error", result.get('error', 'Error desconocido'))
    
    def launch_nmap(self):
        target = self.nmap_target.text().strip()
        if not target:
            QMessageBox.warning(self, "Error", "Ingresa un objetivo")
            return
        
        scan_types = ["basic", "full", "stealth", "vuln"]
        scan_type = scan_types[self.nmap_type.currentIndex()]
        
        options = {
            'scan_type': scan_type
        }
        if self.nmap_ports.text().strip():
            options['ports'] = self.nmap_ports.text().strip()
        
        result = self.launcher.launch_tool('fish_nmap', target, options)
        if result.get('success'):
            self.status_bar.showMessage(f"✅ Fish-nmap iniciado (ID: {result['scan_id']})")
            self.nmap_results.append(f"[{datetime.now().strftime('%H:%M:%S')}] "
                                    f"Iniciado escaneo para {target} ({scan_type})")
        else:
            QMessageBox.critical(self, "Error", result.get('error', 'Error desconocido'))

def run_desktop():
    """Ejecuta la aplicación de escritorio."""
    if not QT_AVAILABLE:
        print("[!] PyQt5 no instalado. No se puede iniciar el modo escritorio.")
        return
    
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    
    # Icono de la aplicación
    app.setWindowIcon(QIcon())
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec_())

if __name__ == "__main__":
    run_desktop()
