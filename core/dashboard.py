# -*- coding: utf-8 -*-

"""
The Big Fish - Dashboard Module
Visualización centralizada de todas las operaciones.
"""

import json
from datetime import datetime, timedelta
from collections import Counter
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class FishDashboard:
    """Dashboard central de The Big Fish."""
    
    def __init__(self, db, launcher):
        self.db = db
        self.launcher = launcher
        self.cache = {}
        self.last_update = None
    
    def get_dashboard_data(self):
        """Obtiene todos los datos para el dashboard."""
        try:
            # Estadísticas generales
            stats = self.db.get_stats()
            
            # Últimos escaneos
            recent_scans = self.db.get_scans(limit=10)
            
            # Procesos activos
            running = self.launcher.get_running_tools()
            
            # Últimos handshakes
            recent_handshakes = self.db.get_handshakes(limit=5)
            
            # Últimos subdominios
            recent_subdomains = self.db.get_subdomains(limit=5)
            
            # Últimas ubicaciones
            recent_locations = self.db.get_locations(limit=5)
            
            # Actividad reciente (últimas 24h)
            activity = self._get_activity_timeline()
            
            return {
                'timestamp': datetime.now().isoformat(),
                'stats': stats,
                'recent_scans': recent_scans,
                'running_tools': running,
                'recent_handshakes': recent_handshakes,
                'recent_subdomains': recent_subdomains,
                'recent_locations': recent_locations,
                'activity': activity,
                'system_info': self._get_system_info()
            }
            
        except Exception as e:
            logger.error(f"❌ Error obteniendo datos del dashboard: {e}")
            return {'error': str(e)}
    
    def _get_activity_timeline(self):
        """Genera timeline de actividad de las últimas 24 horas."""
        activity = []
        now = datetime.now()
        last_day = now - timedelta(days=1)
        
        # Obtener escaneos de las últimas 24h
        scans = self.db.get_scans(limit=100)
        
        for scan in scans:
            try:
                scan_time = datetime.fromisoformat(scan['start_time'])
                if scan_time > last_day:
                    activity.append({
                        'time': scan_time.isoformat(),
                        'type': 'scan',
                        'tool': scan['tool'],
                        'target': scan['target'],
                        'status': scan.get('status', 'running')
                    })
            except:
                continue
        
        # Ordenar por tiempo (más reciente primero)
        activity.sort(key=lambda x: x['time'], reverse=True)
        
        return activity[:20]  # Top 20 eventos
    
    def _get_system_info(self):
        """Obtiene información del sistema."""
        import platform
        import os
        
        return {
            'os': platform.system(),
            'os_version': platform.version(),
            'python_version': platform.python_version(),
            'hostname': platform.node(),
            'cpus': os.cpu_count(),
            'timestamp': datetime.now().isoformat()
        }
    
    def get_module_status(self):
        """Obtiene el estado de todos los módulos."""
        modules = {}
        
        # Verificar si existen los módulos
        module_paths = [
            'modules/fish_recon/recon.py',
            'modules/wifi_cannon/cannon.py',
            'modules/fish_track/track.py',
            'modules/fish_nmap/nmap_scan.py'
        ]
        
        for path in module_paths:
            from pathlib import Path
            module_name = path.split('/')[1] if '/' in path else path
            exists = Path(path).exists()
            modules[module_name] = {
                'installed': exists,
                'path': path
            }
        
        return modules
    
    def get_visualization_data(self, scan_id=None):
        """
        Obtiene datos para visualizaciones gráficas.
        
        Args:
            scan_id: ID específico de escaneo (opcional)
        """
        if scan_id:
            scan = self.db.get_scans(limit=1)
            if scan:
                return self._parse_scan_results(scan[0])
        
        # Datos agregados para gráficos generales
        return {
            'scans_by_tool': self._get_scans_by_tool(),
            'handshakes_by_bssid': self._get_handshakes_by_bssid(),
            'subdomains_by_domain': self._get_subdomains_by_domain(),
            'activity_heatmap': self._get_activity_heatmap()
        }
    
    def _parse_scan_results(self, scan):
        """Parsea los resultados de un escaneo para visualización."""
        if not scan.get('results'):
            return {'type': 'no_data'}
        
        try:
            results = json.loads(scan['results'])
            
            if scan['tool'] == 'fish_recon':
                return self._parse_recon_results(results)
            elif scan['tool'] == 'fish_nmap':
                return self._parse_nmap_results(results)
            elif scan['tool'] == 'fish_track':
                return self._parse_track_results(results)
            else:
                return {'type': 'unknown', 'data': results}
                
        except json.JSONDecodeError:
            return {'type': 'text', 'data': scan['results']}
    
    def _parse_recon_results(self, results):
        """Parsea resultados de Fish-recon."""
        return {
            'type': 'subdomains',
            'data': results.get('subdomains', []),
            'domain': results.get('domain'),
            'total': len(results.get('subdomains', []))
        }
    
    def _parse_nmap_results(self, results):
        """Parsea resultados de Fish-nmap."""
        return {
            'type': 'ports',
            'data': results.get('ports', []),
            'target': results.get('target'),
            'open_ports': len([p for p in results.get('ports', []) if p.get('state') == 'open'])
        }
    
    def _parse_track_results(self, results):
        """Parsea resultados de Fish-track."""
        return {
            'type': 'location',
            'data': results.get('locations', []),
            'target': results.get('target'),
            'last_location': results.get('locations', [])[-1] if results.get('locations') else None
        }
    
    def _get_scans_by_tool(self):
        """Obtiene conteo de escaneos por herramienta."""
        stats = self.db.get_stats()
        return stats.get('scans_by_tool', {})
    
    def _get_handshakes_by_bssid(self):
        """Obtiene handshakes agrupados por BSSID."""
        handshakes = self.db.get_handshakes(limit=100)
        bssid_count = Counter()
        for h in handshakes:
            bssid_count[h['bssid']] += 1
        return dict(bssid_count.most_common(10))
    
    def _get_subdomains_by_domain(self):
        """Obtiene subdominios agrupados por dominio."""
        subdomains = self.db.get_subdomains(limit=100)
        domain_count = Counter()
        for s in subdomains:
            domain_count[s['domain']] += 1
        return dict(domain_count.most_common(10))
    
    def _get_activity_heatmap(self):
        """Genera datos para heatmap de actividad."""
        # Últimos 7 días
        heatmap = {}
        today = datetime.now().date()
        
        for i in range(7):
            date = today - timedelta(days=i)
            date_str = date.isoformat()
            
            # Contar escaneos de ese día
            count = 0
            scans = self.db.get_scans(limit=200)
            for scan in scans:
                try:
                    scan_date = datetime.fromisoformat(scan['start_time']).date()
                    if scan_date == date:
                        count += 1
                except:
                    continue
            
            heatmap[date_str] = count
        
        return heatmap
    
    def export_report(self, format_type='json'):
        """Exporta un reporte completo del dashboard."""
        data = self.get_dashboard_data()
        
        if format_type == 'json':
            return json.dumps(data, indent=2)
        elif format_type == 'html':
            # Generar HTML básico
            html = f"""
            <html>
            <head><title>The Big Fish - Report</title></head>
            <body>
                <h1>The Big Fish - Report</h1>
                <h2>Stats</h2>
                <pre>{json.dumps(data.get('stats', {}), indent=2)}</pre>
                <h2>Recent Scans</h2>
                <ul>
            """
            for scan in data.get('recent_scans', [])[:10]:
                html += f"<li>{scan['tool']} - {scan['target']} - {scan.get('status', 'unknown')}</li>"
            html += """
                </ul>
            </body>
            </html>
            """
            return html
        
        return None
