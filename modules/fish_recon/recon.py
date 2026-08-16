#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Fish-recon - Herramienta de reconocimiento y descubrimiento de subdominios
Módulo para The Big Fish
"""

import sys
import os
import json
import argparse
import subprocess
import socket
import dns.resolver
import dns.zone
import requests
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(message)s')
logger = logging.getLogger(__name__)

# Añadir el directorio raíz al path para importar core
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class FishRecon:
    """Clase principal de Fish-recon para descubrimiento de subdominios."""
    
    def __init__(self, domain, output_dir=None, threads=10, use_dns=True, use_bruteforce=True):
        """
        Inicializa Fish-recon.
        
        Args:
            domain: Dominio objetivo (ej: example.com)
            output_dir: Directorio para guardar resultados
            threads: Número de hilos para escaneo concurrente
            use_dns: Usar técnicas de DNS
            use_bruteforce: Usar fuerza bruta con wordlist
        """
        self.domain = domain
        self.threads = threads
        self.use_dns = use_dns
        self.use_bruteforce = use_bruteforce
        self.subdomains = set()
        self.resolved_ips = {}
        
        # Configurar directorio de salida
        if output_dir:
            self.output_dir = output_dir
        else:
            self.output_dir = f"recon_{domain}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Wordlist para fuerza bruta
        self.wordlist = self._load_wordlist()
    
    def _load_wordlist(self):
        """Carga la wordlist para fuerza bruta de subdominios."""
        # Wordlist básica de subdominios comunes
        wordlist = [
            'www', 'mail', 'ftp', 'localhost', 'webmail', 'smtp', 'pop', 'ns1', 'webdisk',
            'ns2', 'cpanel', 'whm', 'autodiscover', 'autoconfig', 'm', 'imap', 'test',
            'dns', 'ns3', 'dev', 'api', 'blog', 'shop', 'support', 'docs', 'wiki',
            'forum', 'news', 'media', 'app', 'admin', 'static', 'images', 'js',
            'css', 'cdn', 'download', 'video', 'stream', 'vpn', 'remote', 'web',
            'secure', 'portal', 'account', 'login', 'auth', 'dashboard', 'stats',
            'monitor', 'status', 'backend', 'internal', 'sip', 'voip', 'xmpp',
            'ldap', 'radius', 'ntp', 'syslog', 'monitoring', 'analytics', 'analytics',
            'beta', 'stage', 'staging', 'dev2', 'test2', 'demo', 'sandbox',
            'es', 'mx', 'mail2', 'smtp2', 'pop3', 'imap4', 'ns4', 'ns5',
            'cpanel2', 'whm2', 'webmail2', 'mail3', 'smtp3'
        ]
        
        # Intentar cargar wordlist desde archivo externo
        wordlist_file = os.path.join(os.path.dirname(__file__), 'wordlist.txt')
        if os.path.exists(wordlist_file):
            try:
                with open(wordlist_file, 'r') as f:
                    extra_words = [line.strip() for line in f if line.strip()]
                    wordlist.extend(extra_words)
                    logger.info(f"✅ Wordlist cargada: {len(wordlist)} subdominios")
            except:
                logger.warning("⚠️ No se pudo cargar wordlist externa, usando lista básica")
        
        return wordlist
    
    def _resolve_subdomain(self, subdomain):
        """Resuelve un subdominio a IP."""
        try:
            full_domain = f"{subdomain}.{self.domain}"
            ip = socket.gethostbyname(full_domain)
            return full_domain, ip
        except:
            return None, None
    
    def _dns_zone_transfer(self):
        """Intenta hacer transferencia de zona DNS."""
        try:
            resolver = dns.resolver.Resolver()
            resolver.nameservers = ['8.8.8.8', '1.1.1.1']
            
            # Intentar obtener el NS del dominio
            try:
                ns_records = resolver.resolve(self.domain, 'NS')
                ns_server = str(ns_records[0]).rstrip('.')
            except:
                return []
            
            # Intentar transferencia de zona
            try:
                zone = dns.zone.from_xfr(dns.query.xfr(ns_server, self.domain))
                subdomains = [str(name) for name in zone.nodes.keys() if str(name) != '@']
                if subdomains:
                    logger.info(f"✅ Transferencia de zona exitosa: {len(subdomains)} subdominios encontrados")
                    return subdomains
            except Exception as e:
                logger.debug(f"Transferencia de zona fallida: {e}")
            
            return []
            
        except Exception as e:
            logger.debug(f"Error en transferencia de zona: {e}")
            return []
    
    def _bruteforce_subdomains(self):
        """Fuerza bruta de subdominios usando wordlist."""
        found = []
        total = len(self.wordlist)
        
        logger.info(f"🔍 Iniciando fuerza bruta: {total} subdominios a probar...")
        
        with ThreadPoolExecutor(max_workers=self.threads) as executor:
            futures = {executor.submit(self._resolve_subdomain, sub): sub for sub in self.wordlist}
            
            for i, future in enumerate(as_completed(futures), 1):
                subdomain, ip = future.result()
                if subdomain:
                    found.append((subdomain, ip))
                    logger.info(f"✅ Encontrado: {subdomain} → {ip}")
                
                # Mostrar progreso cada 50 intentos
                if i % 50 == 0:
                    logger.info(f"⏳ Progreso: {i}/{total} ({i*100//total}%)")
        
        return found
    
    def _check_dns_records(self):
        """Verifica registros DNS para descubrir subdominios."""
        found = []
        record_types = ['A', 'AAAA', 'CNAME', 'MX', 'TXT', 'NS', 'SRV']
        
        logger.info("🔍 Verificando registros DNS...")
        
        for record_type in record_types:
            try:
                resolver = dns.resolver.Resolver()
                resolver.nameservers = ['8.8.8.8', '1.1.1.1']
                answers = resolver.resolve(self.domain, record_type)
                
                for answer in answers:
                    if record_type == 'MX':
                        # Extraer subdominios de registros MX
                        mx_domain = str(answer.exchange).rstrip('.')
                        if mx_domain != self.domain and self.domain in mx_domain:
                            sub = mx_domain.replace(f".{self.domain}", "")
                            if sub and sub not in [f[0] for f in found]:
                                found.append((mx_domain, None))
                                logger.info(f"✅ MX encontrado: {mx_domain}")
            except:
                continue
        
        return found
    
    def _check_security_trails(self):
        """Busca subdominios en servicios públicos y fuentes OSINT."""
        found = []
        
        # Verificar en crt.sh (Certificate Transparency)
        try:
            url = f"https://crt.sh/?q=%.{self.domain}&output=json"
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                for entry in data:
                    name = entry.get('name_value', '').lower()
                    if name and self.domain in name:
                        # Limpiar el nombre (puede tener formato de certificado)
                        sub = name.replace(f".{self.domain}", "")
                        if sub and sub not in [f[0] for f in found]:
                            found.append((name, None))
                            logger.info(f"✅ Certificado encontrado: {name}")
        except Exception as e:
            logger.debug(f"Error consultando crt.sh: {e}")
        
        return found
    
    def run(self):
        """Ejecuta el escaneo completo de subdominios."""
        logger.info(f"🐟 Iniciando Fish-recon para: {self.domain}")
        logger.info("=" * 50)
        
        all_subdomains = []
        
        # 1. Transferencia de zona DNS
        if self.use_dns:
            zone_subdomains = self._dns_zone_transfer()
            all_subdomains.extend(zone_subdomains)
        
        # 2. Verificación de registros DNS
        if self.use_dns:
            dns_subdomains = self._check_dns_records()
            all_subdomains.extend(dns_subdomains)
        
        # 3. Fuerza bruta
        if self.use_bruteforce:
            brute_subdomains = self._bruteforce_subdomains()
            all_subdomains.extend(brute_subdomains)
        
        # 4. OSINT y fuentes externas
        osint_subdomains = self._check_security_trails()
        all_subdomains.extend(osint_subdomains)
        
        # Procesar resultados
        results = self._process_results(all_subdomains)
        
        # Guardar resultados
        self._save_results(results)
        
        logger.info("=" * 50)
        logger.info(f"✅ Escaneo completado: {len(results['subdomains'])} subdominios encontrados")
        
        return results
    
    def _process_results(self, subdomains):
        """Procesa y organiza los resultados."""
        unique_subdomains = {}
        
        for item in subdomains:
            if isinstance(item, tuple):
                subdomain, ip = item
            else:
                subdomain = item
                ip = None
            
            # Limpiar subdominio
            if subdomain.endswith('.'):
                subdomain = subdomain[:-1]
            
            # Verificar que sea subdominio del dominio principal
            if not subdomain.endswith(self.domain):
                continue
            
            # Extraer nombre del subdominio
            name = subdomain.replace(f".{self.domain}", "")
            
            # Resolver IP si no se tiene
            if not ip:
                try:
                    ip = socket.gethostbyname(subdomain)
                except:
                    ip = None
            
            unique_subdomains[name] = {
                'full_domain': subdomain,
                'subdomain': name,
                'ip': ip,
                'found_date': datetime.now().isoformat()
            }
        
        return {
            'domain': self.domain,
            'total': len(unique_subdomains),
            'subdomains': list(unique_subdomains.values()),
            'timestamp': datetime.now().isoformat()
        }
    
    def _save_results(self, results):
        """Guarda los resultados en archivos."""
        # Guardar JSON
        json_file = os.path.join(self.output_dir, f"{self.domain}_subdomains.json")
        with open(json_file, 'w') as f:
            json.dump(results, f, indent=2)
        logger.info(f"💾 Resultados guardados en: {json_file}")
        
        # Guardar lista simple de subdominios
        txt_file = os.path.join(self.output_dir, f"{self.domain}_subdomains.txt")
        with open(txt_file, 'w') as f:
            for sub in results['subdomains']:
                f.write(f"{sub['subdomain']}.{self.domain}\n")
        logger.info(f"💾 Lista guardada en: {txt_file}")
        
        # Guardar subdominios con IP
        ips_file = os.path.join(self.output_dir, f"{self.domain}_subdomains_ip.txt")
        with open(ips_file, 'w') as f:
            for sub in results['subdomains']:
                ip = sub.get('ip', 'unknown')
                f.write(f"{sub['full_domain']} -> {ip}\n")
        logger.info(f"💾 Lista con IPs guardada en: {ips_file}")
        
        # Si la base de datos está disponible, guardar resultados
        try:
            from core.database import FishDatabase
            db_path = os.environ.get('THE_BIG_FISH_DB', 'data/fish.db')
            db = FishDatabase(db_path)
            
            # Guardar cada subdominio
            for sub in results['subdomains']:
                db.save_subdomain(
                    domain=self.domain,
                    subdomain=sub['subdomain'],
                    ip=sub.get('ip'),
                    source='fish_recon',
                    metadata={'full_domain': sub['full_domain']}
                )
            
            # Actualizar el escaneo si se ejecuta desde The Big Fish
            if 'THE_BIG_FISH_SCAN_ID' in os.environ:
                scan_id = int(os.environ.get('THE_BIG_FISH_SCAN_ID'))
                db.update_scan(scan_id, status='completed', results=results)
            
            db.close()
        except Exception as e:
            logger.warning(f"No se pudo guardar en base de datos: {e}")

def main():
    """Función principal para ejecución desde línea de comandos."""
    parser = argparse.ArgumentParser(description='Fish-recon - Descubrimiento de subdominios')
    parser.add_argument('--target', required=True, help='Dominio objetivo')
    parser.add_argument('--threads', type=int, default=10, help='Número de hilos (default: 10)')
    parser.add_argument('--output', help='Directorio de salida')
    parser.add_argument('--no-dns', action='store_true', help='Deshabilitar técnicas DNS')
    parser.add_argument('--no-bruteforce', action='store_true', help='Deshabilitar fuerza bruta')
    
    args = parser.parse_args()
    
    # Ejecutar Fish-recon
    recon = FishRecon(
        domain=args.target,
        output_dir=args.output,
        threads=args.threads,
        use_dns=not args.no_dns,
        use_bruteforce=not args.no_bruteforce
    )
    
    results = recon.run()
    
    # Imprimir resumen
    print("\n📊 RESUMEN:")
    print(f"  Dominio: {args.target}")
    print(f"  Subdominios encontrados: {results['total']}")
    print(f"  Resultados guardados en: {recon.output_dir}")
    
    if results['subdomains']:
        print("\n  Subdominios más relevantes:")
        for i, sub in enumerate(results['subdomains'][:10], 1):
            ip = sub.get('ip', 'unknown')
            print(f"    {i}. {sub['full_domain']} -> {ip}")

if __name__ == "__main__":
    main()
