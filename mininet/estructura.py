#!/usr/bin/python

# estructura.py — Topologia Mininet Multi-Sitio con VXLAN
# Autor: Hector Munoz Rubio
# TFG — Microsegmentacion de red en entornos SDN

from mininet.topo import Topo
from mininet.net import Mininet
from mininet.node import RemoteController, OVSKernelSwitch
from mininet.cli import CLI
from mininet.log import setLogLevel, info
import time

class MultiSiteVXLANTopo(Topo):
    def build(self):

        # ── SITIO A ──────────────────────────────────────────────────────────
        s1 = self.addSwitch('s1', protocols='OpenFlow13')  # Core A
        s2 = self.addSwitch('s2', protocols='OpenFlow13')  # Usuarios A
        s3 = self.addSwitch('s3', protocols='OpenFlow13')  # DC-A (VTEP-A)
        s4 = self.addSwitch('s4', protocols='OpenFlow13')  # DMZ-A

        self.addLink(s1, s2)
        self.addLink(s1, s3)
        self.addLink(s1, s4)

        # Ventas A — 10.0.1.x
        for i in range(1, 3):
            h = self.addHost(f'hv{i}', ip=f'10.0.1.{i}/24',
                            mac=f'00:00:00:01:01:0{i}',
                            defaultRoute='via 10.0.1.254')
            self.addLink(h, s2)

        # IT A — 10.0.2.x
        for i in range(1, 3):
            h = self.addHost(f'hit{i}', ip=f'10.0.2.{i}/24',
                            mac=f'00:00:00:01:02:0{i}',
                            defaultRoute='via 10.0.2.254')
            self.addLink(h, s2)

        # DC-A — 10.0.10.x
        srv_web = self.addHost('srv_web', ip='10.0.10.80/24',
                            mac='00:00:00:01:10:80',
                            defaultRoute='via 10.0.10.254')
        self.addLink(srv_web, s3)

        # DMZ-A — 10.0.66.x
        attacker = self.addHost('attacker', ip='10.0.66.66/24',
                                mac='00:00:00:01:66:66',
                                defaultRoute='via 10.0.66.254')
        honeypot = self.addHost('honeypot', ip='10.0.66.77/24',
                                mac='00:00:00:01:66:77',
                                defaultRoute='via 10.0.66.254')
        self.addLink(attacker, s4)
        self.addLink(honeypot, s4)

        # ── SITIO B ──────────────────────────────────────────────────────────
        s5 = self.addSwitch('s5', protocols='OpenFlow13')  # Core B
        s6 = self.addSwitch('s6', protocols='OpenFlow13')  # DC-B (VTEP-B)
        s7 = self.addSwitch('s7', protocols='OpenFlow13')  # Usuarios B
        s8 = self.addSwitch('s8', protocols='OpenFlow13')  # DMZ-B

        self.addLink(s5, s6)
        self.addLink(s5, s7)
        self.addLink(s5, s8)

        # DC-B — 10.0.10.x (misma subred lógica que DC-A, unida por VXLAN)
        srv_db = self.addHost('srv_db', ip='10.0.10.33/24',
                            mac='00:00:00:02:10:33',
                            defaultRoute='via 10.0.10.254')
        backup = self.addHost('backup', ip='10.0.10.50/24',
                            mac='00:00:00:02:10:50',
                            defaultRoute='via 10.0.10.254')
        self.addLink(srv_db, s6)
        self.addLink(backup, s6)

        # Ventas B — 10.0.1.x
        for i in range(3, 5):
            h = self.addHost(f'hv{i}', ip=f'10.0.1.{i}/24',
                            mac=f'00:00:00:02:01:0{i}',
                            defaultRoute='via 10.0.1.254')
            self.addLink(h, s7)

        # IT B — 10.0.2.x
        for i in range(3, 5):
            h = self.addHost(f'hit{i}', ip=f'10.0.2.{i}/24',
                            mac=f'00:00:00:02:02:0{i}',
                            defaultRoute='via 10.0.2.254')
            self.addLink(h, s7)

        # DMZ-B — 10.0.66.x
        honeypot2 = self.addHost('honeypot2', ip='10.0.66.78/24',
                                mac='00:00:00:02:66:78',
                                defaultRoute='via 10.0.66.254')
        ids = self.addHost('ids', ip='10.0.66.90/24',
                        mac='00:00:00:02:66:90',
                        defaultRoute='via 10.0.66.254')
        self.addLink(honeypot2, s8)
        self.addLink(ids, s8)

        # ── ENLACE INTER-SITIO (underlay) ────────────────────────────────────
        self.addLink(s1, s5)


def setup_vxlan(net):
    """Crea el túnel VXLAN OVS entre DC-A (s3) y DC-B (s6)."""
    s1 = net.get('s1')
    s3 = net.get('s3')
    s5 = net.get('s5')
    s6 = net.get('s6')

    VTEP_A = '192.168.100.10'
    VTEP_B = '192.168.100.20'

    s1.cmd('ip addr add 192.168.100.1/30 dev s1-eth4')
    s5.cmd('ip addr add 192.168.100.2/30 dev s5-eth4')
    s3.cmd(f'ip addr add {VTEP_A}/32 dev lo')
    s6.cmd(f'ip addr add {VTEP_B}/32 dev lo')
    s3.cmd(f'ip route add {VTEP_B}/32 via 192.168.100.2')
    s6.cmd(f'ip route add {VTEP_A}/32 via 192.168.100.1')

    s3.cmd('ovs-vsctl del-port s3 vxlan_dc 2>/dev/null; true')
    s3.cmd(
        f'ovs-vsctl add-port s3 vxlan_dc '
        f'-- set interface vxlan_dc type=vxlan '
        f'options:remote_ip={VTEP_B} '
        f'options:local_ip={VTEP_A} '
        f'options:key=100 '
        f'options:dst_port=4789'
    )

    s6.cmd('ovs-vsctl del-port s6 vxlan_dc 2>/dev/null; true')
    s6.cmd(
        f'ovs-vsctl add-port s6 vxlan_dc '
        f'-- set interface vxlan_dc type=vxlan '
        f'options:remote_ip={VTEP_A} '
        f'options:local_ip={VTEP_B} '
        f'options:key=100 '
        f'options:dst_port=4789'
    )

    info('\n*** VXLAN VNI=100 activo: s3 (DC-A) <──> s6 (DC-B)\n')
    info('    VTEP-A: 192.168.100.10  |  VTEP-B: 192.168.100.20\n\n')


def runNet():
    topo = MultiSiteVXLANTopo()

    net = Mininet(
        topo=topo,
        controller=lambda name: RemoteController(name, ip='ryu', port=6633),
        switch=OVSKernelSwitch,
        autoSetMacs=True
    )

    net.start()
    setup_vxlan(net)

    info('*** Zonas: Ventas(1.x) IT(2.x) DC(10.x) DMZ(66.x)\n')
    info('*** Sitio A: s1-s4  |  Sitio B: s5-s8\n')
    
    # 1. IMPORTACIÓN Y ARRANQUE DE API (Antes del CLI)
    try:
        from servidor_api import start_api
        info('*** Iniciando API REST en puerto 5000...\n')
        start_api(net, port=5000)
        time.sleep(2) # Espera para que Flask levante el socket
    except ImportError:
        info('*** Error: No se pudo importar servidor_api.py\n')
    except Exception as e:
        info(f'*** Error iniciando API: {e}\n')

    info('*** Mininet listo. Puedes usar el Dashboard.\n\n')

    # 2. LANZAR CLI (Bloquea la ejecución hasta que salgas)
    CLI(net)

    # 3. PARADA
    net.stop()


if __name__ == '__main__':
    setLogLevel('info')
    runNet()
