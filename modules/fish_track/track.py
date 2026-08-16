#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Fish-track - Herramienta de geolocalización y seguimiento
Módulo para The Big Fish
"""

import sys
import os
import json
import argparse
import socket
import requests
import time
import re
import subprocess 
from datetime import datetime
import logging
from urllib.parse import urlparse

# Configurar logging
logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(message)s')
logger = logging.getLogger(__name__)

# Añadir el directorio raíz al path para importar core
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class FishTrack:
    """Clase principal de Fish-track para geolocalización."""
    
    def __init__(self, target, output_dir=None, use_ip=True, use_url=True):
        """
        Inicializa Fish-track.
        
        Args:
            target: Objetivo (IP, URL, o identificador)
            output_dir: Directorio para guardar resultados
            use_ip: Usar técnicas basadas en IP
            use_url: Usar técnicas basadas en URL
        """
        self.target = target
        self.output_dir = output_dir or f"track_{target}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.use_ip = use_ip
        self.use_url = use_url
        self.locations = []
        self.ip_info = {}
        
        os.makedirs(self.output_dir, exist_ok=True)
    
    def _resolve_ip(self, target):
        """Resuelve el target a IP."""
        # Verificar si target es una URL
        if target.startswith(('http://', 'https://')):
            parsed = urlparse(target)
            target = parsed.netloc or parsed.path
        
        # Verificar si es un dominio o IP
        try:
            if not re.match(r'^\d+\.\d+\.\d+\.\d+$', target):
                ip = socket.gethostbyname(target)
                logger.info(f"🌐 {target} resuelto a: {ip}")
                return ip
            return target
        except Exception as e:
            logger.error(f"❌ Error resolviendo {target}: {e}")
            return None
    
    def _get_ip_geolocation(self, ip):
        """Obtiene geolocalización de una IP usando servicios públicos."""
        location = {
            'ip': ip,
            'timestamp': datetime.now().isoformat(),
            'sources': {}
        }
        
        # 1. Usar ip-api.com (gratuito, sin API key)
        try:
            response = requests.get(f'http://ip-api.com/json/{ip}', timeout=5)
            if response.status_code == 200:
                data = response.json()
                if data.get('status') == 'success':
                    location['sources']['ip-api'] = {
                        'city': data.get('city'),
                        'region': data.get('regionName'),
                        'country': data.get('country'),
                        'country_code': data.get('countryCode'),
                        'lat': data.get('lat'),
                        'lon': data.get('lon'),
                        'isp': data.get('isp'),
                        'org': data.get('org'),
                        'timezone': data.get('timezone'),
                        'zip': data.get('zip')
                    }
                    logger.info(f"📍 IP-API: {data.get('city')}, {data.get('country')}")
        except Exception as e:
            logger.debug(f"Error en ip-api: {e}")
        
        # 2. Usar ipinfo.io (sin API key, limitado)
        try:
            response = requests.get(f'https://ipinfo.io/{ip}/json', timeout=5)
            if response.status_code == 200:
                data = response.json()
                if 'loc' in data:
                    loc = data['loc'].split(',')
                    location['sources']['ipinfo'] = {
                        'city': data.get('city'),
                        'region': data.get('region'),
                        'country': data.get('country'),
                        'lat': float(loc[0]) if len(loc) > 0 else None,
                        'lon': float(loc[1]) if len(loc) > 1 else None,
                        'org': data.get('org'),
                        'hostname': data.get('hostname')
                    }
                    logger.info(f"📍 IPInfo: {data.get('city')}, {data.get('country')}")
        except Exception as e:
            logger.debug(f"Error en ipinfo: {e}")
        
        # Determinar mejor ubicación
        location['best_location'] = self._get_best_location(location)
        
        return location
    
    def _get_best_location(self, location):
        """Determina la mejor ubicación de las fuentes disponibles."""
        best = {
            'lat': None,
            'lon': None,
            'city': 'Unknown',
            'country': 'Unknown',
            'accuracy': 'low'
        }
        
        # Prioridad: ip-api > ipinfo
        if 'ip-api' in location['sources'] and location['sources']['ip-api']['lat']:
            data = location['sources']['ip-api']
            best['lat'] = data['lat']
            best['lon'] = data['lon']
            best['city'] = data['city'] or 'Unknown'
            best['country'] = data['country'] or 'Unknown'
            best['accuracy'] = 'medium'
            best['isp'] = data.get('isp')
            return best
        
        if 'ipinfo' in location['sources'] and location['sources']['ipinfo']['lat']:
            data = location['sources']['ipinfo']
            best['lat'] = data['lat']
            best['lon'] = data['lon']
            best['city'] = data['city'] or 'Unknown'
            best['country'] = data['country'] or 'Unknown'
            best['accuracy'] = 'medium'
            return best
        
        return best
    
    def _trace_route(self, target):
        """Realiza traceroute al objetivo."""
        logger.info(f"🔍 Realizando traceroute a: {target}")
        
        hops = []
        try:
            # Usar traceroute del sistema
            result = subprocess.run(['traceroute', '-n', '-m', '15', target], 
                                  capture_output=True, text=True)
            
            for line in result.stdout.split('\n'):
                if line.strip() and not line.startswith('traceroute'):
                    parts = line.split()
                    if len(parts) >= 2:
                        hop = {
                            'hop': parts[0] if parts[0].isdigit() else None,
                            'ip': None,
                            'rtt': []
                        }
                        
                        # Extraer IP y tiempo
                        ip_pattern = r'(\d+\.\d+\.\d+\.\d+)'
                        ips = re.findall(ip_pattern, line)
                        if ips:
                            hop['ip'] = ips[0]
                        
                        time_pattern = r'(\d+\.\d+)\s*ms'
                        times = re.findall(time_pattern, line)
                        if times:
                            hop['rtt'] = [float(t) for t in times]
                        
                        if hop['ip']:
                            hops.append(hop)
                    
            logger.info(f"✅ Traceroute completado: {len(hops)} saltos")
        except Exception as e:
            logger.error(f"❌ Error en traceroute: {e}")
        
        return hops
    
    def _get_url_info(self, url):
        """Obtiene información de una URL."""
        info = {
            'url': url,
            'timestamp': datetime.now().isoformat()
        }
        
        parsed = urlparse(url)
        info['protocol'] = parsed.scheme
        info['domain'] = parsed.netloc
        info['path'] = parsed.path
        
        # Verificar si el sitio está activo
        try:
            response = requests.get(url, timeout=5, verify=False)
            info['status_code'] = response.status_code
            info['server'] = response.headers.get('Server', 'unknown')
            info['content_length'] = len(response.content)
            info['accessible'] = response.status_code < 400
        except Exception as e:
            info['accessible'] = False
            info['error'] = str(e)
        
        # Obtener IP del dominio
        ip = self._resolve_ip(info['domain'])
        if ip:
            info['ip'] = ip
            # Enriquecer con geolocalización
            ip_location = self._get_ip_geolocation(ip)
            info['location'] = ip_location['best_location']
        
        return info
    
    def _get_past_ips(self, domain):
        """Obtiene IPs históricas de un dominio (usando SecurityTrails o similares)."""
        # Nota: Esto requiere API key, implementación simplificada
        past_ips = []
        
        # Simular búsqueda en servicios públicos
        try:
            # Usar DNS query para obtener diferentes registros
            import dns.resolver
            resolver = dns.resolver.Resolver()
            resolver.nameservers = ['8.8.8.8', '1.1.1.1']
            
            # Obtener registros A
            try:
                answers = resolver.resolve(domain, 'A')
                for answer in answers:
                    ip = str(answer)
                    if ip not in [p['ip'] for p in past_ips]:
                        past_ips.append({
                            'ip': ip,
                            'type': 'A',
                            'timestamp': datetime.now().isoformat()
                        })
            except:
                pass
            
            # Obtener registros AAAA (IPv6)
            try:
                answers = resolver.resolve(domain, 'AAAA')
                for answer in answers:
                    ip = str(answer)
                    if ip not in [p['ip'] for p in past_ips]:
                        past_ips.append({
                            'ip': ip,
                            'type': 'AAAA',
                            'timestamp': datetime.now().isoformat()
                        })
            except:
                pass
            
            # Obtener registros MX
            try:
                answers = resolver.resolve(domain, 'MX')
                for answer in answers:
                    mx_domain = str(answer.exchange).rstrip('.')
                    try:
                        mx_ip = socket.gethostbyname(mx_domain)
                        if mx_ip not in [p['ip'] for p in past_ips]:
                            past_ips.append({
                                'ip': mx_ip,
                                'type': 'MX',
                                'domain': mx_domain,
                                'timestamp': datetime.now().isoformat()
                            })
                    except:
                        pass
            except:
                pass
                
        except Exception as e:
            logger.debug(f"Error obteniendo IPs históricas: {e}")
        
        return past_ips
    
    def run(self):
        """Ejecuta el seguimiento completo."""
        logger.info(f"🕵️ Iniciando Fish-track para: {self.target}")
        logger.info("=" * 50)
        
        results = {
            'target': self.target,
            'timestamp': datetime.now().isoformat(),
            'locations': [],
            'info': {}
        }
        
        # 1. Resolver objetivo
        ip = self._resolve_ip(self.target)
        if ip:
            results['resolved_ip'] = ip
            
            # 2. Obtener geolocalización
            if self.use_ip:
                location = self._get_ip_geolocation(ip)
                results['locations'].append(location)
                self.locations.append(location)
                
                # 3. Obtener IPs históricas (si es dominio)
                if not re.match(r'^\d+\.\d+\.\d+\.\d+$', self.target):
                    past_ips = self._get_past_ips(self.target)
                    results['past_ips'] = past_ips
                    logger.info(f"📜 IPs históricas encontradas: {len(past_ips)}")
        
        # 4. Si es URL, obtener información adicional
        if self.use_url and self.target.startswith(('http://', 'https://')):
            url_info = self._get_url_info(self.target)
            results['url_info'] = url_info
            logger.info(f"🌐 URL analizada: {url_info.get('domain')}")
        
        # 5. Traceroute
        trace = self._trace_route(self.target)
        results['trace'] = trace
        
        # 6. Guardar resultados
        self._save_results(results)
        
        logger.info("=" * 50)
        logger.info(f"✅ Seguimiento completado")
        
        return results
    
    def _save_results(self, results):
        """Guarda los resultados en archivos."""
        # Guardar JSON completo
        json_file = os.path.join(self.output_dir, f"track_{self.target}_results.json")
        with open(json_file, 'w') as f:
            json.dump(results, f, indent=2)
        logger.info(f"💾 Resultados guardados en: {json_file}")
        
        # Guardar ubicación en formato KML para Google Earth
        if results.get('locations'):
            self._save_kml(results['locations'])
        
        # Guardar en base de datos
        try:
            from core.database import FishDatabase
            db_path = os.environ.get('THE_BIG_FISH_DB', 'data/fish.db')
            db = FishDatabase(db_path)
            
            for location in results.get('locations', []):
                best = location.get('best_location', {})
                if best.get('lat') and best.get('lon'):
                    db.save_location(
                        target=self.target,
                        lat=best['lat'],
                        lon=best['lon'],
                        accuracy=0.5,  # Aproximado
                        metadata={
                            'ip': location.get('ip'),
                            'city': best.get('city'),
                            'country': best.get('country'),
                            'sources': list(location.get('sources', {}).keys())
                        }
                    )
            
            # Actualizar escaneo si está en curso
            if 'THE_BIG_FISH_SCAN_ID' in os.environ:
                scan_id = int(os.environ.get('THE_BIG_FISH_SCAN_ID'))
                db.update_scan(scan_id, status='completed', results=results)
            
            db.close()
        except Exception as e:
            logger.warning(f"No se pudo guardar en base de datos: {e}")
    
    def _save_kml(self, locations):
        """Genera archivo KML para visualización en Google Earth."""
        kml_file = os.path.join(self.output_dir, f"track_{self.target}.kml")
        
        kml_template = """<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
  <Document>
    <name>Fish-track: {target}</name>
    <description>Ubicaciones de {target}</description>
"""
        
        for i, location in enumerate(locations):
            best = location.get('best_location', {})
            if best.get('lat') and best.get('lon'):
                kml_template += f"""
    <Placemark>
      <name>Ubicación {i+1}</name>
      <description>
        IP: {location.get('ip', 'unknown')}
        Ciudad: {best.get('city', 'unknown')}
        País: {best.get('country', 'unknown')}
        ISP: {best.get('isp', 'unknown')}
      </description>
      <Point>
        <coordinates>{best['lon']},{best['lat']},0</coordinates>
      </Point>
    </Placemark>
"""
        
        kml_template += """
  </Document>
</kml>
"""
        
        with open(kml_file, 'w') as f:
            f.write(kml_template.format(target=self.target))
        
        logger.info(f"🗺️ Archivo KML generado: {kml_file}")

def main():
    """Función principal para ejecución desde línea de comandos."""
    parser = argparse.ArgumentParser(description='Fish-track - Herramienta de geolocalización')
    parser.add_argument('--target', required=True, help='Objetivo (IP, dominio o URL)')
    parser.add_argument('--output', help='Directorio de salida')
    parser.add_argument('--no-ip', action='store_true', help='Deshabilitar técnicas IP')
    parser.add_argument('--no-url', action='store_true', help='Deshabilitar técnicas URL')
    
    args = parser.parse_args()
    
    # Ejecutar Fish-track
    track = FishTrack(
        target=args.target,
        output_dir=args.output,
        use_ip=not args.no_ip,
        use_url=not args.no_url
    )
    
    results = track.run()
    
    # Imprimir resumen
    print("\n📊 RESUMEN:")
    print(f"  Objetivo: {args.target}")
    print(f"  Resultados guardados en: {track.output_dir}")
    
    if results.get('resolved_ip'):
        print(f"  IP resuelta: {results['resolved_ip']}")
    
    if results.get('locations'):
        best_loc = results['locations'][0].get('best_location', {})
        print(f"  Ubicación: {best_loc.get('city', 'unknown')}, {best_loc.get('country', 'unknown')}")
        if best_loc.get('lat') and best_loc.get('lon'):
            print(f"  Coordenadas: {best_loc['lat']}, {best_loc['lon']}")

if __name__ == "__main__":
    main()
