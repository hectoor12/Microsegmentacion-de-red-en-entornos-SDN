# grafico.py — Topologia SDN Multi-Sitio
# Autor: Hector Munoz Rubio
# TFG — Microsegmentacion de red en entornos SDN

import plotly.graph_objects as go


def build_topology_figure(config=None):
    """
    Construye y devuelve un objeto go.Figure con la topología SDN multi-sitio
    con VXLAN entre DC-A (s3) y DC-B (s6).
    """

    # =====================================================================
    #  NODOS: (display_label, hover_label, grupo, x, y, textpos)
    #  - display_label: texto corto visible junto al nodo
    #  - hover_label:   texto completo al pasar el ratón
    #  - textpos:       posición del texto para evitar solapamientos
    # =====================================================================
    nodes = {
        # Controlador
        'ctrl':  ('Controlador Ryu',   'Controlador Ryu',               'controller',  0.0,   4.5, 'top center'),

        # ── SITIO A ─────────────────────────────────────────────────────
        's1':    ('S1 Core A',         'S1 — Core A',                   'switch',     -5.0,   3.0, 'bottom center'),
        's2':    ('S2 Usuarios A',     'S2 — Usuarios A',              'switch',     -8.5,   2.0, 'bottom center'),
        's3':    ('S3 DC-A',           'S3 — DC-A (VTEP-A)',           'switch',     -5.0,   2.0, 'bottom center'),
        's4':    ('S4 DMZ-A',          'S4 — DMZ-A',                   'switch',     -2.0,   2.0, 'bottom center'),

        # Ventas A — staggered vertically
        'hv1':   ('hv1',    'hv1 — 10.0.1.1 (VENTAS)',    'ventas', -10.0,  1.0, 'bottom center'),
        'hv2':   ('hv2',    'hv2 — 10.0.1.2 (VENTAS)',    'ventas',  -8.5,  0.6, 'bottom center'),
        # IT A
        'hit1':  ('hit1',   'hit1 — 10.0.2.1 (IT)',       'it',      -7.0,  1.0, 'bottom center'),
        'hit2':  ('hit2',   'hit2 — 10.0.2.2 (IT)',       'it',      -5.5,  0.6, 'bottom center'),
        # DC-A
        'web':   ('srv_web','srv_web — 10.0.10.80 (WEB)', 'server',  -4.0,  0.8, 'bottom center'),
        # DMZ-A
        'atk':   ('attacker','attacker — 10.0.66.66',     'threat',  -2.5,  1.0, 'bottom center'),
        'hp1':   ('honeypot','honeypot — 10.0.66.77',     'threat',  -1.0,  0.6, 'bottom center'),

        # ── SITIO B ─────────────────────────────────────────────────────
        's5':    ('S5 Core B',         'S5 — Core B',                  'switch',      5.0,   3.0, 'bottom center'),
        's6':    ('S6 DC-B',           'S6 — DC-B (VTEP-B)',           'switch',      3.5,   2.0, 'bottom center'),
        's7':    ('S7 Usuarios B',     'S7 — Usuarios B',             'switch',      8.5,   2.0, 'bottom center'),
        's8':    ('S8 DMZ-B',          'S8 — DMZ-B',                  'switch',      2.0,   2.0, 'bottom center'),

        # DC-B
        'db':    ('srv_db', 'srv_db — 10.0.10.33 (DB)',   'server',   2.8,   0.6, 'bottom center'),
        'bkp':   ('backup', 'backup — 10.0.10.50 (DB)',   'server',   4.4,   1.0, 'bottom center'),
        # Ventas B
        'hv3':   ('hv3',    'hv3 — 10.0.1.3 (VENTAS)',    'ventas',   6.5,   0.6, 'bottom center'),
        'hv4':   ('hv4',    'hv4 — 10.0.1.4 (VENTAS)',    'ventas',   8.0,   1.0, 'bottom center'),
        # IT B
        'hit3':  ('hit3',   'hit3 — 10.0.2.3 (IT)',       'it',       9.5,   0.6, 'bottom center'),
        'hit4':  ('hit4',   'hit4 — 10.0.2.4 (IT)',       'it',      11.0,   1.0, 'bottom center'),
        # DMZ-B
        'hp2':   ('honeypot2','honeypot2 — 10.0.66.78',   'threat',   1.0,   1.0, 'bottom center'),
        'ids':   ('ids',      'ids — 10.0.66.90 (IDS)',   'threat',   2.5,   0.6, 'bottom center'),
    }

    # =====================================================================
    #  ENLACES FÍSICOS
    # =====================================================================
    edges = [
        # Controlador → Cores
        ('ctrl', 's1'), ('ctrl', 's5'),
        # Sitio A interno
        ('s1', 's2'), ('s1', 's3'), ('s1', 's4'),
        ('s2', 'hv1'), ('s2', 'hv2'), ('s2', 'hit1'), ('s2', 'hit2'),
        ('s3', 'web'),
        ('s4', 'atk'), ('s4', 'hp1'),
        # Sitio B interno
        ('s5', 's6'), ('s5', 's7'), ('s5', 's8'),
        ('s6', 'db'), ('s6', 'bkp'),
        ('s7', 'hv3'), ('s7', 'hv4'), ('s7', 'hit3'), ('s7', 'hit4'),
        ('s8', 'hp2'), ('s8', 'ids'),
    ]

    # =====================================================================
    #  ESTILOS
    # =====================================================================
    style = {
        'controller': dict(color='#FF6B6B', size=42, symbol='square'),
        'switch':     dict(color='#4ECDC4', size=35, symbol='diamond'),
        'ventas':     dict(color='#45B7D1', size=26, symbol='circle'),
        'it':         dict(color='#F39C12', size=26, symbol='circle'),
        'server':     dict(color='#9B59B6', size=26, symbol='circle'),
        'threat':     dict(color='#E74C3C', size=26, symbol='triangle-up'),
    }

    group_labels = {
        'controller': 'Controlador',
        'switch':     'Switches',
        'ventas':     'Ventas',
        'it':         'IT',
        'server':     'Servidores (DC)',
        'threat':     'Seguridad (DMZ)',
    }

    # =====================================================================
    #  TRAZA DE ENLACES FÍSICOS
    # =====================================================================
    edge_x, edge_y = [], []
    for src, dst in edges:
        x0, y0 = nodes[src][3], nodes[src][4]
        x1, y1 = nodes[dst][3], nodes[dst][4]
        edge_x += [x0, x1, None]
        edge_y += [y0, y1, None]

    edge_trace = go.Scatter(
        x=edge_x, y=edge_y,
        line=dict(width=2, color='rgba(150,150,150,0.5)'),
        hoverinfo='none', mode='lines', showlegend=False
    )

    # =====================================================================
    #  ENLACE INTER-SITIO (s1 ↔ s5) — línea gruesa
    # =====================================================================
    wan_trace = go.Scatter(
        x=[nodes['s1'][3], nodes['s5'][3]],
        y=[nodes['s1'][4], nodes['s5'][4]],
        line=dict(width=4, color='#2C3E50'),
        hoverinfo='text',
        hovertext='Enlace Inter-Sitio<br>192.168.100.0/30',
        mode='lines', name='Enlace WAN',
    )

    # =====================================================================
    #  TÚNEL VXLAN (s3 ↔ s6) — línea discontinua
    # =====================================================================
    vxlan_trace = go.Scatter(
        x=[nodes['s3'][3], nodes['s6'][3]],
        y=[nodes['s3'][4], nodes['s6'][4]],
        line=dict(width=3, color='#E67E22', dash='dash'),
        hoverinfo='text',
        hovertext='VXLAN VNI=100<br>UDP 4789',
        mode='lines', name='VXLAN VNI=100',
    )

    # =====================================================================
    #  TRAZAS DE NODOS (agrupados por tipo para leyenda)
    # =====================================================================
    groups_seen = {}
    for nid, (display, hover, group, x, y, tpos) in nodes.items():
        if group not in groups_seen:
            groups_seen[group] = dict(x=[], y=[], display=[], hover=[], tpos=[])
        groups_seen[group]['x'].append(x)
        groups_seen[group]['y'].append(y)
        groups_seen[group]['display'].append(display)
        groups_seen[group]['hover'].append(hover)
        groups_seen[group]['tpos'].append(tpos)

    node_traces = []
    for group, data in groups_seen.items():
        s = style.get(group, style['ventas'])
        # Use the most common textposition for the group
        most_common_tpos = max(set(data['tpos']), key=data['tpos'].count)
        node_traces.append(go.Scatter(
            x=data['x'], y=data['y'],
            mode='markers+text',
            marker=dict(
                size=s['size'], color=s['color'],
                symbol=s['symbol'],
                line=dict(width=2, color='white'),
                opacity=0.95
            ),
            text=data['display'],
            textposition=most_common_tpos,
            textfont=dict(size=9, color='#cbd5e1', family='Inter'),
            name=group_labels.get(group, group),
            hovertext=data['hover'],
            hoverinfo='text',
        ))

    # =====================================================================
    #  ANOTACIONES
    # =====================================================================
    annotations = [
        # Enlace WAN
        dict(x=0.0, y=3.25, text="Enlace Inter-Sitio · 192.168.100.0/30",
             font=dict(size=10, color='#2C3E50'), showarrow=False,
             bgcolor='rgba(44,62,80,0.08)', bordercolor='#2C3E50',
             borderwidth=1, borderpad=4),
        # VXLAN
        dict(x=-0.75, y=1.75, text="VXLAN VNI=100",
             font=dict(size=10, color='#E67E22', family='Arial Black'),
             showarrow=False, bgcolor='rgba(230,126,34,0.1)',
             bordercolor='#E67E22', borderwidth=1, borderpad=4),
        # Sitio labels
        dict(x=-5.5, y=3.55, text="<b>SITIO A</b>",
             font=dict(size=14, color='#60a5fa', family='Inter'),
             showarrow=False),
        dict(x=6.5, y=3.55, text="<b>SITIO B</b>",
             font=dict(size=14, color='#4ade80', family='Inter'),
             showarrow=False),
        # Subnet labels — small, below host area
        dict(x=-9.2, y=0.15, text="10.0.1.0/24", font=dict(size=8, color='#45B7D1'), showarrow=False),
        dict(x=-6.2, y=0.15, text="10.0.2.0/24", font=dict(size=8, color='#F39C12'), showarrow=False),
        dict(x=-4.0, y=0.15, text="10.0.10.0/24", font=dict(size=8, color='#9B59B6'), showarrow=False),
        dict(x=-1.8, y=0.15, text="10.0.66.0/24", font=dict(size=8, color='#E74C3C'), showarrow=False),
        dict(x=3.6, y=0.15, text="10.0.10.0/24", font=dict(size=8, color='#9B59B6'), showarrow=False),
        dict(x=7.2, y=0.15, text="10.0.1.0/24", font=dict(size=8, color='#45B7D1'), showarrow=False),
        dict(x=10.2, y=0.15, text="10.0.2.0/24", font=dict(size=8, color='#F39C12'), showarrow=False),
        dict(x=1.8, y=0.15, text="10.0.66.0/24", font=dict(size=8, color='#E74C3C'), showarrow=False),
    ]

    # =====================================================================
    #  FORMAS — cajas de sitio
    # =====================================================================
    shapes = [
        dict(type='rect', x0=-11.0, y0=0.0, x1=-0.3, y1=3.7,
             line=dict(color='rgba(52,152,219,0.3)', width=2, dash='dot'),
             fillcolor='rgba(52,152,219,0.03)', layer='below'),
        dict(type='rect', x0=0.3, y0=0.0, x1=12.0, y1=3.7,
             line=dict(color='rgba(46,204,113,0.3)', width=2, dash='dot'),
             fillcolor='rgba(46,204,113,0.03)', layer='below'),
    ]

    # =====================================================================
    #  FIGURA FINAL
    # =====================================================================
    fig = go.Figure(
        data=[edge_trace, wan_trace, vxlan_trace] + node_traces,
        layout=go.Layout(
            title=dict(
                text='Topologia SDN Multi-Sitio con Microsegmentacion y VXLAN',
                font=dict(size=18, color='#e2e8f0', family='Inter'),
                x=0.5
            ),
            showlegend=True,
            legend=dict(
                font=dict(size=11, color='#e2e8f0', family='Inter'),
                bgcolor='rgba(17,24,39,0.85)',
                bordercolor='#1e293b', borderwidth=1,
                x=1.02, y=1,
                itemsizing='constant'
            ),
            hovermode='closest',
            xaxis=dict(showgrid=False, zeroline=False,
                       showticklabels=False, range=[-12, 13]),
            yaxis=dict(showgrid=False, zeroline=False,
                       showticklabels=False, range=[-0.2, 5.0]),
            plot_bgcolor='#111827',
            paper_bgcolor='rgba(0,0,0,0)',
            margin=dict(l=20, r=20, t=60, b=20),
            annotations=annotations,
            shapes=shapes,
            height=650,
            )
    )

    return fig


if __name__ == "__main__":
    fig = build_topology_figure()
    fig.show()
