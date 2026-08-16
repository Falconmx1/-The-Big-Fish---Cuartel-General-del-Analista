# -*- coding: utf-8 -*-

"""
The Big Fish - Database Module
Manejo de la base de datos local SQLite para almacenar resultados.
"""

import sqlite3
import json
import threading
from datetime import datetime
from pathlib import Path
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class FishDatabase:
    """Clase principal para manejar la base de datos de The Big Fish."""
    
    def __init__(self, db_path="data/fish.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(exist_ok=True)
        self._local = threading.local()
        self._initialize_db()
    
    def _get_connection(self):
        """Obtiene una conexión a la base de datos para el hilo actual."""
        if not hasattr(self._local, 'connection') or self._local.connection is None:
            self._local.connection = sqlite3.connect(str(self.db_path))
            self._local.connection.row_factory = sqlite3.Row
        return self._local.connection
    
    def _initialize_db(self):
        """Crea las tablas necesarias si no existen."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Tabla de escaneos
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS scans (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tool TEXT NOT NULL,
                target TEXT NOT NULL,
                scan_type TEXT,
                start_time TEXT NOT NULL,
                end_time TEXT,
                status TEXT DEFAULT 'running',
                results TEXT,
                metadata TEXT
            )
        ''')
        
        # Tabla de handshakes WiFi
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS handshakes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                bssid TEXT NOT NULL,
                essid TEXT,
                channel INTEGER,
                capture_time TEXT NOT NULL,
                file_path TEXT,
                status TEXT DEFAULT 'captured',
                metadata TEXT
            )
        ''')
        
        # Tabla de ubicaciones
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS locations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                target TEXT NOT NULL,
                lat REAL NOT NULL,
                lon REAL NOT NULL,
                accuracy REAL,
                timestamp TEXT NOT NULL,
                metadata TEXT
            )
        ''')
        
        # Tabla de subdominios
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS subdomains (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                domain TEXT NOT NULL,
                subdomain TEXT NOT NULL,
                ip TEXT,
                found_date TEXT NOT NULL,
                source TEXT,
                metadata TEXT
            )
        ''')
        
        conn.commit()
        logger.info("✅ Base de datos inicializada correctamente")
    
    def close(self):
        """Cierra la conexión a la base de datos del hilo actual."""
        if hasattr(self._local, 'connection') and self._local.connection:
            self._local.connection.close()
            self._local.connection = None
    
    # ========== MÉTODOS PARA ESCANEOS ==========
    
    def save_scan(self, tool, target, scan_type=None, metadata=None):
        """Guarda un nuevo escaneo en la base de datos."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        now = datetime.now().isoformat()
        cursor.execute('''
            INSERT INTO scans (tool, target, scan_type, start_time, metadata)
            VALUES (?, ?, ?, ?, ?)
        ''', (tool, target, scan_type, now, json.dumps(metadata) if metadata else None))
        
        conn.commit()
        scan_id = cursor.lastrowid
        logger.info(f"📝 Escaneo guardado: {tool} - {target} (ID: {scan_id})")
        return scan_id
    
    def update_scan(self, scan_id, status=None, results=None, metadata=None):
        """Actualiza un escaneo existente."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        updates = []
        params = []
        
        if status:
            updates.append("status = ?")
            params.append(status)
        
        if results is not None:
            updates.append("results = ?")
            params.append(json.dumps(results))
        
        if metadata:
            updates.append("metadata = ?")
            params.append(json.dumps(metadata))
        
        if not updates:
            return
        
        if status == 'completed':
            updates.append("end_time = ?")
            params.append(datetime.now().isoformat())
        
        params.append(scan_id)
        query = f"UPDATE scans SET {', '.join(updates)} WHERE id = ?"
        cursor.execute(query, params)
        conn.commit()
        logger.info(f"✅ Escaneo {scan_id} actualizado")
    
    def get_scans(self, tool=None, target=None, limit=50):
        """Obtiene escaneos filtrados."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        query = "SELECT * FROM scans WHERE 1=1"
        params = []
        
        if tool:
            query += " AND tool = ?"
            params.append(tool)
        if target:
            query += " AND target LIKE ?"
            params.append(f"%{target}%")
        
        query += " ORDER BY start_time DESC LIMIT ?"
        params.append(limit)
        
        cursor.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]
    
    # ========== MÉTODOS PARA HANDSHAKES ==========
    
    def save_handshake(self, bssid, essid=None, channel=None, file_path=None, metadata=None):
        """Guarda un handshake capturado."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        now = datetime.now().isoformat()
        cursor.execute('''
            INSERT INTO handshakes (bssid, essid, channel, capture_time, file_path, metadata)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (bssid, essid, channel, now, file_path, json.dumps(metadata) if metadata else None))
        
        conn.commit()
        h_id = cursor.lastrowid
        logger.info(f"📶 Handshake guardado: {essid} ({bssid}) - ID: {h_id}")
        return h_id
    
    def get_handshakes(self, limit=50):
        """Obtiene los últimos handshakes."""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM handshakes 
            ORDER BY capture_time DESC LIMIT ?
        ''', (limit,))
        return [dict(row) for row in cursor.fetchall()]
    
    # ========== MÉTODOS PARA UBICACIONES ==========
    
    def save_location(self, target, lat, lon, accuracy=None, metadata=None):
        """Guarda una ubicación registrada."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        now = datetime.now().isoformat()
        cursor.execute('''
            INSERT INTO locations (target, lat, lon, accuracy, timestamp, metadata)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (target, lat, lon, accuracy, now, json.dumps(metadata) if metadata else None))
        
        conn.commit()
        loc_id = cursor.lastrowid
        logger.info(f"📍 Ubicación guardada: {target} ({lat}, {lon})")
        return loc_id
    
    def get_locations(self, target=None, limit=50):
        """Obtiene ubicaciones históricas."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        query = "SELECT * FROM locations WHERE 1=1"
        params = []
        
        if target:
            query += " AND target = ?"
            params.append(target)
        
        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)
        
        cursor.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]
    
    # ========== MÉTODOS PARA SUBDOMINIOS ==========
    
    def save_subdomain(self, domain, subdomain, ip=None, source=None, metadata=None):
        """Guarda un subdominio encontrado."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        now = datetime.now().isoformat()
        
        cursor.execute('''
            SELECT id FROM subdomains 
            WHERE domain = ? AND subdomain = ?
        ''', (domain, subdomain))
        
        if cursor.fetchone():
            logger.debug(f"⏭️ Subdominio ya existe: {subdomain}.{domain}")
            return None
        
        cursor.execute('''
            INSERT INTO subdomains (domain, subdomain, ip, found_date, source, metadata)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (domain, subdomain, ip, now, source, json.dumps(metadata) if metadata else None))
        
        conn.commit()
        s_id = cursor.lastrowid
        logger.info(f"🌐 Subdominio guardado: {subdomain}.{domain}")
        return s_id
    
    def get_subdomains(self, domain=None, limit=100):
        """Obtiene subdominios de un dominio."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        query = "SELECT * FROM subdomains WHERE 1=1"
        params = []
        
        if domain:
            query += " AND domain = ?"
            params.append(domain)
        
        query += " ORDER BY found_date DESC LIMIT ?"
        params.append(limit)
        
        cursor.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]
    
    def get_stats(self):
        """Obtiene estadísticas generales de la base de datos."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        stats = {}
        
        cursor.execute("SELECT COUNT(*) FROM scans")
        stats['total_scans'] = cursor.fetchone()[0]
        
        cursor.execute("SELECT tool, COUNT(*) FROM scans GROUP BY tool")
        stats['scans_by_tool'] = {row[0]: row[1] for row in cursor.fetchall()}
        
        cursor.execute("SELECT COUNT(*) FROM handshakes")
        stats['total_handshakes'] = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM subdomains")
        stats['total_subdomains'] = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM locations")
        stats['total_locations'] = cursor.fetchone()[0]
        
        return stats
