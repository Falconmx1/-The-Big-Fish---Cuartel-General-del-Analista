#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Fish-nmap - Herramienta de escaneo de puertos
Módulo para The Big Fish
"""

import sys
import os
import json
import argparse
import subprocess
import re
import xml.etree.ElementTree as ET
from datetime import datetime
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(message)s')
logger = logging.getLogger(__name__)

# Añadir el directorio raíz al path para importar core
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class FishNmap:
    """Clase principal de Fish-nmap para escaneo de puertos."""
    
    def __init__(self, target, scan_type='basic', output_dir=None, ports=None, scripts=None):
        """
        Inicializa Fish-nmap.
        
        Args:
            target: Objetivo (IP o dominio)
            scan_type: Tipo de escaneo (basic, full, stealth, vuln)
            output_dir: Directorio para guardar resultados
            ports: Puertos a escanear (ej: "22,80,443" o "1-1000")
            scripts: Scripts de Nmap a ejecutar
        """
        self.target = target
        self.scan_type = scan_type
        self.output_dir = output_dir or f"nmap_{target}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.ports = ports
        self.scripts = scripts
        self.results = {}
        
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Verificar que Nmap está instalado
        self._check_nmap()
    
    def _check_nmap(self):
        """Verifica que Nmap está instalado."""
        try:
            subprocess.run(['nmap', '--version'], capture_output=True, check=True)
            logger.info("✅ Nmap instalado correctamente")
        except:
            logger.error("❌ Nmap no está instalado o no se encuentra en PATH")
            raise RuntimeError("Nmap no instalado")
    
    def _build_command(self):
        """Construye el comando Nmap según los parámetros."""
        cmd = ['nmap', '-oX', os.path.join(self.output_dir, 'scan.xml')]
        
        # Configurar según tipo de escaneo
        if self.scan_type == 'basic':
            cmd.extend(['-sS', '-sV', '--version-intensity', '5'])
        elif self.scan_type == 'full':
            cmd.extend(['-sS', '-sV', '-A', '-O', '--version-all'])
        elif self.scan_type == 'stealth':
            cmd.extend(['-sS', '-T2', '--min-rate', '100', '--max-rate', '1000'])
        elif self.scan_type == 'vuln':
            cmd.extend(['-sS', '-sV', '--script', 'vuln'])
        
        # Agregar scripts específicos
        if self.scripts:
            cmd.extend(['--script', self.scripts])
        
        # Puertos
        if self.ports:
            cmd.extend(['-p', self.ports])
        elif self.scan_type == 'full':
            cmd.extend(['-p-'])  # Todos los puertos
        
        # Agregar target
        cmd.append(self.target)
        
        return cmd
    
    def _parse_results(self, xml_file):
        """Parsea los resultados XML de Nmap."""
        results = {
            'target': self.target,
            'scan_type': self.scan_type,
            'timestamp': datetime.now().isoformat(),
            'ports': [],
            'hosts': [],
            'summary': {}
        }
        
        try:
            tree = ET.parse(xml_file)
            root = tree.getroot()
            
            # Información del escaneo
            scan_info = root.find('scaninfo')
            if scan_info is not None:
                results['scan_info'] = {
                    'type': scan_info.get('type'),
                    'protocol': scan_info.get('protocol'),
                    'num_services': scan_info.get('numservices')
                }
            
            # Hosts y puertos
            for host in root.findall('host'):
                host_info = {}
                
                # Dirección IP
                addr = host.find('address')
                if addr is not None:
                    host_info['ip'] = addr.get('addr')
                    host_info['addr_type'] = addr.get('addrtype')
                
                # Hostname
                hostname = host.find('hostnames/hostname')
                if hostname is not None:
                    host_info['hostname'] = hostname.get('name')
                
                # Estado del host
                status = host.find('status')
                if status is not None:
                    host_info['status'] = status.get('state')
                    host_info['status_reason'] = status.get('reason')
                
                # Puertos
                ports = host.find('ports')
                if ports is not None:
                    for port in ports.findall('port'):
                        port_info = {
                            'port': int(port.get('portid')),
                            'protocol': port.get('protocol'),
                            'state': port.find('state').get('state') if port.find('state') is not None else 'unknown',
                            'service': {}
                        }
                        
                        service = port.find('service')
                        if service is not None:
                            port_info['service']['name'] = service.get('name')
                            port_info['service']['product'] = service.get('product')
                            port_info['service']['version'] = service.get('version')
                            port_info['service']['extrainfo'] = service.get('extrainfo')
                            
                            # Scripts
                            scripts = service.findall('script')
                            if scripts:
                                port_info['scripts'] = []
                                for script in scripts:
                                    port_info['scripts'].append({
                                        'id': script.get('id'),
                                        'output': script.get('output')
                                    })
                        
                        results['ports'].append(port_info)
                
                # OS detection
                os = host.find('os')
                if os is not None:
                    os_info = []
                    for osmatch in os.findall('osmatch'):
                        os_info.append({
                            'name': osmatch.get('name'),
                            'accuracy': int(osmatch.get('accuracy')),
                            'line': osmatch.get('line')
                        })
                    if os_info:
                        host_info['os'] = os_info[0]['name']
                        host_info['os_accuracy'] = os_info[0]['accuracy']
                
                results['hosts'].append(host_info)
            
            # Resumen
            total_ports = len(results['ports'])
            open_ports = len([p for p in results['ports'] if p['state'] == 'open'])
            
            results['summary'] = {
                'total_ports': total_ports,
                'open_ports': open_ports,
                'filtered_ports': len([p for p in results['ports'] if p['state'] == 'filtered']),
                'closed_ports': len([p for p in results['ports'] if p['state'] == 'closed'])
            }
            
            # Estadísticas de escaneo
            runstats = root.find('runstats')
            if runstats is not None:
                finished = runstats.find('finished')
                if finished is not None:
                    results['timing'] = {
                        'elapsed': float(finished.get('elapsed')),
                        'time': finished.get('time'),
                        'timestr': finished.get('timestr')
                    }
            
        except Exception as e:
            logger.error(f"❌ Error parseando resultados: {e}")
        
        return results
    
    def _generate_report(self, results):
        """Genera un reporte legible del escaneo."""
        report = []
        report.append("=" * 60)
        report.append(f"🔍 FISH-NMAP REPORT")
        report.append("=" * 60)
        report.append(f"  Target: {results['target']}")
        report.append(f"  Scan Type: {results['scan_type']}")
        report.append(f"  Timestamp: {results['timestamp']}")
        report.append("-" * 60)
        
        # Resumen
        summary = results.get('summary', {})
        report.append("📊 SUMMARY:")
        report.append(f"  Total ports scanned: {summary.get('total_ports', 0)}")
        report.append(f"  Open ports: {summary.get('open_ports', 0)}")
        report.append(f"  Filtered ports: {summary.get('filtered_ports', 0)}")
        report.append(f"  Closed ports: {summary.get('closed_ports', 0)}")
        
        if results.get('timing'):
            report.append(f"  Scan time: {results['timing'].get('elapsed', 0):.2f} seconds")
        
        report.append("-" * 60)
        
        # Puertos abiertos
        open_ports = [p for p in results.get('ports', []) if p['state'] == 'open']
        if open_ports:
            report.append("🔓 OPEN PORTS:")
            for port in open_ports:
                service = port.get('service', {})
                service_name = service.get('name', 'unknown')
                product = service.get('product', '')
                version = service.get('version', '')
                
                service_info = f"{service_name}"
                if product:
                    service_info += f" ({product}"
                    if version:
                        service_info += f" {version}"
                    service_info += ")"
                
                report.append(f"  {port['port']}/{port['protocol']} - {service_info}")
                
                # Scripts
                if port.get('scripts'):
                    for script in port['scripts']:
                        report.append(f"    ├─ {script['id']}: {script['output'][:100]}...")
        else:
            report.append("  No open ports found")
        
        # Hosts
        if results.get('hosts'):
            report.append("-" * 60)
            report.append("🖥️ HOSTS:")
            for host in results['hosts']:
                report.append(f"  IP: {host.get('ip', 'unknown')}")
                if host.get('hostname'):
                    report.append(f"  Hostname: {host['hostname']}")
                if host.get('os'):
                    report.append(f"  OS: {host['os']} (accuracy: {host.get('os_accuracy', 0)}%)")
                report.append(f"  Status: {host.get('status', 'unknown')}")
        
        report.append("=" * 60)
        
        return "\n".join(report)
    
    def run(self):
        """Ejecuta el escaneo Nmap."""
        logger.info(f"📡 Iniciando Fish-nmap para: {self.target}")
        logger.info(f"  Tipo de escaneo: {self.scan_type}")
        logger.info("=" * 50)
        
        # Construir comando
        cmd = self._build_command()
        logger.info(f"🔧 Comando: {' '.join(cmd)}")
        
        try:
            # Ejecutar Nmap
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, 
                                     text=True)
            
            # Capturar salida en tiempo real
            for line in process.stdout:
                if line.strip():
                    logger.info(f"[nmap] {line.strip()}")
            
            # Esperar a que termine
            process.wait()
            
            if process.returncode != 0:
                logger.error(f"❌ Error en Nmap: Código {process.returncode}")
                stderr = process.stderr.read()
                logger.error(stderr)
                return {'error': f'Nmap failed with code {process.returncode}'}
            
            # Parsear resultados
            xml_file = os.path.join(self.output_dir, 'scan.xml')
            if os.path.exists(xml_file):
                results = self._parse_results(xml_file)
                self.results = results
                
                # Guardar resultados
                self._save_results(results)
                
                # Generar reporte
                report = self._generate_report(results)
                logger.info("\n" + report)
                
                logger.info("=" * 50)
                logger.info(f"✅ Escaneo completado")
                logger.info(f"  Puertos abiertos: {results['summary'].get('open_ports', 0)}")
                
                return results
            else:
                logger.error("❌ No se generó archivo de resultados")
                return {'error': 'No results file generated'}
                
        except Exception as e:
            logger.error(f"❌ Error ejecutando Nmap: {e}")
            return {'error': str(e)}
    
    def _save_results(self, results):
        """Guarda los resultados en archivos."""
        # Guardar JSON
        json_file = os.path.join(self.output_dir, f"nmap_{self.target}_results.json")
        with open(json_file, 'w') as f:
            json.dump(results, f, indent=2)
        logger.info(f"💾 Resultados JSON guardados en: {json_file}")
        
        # Guardar reporte texto
        report = self._generate_report(results)
        txt_file = os.path.join(self.output_dir, f"nmap_{self.target}_report.txt")
        with open(txt_file, 'w') as f:
            f.write(report)
        logger.info(f"💾 Reporte guardado en: {txt_file}")
        
        # Guardar en base de datos
        try:
            from core.database import FishDatabase
            db_path = os.environ.get('THE_BIG_FISH_DB', 'data/fish.db')
            db = FishDatabase(db_path)
            
            # Guardar escaneo
            scan_id = db.save_scan(
                tool='fish_nmap',
                target=self.target,
                scan_type=self.scan_type,
                metadata={
                    'open_ports': results.get('summary', {}).get('open_ports', 0),
                    'total_ports': results.get('summary', {}).get('total_ports', 0)
                }
            )
            
            # Actualizar con resultados
            db.update_scan(scan_id, status='completed', results=results)
            
            db.close()
        except Exception as e:
            logger.warning(f"No se pudo guardar en base de datos: {e}")

def main():
    """Función principal para ejecución desde línea de comandos."""
    parser = argparse.ArgumentParser(description='Fish-nmap - Escaneo de puertos')
    parser.add_argument('--target', required=True, help='Objetivo (IP o dominio)')
    parser.add_argument('--type', choices=['basic', 'full', 'stealth', 'vuln'], 
                       default='basic', help='Tipo de escaneo')
    parser.add_argument('--ports', help='Puertos a escanear (ej: 22,80,443 o 1-1000)')
    parser.add_argument('--scripts', help='Scripts de Nmap a ejecutar')
    parser.add_argument('--output', help='Directorio de salida')
    
    args = parser.parse_args()
    
    # Ejecutar Fish-nmap
    nmap = FishNmap(
        target=args.target,
        scan_type=args.type,
        output_dir=args.output,
        ports=args.ports,
        scripts=args.scripts
    )
    
    results = nmap.run()
    
    # Imprimir resumen
    if not results.get('error'):
        print("\n📊 RESUMEN:")
        print(f"  Target: {args.target}")
        print(f"  Resultados guardados en: {nmap.output_dir}")
        
        summary = results.get('summary', {})
        print(f"  Puertos abiertos: {summary.get('open_ports', 0)}")
        print(f"  Total puertos escaneados: {summary.get('total_ports', 0)}")

if __name__ == "__main__":
    main()
