# firewall.py — Controlador SDN con Microsegmentacion Stateful
# Autor: Hector Munoz Rubio
# TFG — Microsegmentacion de red en entornos SDN
#
# Copyright (C) 2011 Nippon Telegraph and Telephone Corporation.
# Adaptado para topologia multi-sitio con VXLAN
#
# Licensed under the Apache License, Version 2.0

from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.lib.packet import packet, ethernet, ether_types, ipv4, arp, tcp, udp, icmp
import sqlite3
import socket
import struct
import json
import time
import os
from datetime import datetime


class SimpleSwitch13(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    # ─────────────────────────────────────────────────────────────────────────
    # IDs de switches por sitio — usados para logs y decisiones de reenvío
    # ─────────────────────────────────────────────────────────────────────────
    SITE_A_SWITCHES = {1, 2, 3, 4}   # s1=Core-A, s2=Usuarios-A, s3=DC-A, s4=DMZ-A
    SITE_B_SWITCHES = {5, 6, 7, 8}   # s5=Core-B, s6=DC-B,       s7=Usuarios-B, s8=DMZ-B

    def __init__(self, *args, **kwargs):
        super(SimpleSwitch13, self).__init__(*args, **kwargs)
        self.mac_to_port = {}
        
        # Crear directorio data si no existe (por si no se monta correctamente)
        os.makedirs('data', exist_ok=True)
        self.db_name = 'data/log_firewall.db'
        self.init_db()

        # Tabla stateful: 5-tupla → timestamp último paquete
        self.active_connections = {}

        # --- INICIO DEL CAMBIO ---
        # Calculamos la ruta absoluta al directorio donde está guardado ESTE script
        directorio_actual = os.path.dirname(os.path.abspath(__file__))
        ruta_config = os.path.join(directorio_actual, 'config_politicas.json')
        
        # Le pasamos la ruta absoluta al método load_config
        self.load_config(ruta_config)
        # --- FIN DEL CAMBIO ---

    # =========================================================================
    # CARGA DE CONFIGURACIÓN
    # =========================================================================

    def load_config(self, config_path):
        try:
            # Ahora config_path contiene la ruta completa y exacta
            with open(config_path, 'r') as f:
                config = json.load(f)

            self.host_macs    = config['host_macs']
            self.host_groups  = config['host_groups']
            self.allowed_policies = [tuple(p) for p in config['allowed_policies']]
            self.routing_table = {int(k): v for k, v in config['routing_table'].items()}
            self.host_to_port  = {int(k): v for k, v in config.get('host_to_port', {}).items()}

            self.logger.info("✅ Config cargada: %d políticas, %d hosts, %d switches",
                             len(self.allowed_policies),
                             len(self.host_macs),
                             len(self.routing_table))
        except FileNotFoundError:
            self.logger.error("❌ No se encontró %s — usando valores por defecto", config_path)
            self._default_config()
        except Exception as e:
            self.logger.error("❌ Error cargando config: %s", e)
            self._default_config()

    def _default_config(self):
        """
        Configuración embebida para topología multi-sitio.
        Sitio A: s1(Core), s2(Usuarios), s3(DC-A/VTEP-A), s4(DMZ-A)
        Sitio B: s5(Core), s6(DC-B/VTEP-B), s7(Usuarios-B), s8(DMZ-B)
        """

        # ── MACs de todos los hosts ───────────────────────────────────────────
        self.host_macs = {
            # Sitio A
            '10.0.1.1':   '00:00:00:01:01:01',
            '10.0.1.2':   '00:00:00:01:01:02',
            '10.0.2.1':   '00:00:00:01:02:01',
            '10.0.2.2':   '00:00:00:01:02:02',
            '10.0.10.80': '00:00:00:01:10:80',
            '10.0.66.66': '00:00:00:01:66:66',
            '10.0.66.77': '00:00:00:01:66:77',
            # Sitio B
            '10.0.1.3':   '00:00:00:02:01:03',
            '10.0.1.4':   '00:00:00:02:01:04',
            '10.0.2.3':   '00:00:00:02:02:03',
            '10.0.2.4':   '00:00:00:02:02:04',
            '10.0.10.33': '00:00:00:02:10:33',
            '10.0.10.50': '00:00:00:02:10:50',
            '10.0.66.78': '00:00:00:02:66:78',
            '10.0.66.90': '00:00:00:02:66:90',
        }

        # ── Grupos de seguridad ───────────────────────────────────────────────
        # Los grupos son LÓGICOS — no dependen del sitio físico.
        # VENTAS agrupa hv1-hv4, IT agrupa hit1-hit4, etc.
        self.host_groups = {
            # Sitio A
            '10.0.1.1':   'VENTAS',
            '10.0.1.2':   'VENTAS',
            '10.0.2.1':   'IT',
            '10.0.2.2':   'IT',
            '10.0.10.80': 'WEB_SERVER',
            '10.0.66.66': 'ATTACKER',
            '10.0.66.77': 'HONEYPOT',
            # Sitio B
            '10.0.1.3':   'VENTAS',
            '10.0.1.4':   'VENTAS',
            '10.0.2.3':   'IT',
            '10.0.2.4':   'IT',
            '10.0.10.33': 'DB_SERVER',
            '10.0.10.50': 'DB_SERVER',
            '10.0.66.78': 'HONEYPOT',
            '10.0.66.90': 'IDS',
        }

        # ── Políticas permitidas (src_grupo, dst_grupo) ───────────────────────
        # Simétricas donde tiene sentido, asimétricas donde no.
        self.allowed_policies = [
            # Intra-zona (mismo grupo, cualquier sitio)
            ('VENTAS',     'VENTAS'),
            ('IT',         'IT'),
            ('DB_SERVER',  'DB_SERVER'),   # replicación entre srv_db y backup
            # Acceso de usuarios a servidores
            ('VENTAS',     'WEB_SERVER'),
            ('IT',         'WEB_SERVER'),
            ('IT',         'DB_SERVER'),
            # IT puede administrar cualquier zona
            ('IT',         'VENTAS'),
            ('IT',         'HONEYPOT'),
            ('IT',         'IDS'),
            # IDS puede recibir tráfico de cualquier zona (monitorización)
            ('VENTAS',     'IDS'),
            ('WEB_SERVER', 'IDS'),
            ('DB_SERVER',  'IDS'),
            ('ATTACKER',   'HONEYPOT'),    # el atacante puede llegar al honeypot
        ]

        # ── Tabla de rutas por switch ─────────────────────────────────────────
        # Formato: { dpid: { 'red/máscara': puerto_salida } }
        #
        # Diagrama de puertos (referencia):
        #   s1: p1=s2, p2=s3, p3=s4, p4=s5(inter-sitio)
        #   s2: p1=s1, p2-p5=hosts Ventas/IT
        #   s3: p1=s1, p2=srv_web
        #   s4: p1=s1, p2=attacker, p3=honeypot
        #   s5: p1=s1(inter-sitio), p2=s6, p3=s7, p4=s8
        #   s6: p1=s5, p2=srv_db, p3=backup
        #   s7: p1=s5, p2-p5=hosts Ventas/IT
        #   s8: p1=s5, p2=honeypot2, p3=ids
        #
        # NOTA: los números de puerto exactos los asigna Mininet al arrancar.
        # Puedes verificarlos con: s1 ovs-ofctl show s1 -O OpenFlow13
        # y ajustar este diccionario o el JSON de configuración.

        self.routing_table = {
            # Core A — conecta con todos los switches del sitio A y con s5
            1: {
                '10.0.1.0/24':  1,   # → s2 (Usuarios A)
                '10.0.2.0/24':  1,   # → s2 (IT A)
                '10.0.10.0/24': 2,   # → s3 (DC-A)
                '10.0.66.0/24': 3,   # → s4 (DMZ-A)
                # Tráfico hacia sitio B: por el enlace inter-sitio (puerto 4 → s5)
                # Las subredes de B se alcanzan también vía sus propios cores,
                # pero desde s1 todo tráfico hacia B sale por p4.
            },
            # Usuarios A — solo conoce su propia subred y el uplink al core
            2: {
                '10.0.10.0/24': 1,   # → s1 (uplink a core A)
                '10.0.66.0/24': 1,
                '10.0.1.0/24':  1,   # tráfico intra-ventas pasa por core
                '10.0.2.0/24':  1,
            },
            # DC-A — srv_web local + uplink; tráfico a DC-B viaja por VXLAN
            3: {
                '10.0.1.0/24':  1,   # → s1
                '10.0.2.0/24':  1,
                '10.0.66.0/24': 1,
                # 10.0.10.33 y 10.0.10.50 están en DC-B — accesibles por VXLAN
                # OVS reenvía automáticamente por el puerto vxlan_dc cuando
                # el destino no está en la tabla MAC local de s3.
            },
            # DMZ-A — attacker y honeypot, uplink al core
            4: {
                '10.0.1.0/24':  1,   # → s1
                '10.0.2.0/24':  1,
                '10.0.10.0/24': 1,
            },
            # Core B — simétrico al Core A
            5: {
                '10.0.10.0/24': 1,   # → s6 (DC-B)
                '10.0.66.0/24': 3,   # → s8 (DMZ-B)
                '10.0.1.0/24':  2,   # → s7 (Usuarios B)
                '10.0.2.0/24':  2,
                # Tráfico hacia sitio A: por enlace inter-sitio (puerto 4 → s1)
            },
            # DC-B — srv_db y backup locales + uplink
            6: {
                '10.0.1.0/24':  1,   # → s5
                '10.0.2.0/24':  1,
                '10.0.66.0/24': 1,
                # 10.0.10.80 está en DC-A — accesible por VXLAN (puerto vxlan_dc)
            },
            # Usuarios B — simétrico a Usuarios A
            7: {
                '10.0.10.0/24': 1,   # → s5
                '10.0.66.0/24': 1,
                '10.0.1.0/24':  1,
                '10.0.2.0/24':  1,
            },
            # DMZ-B — honeypot2 e IDS, uplink al core B
            8: {
                '10.0.1.0/24':  1,   # → s5
                '10.0.2.0/24':  1,
                '10.0.10.0/24': 1,
            },
        }

        # ── Puertos directos a hosts por switch ───────────────────────────────
        # Permite reenvío directo sin consultar routing_table.
        # Mininet asigna puertos dinámicamente; ajustar tras arrancar con:
        #   s2 ovs-ofctl show s2 -O OpenFlow13
        self.host_to_port = {
            2: {   # s2 — Usuarios A
                '10.0.1.1': 2, '10.0.1.2': 3,
                '10.0.2.1': 4, '10.0.2.2': 5,
            },
            3: {   # s3 — DC-A
                '10.0.10.80': 2,
            },
            4: {   # s4 — DMZ-A
                '10.0.66.66': 2, '10.0.66.77': 3,
            },
            6: {   # s6 — DC-B
                '10.0.10.33': 2, '10.0.10.50': 3,
            },
            7: {   # s7 — Usuarios B
                '10.0.1.3': 2, '10.0.1.4': 3,
                '10.0.2.3': 4, '10.0.2.4': 5,
            },
            8: {   # s8 — DMZ-B
                '10.0.66.78': 2, '10.0.66.90': 3,
            },
        }

    # =========================================================================
    # BASE DE DATOS
    # =========================================================================

    def init_db(self):
        conn = sqlite3.connect(self.db_name, timeout=20.0)
        c = conn.cursor()
        c.execute('PRAGMA journal_mode=WAL;') # Evitar database locked
        c.execute('''CREATE TABLE IF NOT EXISTS logs (
                        id         INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp  TEXT,
                        site       TEXT,
                        dpid       INTEGER,
                        src_ip     TEXT,
                        src_group  TEXT,
                        dst_ip     TEXT,
                        dst_group  TEXT,
                        action     TEXT
                     )''')
        conn.commit()
        conn.close()

    def log_to_db(self, dpid, src_ip, src_group, dst_ip, dst_group, action):
        site = 'A' if dpid in self.SITE_A_SWITCHES else 'B'
        conn = sqlite3.connect(self.db_name, timeout=20.0)
        c = conn.cursor()
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        c.execute(
            "INSERT INTO logs (timestamp, site, dpid, src_ip, src_group, "
            "dst_ip, dst_group, action) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (now, site, dpid, src_ip, src_group, dst_ip, dst_group, action)
        )
        conn.commit()
        conn.close()

    # =========================================================================
    # FIREWALL STATEFUL
    # =========================================================================

    def check_policy(self, src_g, dst_g):
        return (src_g, dst_g) in self.allowed_policies

    def _get_flow_tuple(self, pkt, src_ip, dst_ip):
        tcp_pkt = pkt.get_protocol(tcp.tcp)
        if tcp_pkt:
            return (6, src_ip, tcp_pkt.src_port, dst_ip, tcp_pkt.dst_port)
        udp_pkt = pkt.get_protocol(udp.udp)
        if udp_pkt:
            return (17, src_ip, udp_pkt.src_port, dst_ip, udp_pkt.dst_port)
        icmp_pkt = pkt.get_protocol(icmp.icmp)
        if icmp_pkt:
            icmp_id = icmp_pkt.data.id if (icmp_pkt.data and hasattr(icmp_pkt.data, 'id')) else 0
            return (1, src_ip, icmp_id, dst_ip, icmp_id)
        return (0, src_ip, 0, dst_ip, 0)

    def _get_reverse_tuple(self, flow_tuple):
        proto, src_ip, src_port, dst_ip, dst_port = flow_tuple
        return (proto, dst_ip, dst_port, src_ip, src_port)

    def _cleanup_connections(self, now, timeout=60):
        expired = [k for k, t in self.active_connections.items() if now - t > timeout]
        for k in expired:
            del self.active_connections[k]
        if expired:
            self.logger.info("🧹 Limpiadas %d conexiones expiradas", len(expired))

    def is_allowed(self, src_ip, dst_ip, src_g, dst_g, pkt, dpid):
        """
        Firewall stateful con 5-tupla.
        La decisión es global (no por sitio): la tabla de conexiones activas
        es compartida entre todos los switches, lo que permite que la respuesta
        de un servidor en el sitio B se autorice aunque llegue por s6 y no s3.
        """
        now = time.time()
        flow_tuple   = self._get_flow_tuple(pkt, src_ip, dst_ip)
        reverse_tuple = self._get_reverse_tuple(flow_tuple)
        site = 'A' if dpid in self.SITE_A_SWITCHES else 'B'

        self._cleanup_connections(now)

        # Caso 1: política explícita → nueva conexión autorizada
        if self.check_policy(src_g, dst_g):
            self.active_connections[flow_tuple] = now
            self.logger.info("🟢 [S%d·Sitio%s] ALLOW %s(%s) → %s(%s)",
                             dpid, site, src_ip, src_g, dst_ip, dst_g)
            return True

        # Caso 2: respuesta a conexión activa (tupla inversa)
        if reverse_tuple in self.active_connections:
            self.active_connections[reverse_tuple] = now
            self.active_connections[flow_tuple]    = now
            self.logger.info("🔵 [S%d·Sitio%s] STATEFUL %s(%s) → %s(%s)",
                             dpid, site, src_ip, src_g, dst_ip, dst_g)
            return True

        # Caso 3: bloqueado
        self.logger.info("🔴 [S%d·Sitio%s] BLOCK %s(%s) → %s(%s)",
                         dpid, site, src_ip, src_g, dst_ip, dst_g)
        return False

    # =========================================================================
    # ARP
    # =========================================================================

    def reply_arp(self, datapath, eth, arp_pkt, in_port):
        """Responde ARPs hacia .254 (gateway virtual) con una MAC ficticia."""
        router_mac = '00:00:00:00:00:fe'
        ofproto = datapath.ofproto
        parser  = datapath.ofproto_parser

        pkt = packet.Packet()
        pkt.add_protocol(ethernet.ethernet(
            ethertype=eth.ethertype, dst=eth.src, src=router_mac))
        pkt.add_protocol(arp.arp(
            opcode=arp.ARP_REPLY,
            src_mac=router_mac, src_ip=arp_pkt.dst_ip,
            dst_mac=arp_pkt.src_mac, dst_ip=arp_pkt.src_ip))
        pkt.serialize()

        actions = [parser.OFPActionOutput(in_port)]
        out = parser.OFPPacketOut(
            datapath=datapath, buffer_id=ofproto.OFP_NO_BUFFER,
            in_port=ofproto.OFPP_CONTROLLER, actions=actions, data=pkt.data)
        datapath.send_msg(out)

    # =========================================================================
    # UTILIDADES
    # =========================================================================

    def ip_in_network(self, ip, network):
        try:
            ip_int  = struct.unpack('!L', socket.inet_aton(ip))[0]
            net, bits = network.split('/')
            net_int = struct.unpack('!L', socket.inet_aton(net))[0]
            mask    = (0xFFFFFFFF << (32 - int(bits))) & 0xFFFFFFFF
            return (ip_int & mask) == (net_int & mask)
        except Exception:
            return False

    def get_site(self, dpid):
        return 'A' if dpid in self.SITE_A_SWITCHES else 'B'

    # =========================================================================
    # OPENFLOW — instalación de flows
    # =========================================================================

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        datapath = ev.msg.datapath
        ofproto  = datapath.ofproto
        parser   = datapath.ofproto_parser
        # Table-miss: todo lo que no tenga flow sube al controlador
        match   = parser.OFPMatch()
        actions = [parser.OFPActionOutput(ofproto.OFPP_CONTROLLER,
                                          ofproto.OFPCML_NO_BUFFER)]
        self.add_flow(datapath, 0, match, actions)
        self.logger.info("🔌 Switch S%d conectado (Sitio %s)",
                         datapath.id, self.get_site(datapath.id))

    def add_flow(self, datapath, priority, match, actions, buffer_id=None):
        ofproto = datapath.ofproto
        parser  = datapath.ofproto_parser
        inst    = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)]
        kwargs  = dict(datapath=datapath, priority=priority,
                       match=match, instructions=inst)
        if buffer_id:
            kwargs['buffer_id'] = buffer_id
        datapath.send_msg(parser.OFPFlowMod(**kwargs))

    # =========================================================================
    # PACKET-IN — lógica principal
    # =========================================================================

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def _packet_in_handler(self, ev):
        msg      = ev.msg
        datapath = msg.datapath
        ofproto  = datapath.ofproto
        parser   = datapath.ofproto_parser
        in_port  = msg.match['in_port']
        dpid     = datapath.id

        pkt = packet.Packet(msg.data)
        eth = pkt.get_protocols(ethernet.ethernet)[0]
        dst = eth.dst
        src = eth.src

        # Aprender MAC origen
        self.mac_to_port.setdefault(dpid, {})
        self.mac_to_port[dpid][src] = in_port

        # Ignorar LLDP e IPv6
        if eth.ethertype in [ether_types.ETH_TYPE_LLDP, ether_types.ETH_TYPE_IPV6]:
            return

        # ── ARP ───────────────────────────────────────────────────────────────
        arp_pkt = pkt.get_protocol(arp.arp)
        if arp_pkt:
            if arp_pkt.opcode == arp.ARP_REQUEST and arp_pkt.dst_ip.endswith('.254'):
                self.reply_arp(datapath, eth, arp_pkt, in_port)
                return
            self._normal_switching(msg, eth, datapath, in_port)
            return

        # ── IPv4 ──────────────────────────────────────────────────────────────
        ip_pkt = pkt.get_protocol(ipv4.ipv4)
        if not ip_pkt:
            return

        src_ip = ip_pkt.src
        dst_ip = ip_pkt.dst
        src_g  = self.host_groups.get(src_ip, 'DESCONOCIDO')
        dst_g  = self.host_groups.get(dst_ip, 'DESCONOCIDO')

        self.logger.info("📦 [S%d·Sitio%s] p%d | %s(%s) → %s(%s)",
                         dpid, self.get_site(dpid), in_port,
                         src_ip, src_g, dst_ip, dst_g)

        # ── Filtrar tráfico de plano de control (inter-sitio) ─────────────────
        # Las IPs 192.168.100.x son interfaces de switches, no hosts finales.
        # No se evalúan en microsegmentación (opera solo sobre plano de datos).
        if src_ip.startswith('192.168.100.') or dst_ip.startswith('192.168.100.'):
            return

        # ── Decisión de firewall ──────────────────────────────────────────────
        if not self.is_allowed(src_ip, dst_ip, src_g, dst_g, pkt, dpid):
            self.log_to_db(dpid, src_ip, src_g, dst_ip, dst_g, 'BLOQUEADO')
            return   # paquete descartado silenciosamente

        # Solo logueamos en el switch de acceso (donde entra el host),
        # no en cada switch intermedio, para evitar entradas duplicadas.
        if dpid not in {1, 5}:
            self.log_to_db(dpid, src_ip, src_g, dst_ip, dst_g, 'PERMITIDO')

        # ── Calcular puerto de salida ─────────────────────────────────────────
        out_port = None

        # 1. Host directamente conectado a este switch
        if dpid in self.host_to_port and dst_ip in self.host_to_port[dpid]:
            out_port = self.host_to_port[dpid][dst_ip]
            self.logger.info("📍 [S%d] LOCAL %s → p%d", dpid, dst_ip, out_port)

        # 2. Ruta estática hacia la red del destino
        if out_port is None and dpid in self.routing_table:
            for network, port in self.routing_table[dpid].items():
                if self.ip_in_network(dst_ip, network):
                    out_port = port
                    self.logger.info("🔀 [S%d] RUTA %s → %s → p%d",
                                     dpid, dst_ip, network, out_port)
                    break

        # 3. Tabla MAC aprendida como último recurso
        if out_port is None:
            out_port = self.mac_to_port[dpid].get(dst, ofproto.OFPP_FLOOD)
            if out_port == ofproto.OFPP_FLOOD:
                self.logger.warning("⚠️ [S%d] SIN RUTA para %s — flood", dpid, dst_ip)

        # ── Construir acciones ────────────────────────────────────────────────
        actions = []

        # Reescribir MAC destino si conocemos la del host final.
        # Esto es necesario porque los hosts tienen como gateway .254,
        # que tiene una MAC ficticia; hay que sustituirla por la MAC real
        # del host destino antes de enviarlo al puerto correcto.
        if dst_ip in self.host_macs:
            actions.append(parser.OFPActionSetField(eth_dst=self.host_macs[dst_ip]))

        actions.append(parser.OFPActionOutput(out_port))

        # Instalar flow permanente solo para tráfico intra-grupo
        # (mismo grupo de seguridad). El tráfico inter-grupo siempre
        # sube al controlador para que el stateful pueda evaluarlo.
        if src_g == dst_g and src_g != 'DESCONOCIDO':
            match = parser.OFPMatch(eth_type=0x0800,
                                    ipv4_src=src_ip, ipv4_dst=dst_ip)
            self.add_flow(datapath, 1, match, actions)
            self.logger.info("📝 [S%d] Flow intra-grupo (%s): %s → %s",
                             dpid, src_g, src_ip, dst_ip)
        else:
            self.logger.info("🔍 [S%d] Sin flow (inter-grupo stateful): %s → %s",
                             dpid, src_ip, dst_ip)

        # ── Enviar paquete ────────────────────────────────────────────────────
        out = parser.OFPPacketOut(
            datapath=datapath,
            buffer_id=ofproto.OFP_NO_BUFFER,
            in_port=in_port,
            actions=actions,
            data=msg.data
        )
        datapath.send_msg(out)

    # =========================================================================
    # SWITCHING NORMAL (para ARP y tráfico no-IP)
    # =========================================================================

    def _normal_switching(self, msg, eth, datapath, in_port):
        parser  = datapath.ofproto_parser
        ofproto = datapath.ofproto
        dst     = eth.dst
        dpid    = datapath.id

        self.mac_to_port.setdefault(dpid, {})

        out_port = self.mac_to_port[dpid].get(dst, ofproto.OFPP_FLOOD)

        actions = [parser.OFPActionOutput(out_port)]

        if out_port != ofproto.OFPP_FLOOD:
            match = parser.OFPMatch(in_port=in_port, eth_dst=dst, eth_src=eth.src,
                                    eth_type=ether_types.ETH_TYPE_ARP)
            self.add_flow(datapath, 1, match, actions)

        data = msg.data if msg.buffer_id == ofproto.OFP_NO_BUFFER else None
        out  = parser.OFPPacketOut(
            datapath=datapath, buffer_id=msg.buffer_id,
            in_port=in_port, actions=actions, data=data)
        datapath.send_msg(out)
