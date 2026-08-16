# -*- coding: utf-8 -*-

"""
The Big Fish - Launcher Module
Lanza y gestiona la ejecución de las herramientas del arsenal.
"""

import subprocess
import threading
import json
import os
import sys
from pathlib import Path
from datetime import datetime
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ToolLauncher:
    """Lanzador de herramientas del arsenal Fish."""
    
    def __init__(self, db):
        self.db = db
        self.running_tools = {}
        self.tool_paths = {
            'fish_recon': 'modules/fish_recon/recon.py',
            'wifi_cannon': 'modules/wifi_cannon/cannon.py',
            'fish_track': 'modules/fish_track/track.py',
            'fish_nmap': 'modules/fish_nmap/nmap_scan.py'
        }
    
    def launch_tool(self, tool_name, target=None, options=None):
        """
        Lanza una herramienta del arsenal.
        
        Args:
            tool_name: Nombre de la herramienta (fish_recon, wifi_cannon, etc.)
            target: Objetivo (dominio, IP, BSSID, etc.)
            options: Diccionario con opciones adicionales
        
        Returns:
            dict: Información del proceso lanzado
        """
        if tool_name not in self.tool_paths:
            logger.error(f"❌ Herramienta desconocida: {tool_name}")
            return {'error': f'Herramienta {tool_name} no encontrada'}
        
        tool_path = Path(self.tool_paths[tool_name])
        if not tool_path.exists():
            logger.error(f"❌ Tool no encontrada: {tool_path}")
            return {'error': f'Archivo de herramienta no encontrado: {tool_path}'}
        
        # Construir comando según la herramienta
        cmd = [sys.executable, str(tool_path)]
        
        # Mapear opciones según la herramienta
        if tool_name == 'fish_recon':
            cmd.extend(['--target', target])
            if options:
                if options.get('threads'):
                    cmd.extend(['--threads', str(options['threads'])])
                if options.get('use_dns') is False:
                    cmd.append('--no-dns')
                if options.get('use_bruteforce') is False:
                    cmd.append('--no-bruteforce')
        
        elif tool_name == 'wifi_cannon':
            if options and options.get('mode'):
                cmd.extend(['--mode', options['mode']])
            if target and target != 'all':
                cmd.extend(['--bssid', target])
            if options:
                if options.get('interface'):
                    cmd.extend(['--interface', options['interface']])
                if options.get('channel'):
                    cmd.extend(['--channel', str(options['channel'])])
                if options.get('duration'):
                    cmd.extend(['--duration', str(options['duration'])])
        
        elif tool_name == 'fish_track':
            cmd.extend(['--target', target])
            if options:
                if options.get('use_ip') is False:
                    cmd.append('--no-ip')
                if options.get('use_url') is False:
                    cmd.append('--no-url')
        
        elif tool_name == 'fish_nmap':
            cmd.extend(['--target', target])
            if options:
                if options.get('scan_type'):
                    cmd.extend(['--type', options['scan_type']])
                if options.get('ports'):
                    cmd.extend(['--ports', options['ports']])
                if options.get('scripts'):
                    cmd.extend(['--scripts', options['scripts']])
        
        # Preparar variables de entorno
        env = os.environ.copy()
        env['THE_BIG_FISH_DB'] = str(self.db.db_path)
        
        # Iniciar proceso
        try:
            logger.info(f"🚀 Lanzando {tool_name} - Target: {target}")
            logger.info(f"🔧 Comando: {' '.join(cmd)}")
            
            # Guardar en DB
            scan_id = self.db.save_scan(
                tool=tool_name,
                target=target or 'unknown',
                scan_type=options.get('scan_type') if options else None,
                metadata={
                    'command': ' '.join(cmd),
                    'options': options,
                    'pid': None
                }
            )
            
            # Crear thread para ejecutar el proceso
            def run_process():
                try:
                    process = subprocess.Popen(
                        cmd,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True,
                        env=env,
                        cwd=Path(__file__).parent.parent
                    )
                    
                    # Guardar PID
                    self.running_tools[scan_id] = {
                        'process': process,
                        'tool': tool_name,
                        'target': target,
                        'start_time': datetime.now(),
                        'scan_id': scan_id
                    }
                    
                    # Actualizar DB con PID
                    self.db.update_scan(scan_id, metadata={
                        'pid': process.pid
                    })
                    
                    # Capturar salida en tiempo real
                    stdout_lines = []
                    stderr_lines = []
                    
                    for line in process.stdout:
                        stdout_lines.append(line)
                        logger.info(f"[{tool_name}] {line.strip()}")
                    
                    for line in process.stderr:
                        stderr_lines.append(line)
                        if line.strip():
                            logger.warning(f"[{tool_name}] ERROR: {line.strip()}")
                    
                    process.wait()
                    
                    # Guardar resultados
                    results = {
                        'stdout': ''.join(stdout_lines),
                        'stderr': ''.join(stderr_lines),
                        'returncode': process.returncode
                    }
                    
                    # Actualizar estado
                    status = 'completed' if process.returncode == 0 else 'failed'
                    self.db.update_scan(scan_id, status=status, results=results)
                    
                    # Eliminar de procesos activos
                    if scan_id in self.running_tools:
                        del self.running_tools[scan_id]
                    
                    logger.info(f"✅ Herramienta {tool_name} finalizada - Código: {process.returncode}")
                    
                except Exception as e:
                    logger.error(f"❌ Error ejecutando {tool_name}: {e}")
                    self.db.update_scan(scan_id, status='error', results={'error': str(e)})
                    if scan_id in self.running_tools:
                        del self.running_tools[scan_id]
            
            # Iniciar thread
            thread = threading.Thread(target=run_process)
            thread.daemon = True
            thread.start()
            
            return {
                'success': True,
                'scan_id': scan_id,
                'message': f'Herramienta {tool_name} lanzada correctamente'
            }
            
        except Exception as e:
            logger.error(f"❌ Error lanzando {tool_name}: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_running_tools(self):
        """Obtiene las herramientas en ejecución."""
        running = []
        for scan_id, info in self.running_tools.items():
            process = info['process']
            status = 'running'
            if process.poll() is not None:
                status = 'finished' if process.returncode == 0 else 'failed'
            
            running.append({
                'scan_id': scan_id,
                'tool': info['tool'],
                'target': info['target'],
                'start_time': info['start_time'].isoformat(),
                'pid': process.pid,
                'status': status
            })
        return running
    
    def get_scan_status(self, scan_id):
        """Obtiene el estado de un escaneo específico."""
        scans = self.db.get_scans(limit=1)
        for scan in scans:
            if scan['id'] == scan_id:
                return scan
        return None
    
    def stop_tool(self, scan_id):
        """Detiene una herramienta en ejecución."""
        if scan_id in self.running_tools:
            process = self.running_tools[scan_id]['process']
            try:
                process.terminate()
                process.wait(timeout=5)
                self.db.update_scan(scan_id, status='stopped')
                del self.running_tools[scan_id]
                logger.info(f"⏹️ Herramienta {scan_id} detenida")
                return True
            except Exception as e:
                logger.error(f"❌ Error deteniendo {scan_id}: {e}")
                return False
        return False

class ModuleLauncher(ToolLauncher):
    """Versión simplificada para lanzar módulos directamente."""
    
    def launch_recon(self, domain, options=None):
        """Lanza Fish-recon para descubrimiento de subdominios."""
        return self.launch_tool('fish_recon', target=domain, options=options)
    
    def launch_wifi(self, bssid=None, interface=None, options=None):
        """Lanza WifiCannon para captura de handshakes."""
        target = bssid or 'all'
        wifi_options = options or {}
        if interface:
            wifi_options['interface'] = interface
        return self.launch_tool('wifi_cannon', target=target, options=wifi_options)
    
    def launch_track(self, target, options=None):
        """Lanza Fish-track para geolocalización."""
        return self.launch_tool('fish_track', target=target, options=options)
    
    def launch_nmap(self, target, options=None):
        """Lanza Fish-nmap para escaneo de puertos."""
        nmap_options = options or {}
        if 'scan_type' not in nmap_options:
            nmap_options['scan_type'] = 'basic'
        return self.launch_tool('fish_nmap', target=target, options=nmap_options)
