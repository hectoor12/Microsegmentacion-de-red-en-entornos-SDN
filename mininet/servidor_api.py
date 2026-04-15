# servidor_api.py — API REST para ejecutar comandos en hosts Mininet
# Autor: Hector Munoz Rubio
# TFG — Microsegmentacion de red en entornos SDN

"""
servidor_api.py — API REST ligera para ejecutar comandos en hosts Mininet.

Se lanza como hilo daemon desde estructura2.py, recibiendo la referencia
a la instancia de Mininet.  El dashboard de Streamlit consume el endpoint
POST /ping para lanzar pings entre hosts.
"""

from flask import Flask, request, jsonify
import json
import threading

app = Flask(__name__)

# Referencia global a la red Mininet (se inyecta al iniciar)
_net = None

# Mecanismo de bloqueo (Deadlock prevention) para Mininet 
_mn_lock = threading.Lock()

# Mapa nombre ↔ IP  (se construye desde config_politicas.json)
_name_to_ip = {}
_ip_to_name = {}


def _load_host_map():
    """Carga el mapa desde config_politicas.json y los nombres de estructura2."""
    global _name_to_ip, _ip_to_name

    # Mapa explícito nombre → IP (coincide con estructura2.py)
    mapping = {
        "hv1":       "10.0.1.1",
        "hv2":       "10.0.1.2",
        "hit1":      "10.0.2.1",
        "hit2":      "10.0.2.2",
        "srv_web":   "10.0.10.80",
        "attacker":  "10.0.66.66",
        "honeypot":  "10.0.66.77",
        "hv3":       "10.0.1.3",
        "hv4":       "10.0.1.4",
        "hit3":      "10.0.2.3",
        "hit4":      "10.0.2.4",
        "srv_db":    "10.0.10.33",
        "backup":    "10.0.10.50",
        "honeypot2": "10.0.66.78",
        "ids":       "10.0.66.90",
    }

    _name_to_ip = mapping
    _ip_to_name = {v: k for k, v in mapping.items()}


def _resolve(identifier):
    """Resuelve un identificador (nombre o IP) a (nombre_host, ip)."""
    # Es una IP directa
    if identifier in _ip_to_name:
        return _ip_to_name[identifier], identifier
    # Es un nombre de host
    if identifier in _name_to_ip:
        return identifier, _name_to_ip[identifier]
    return None, None


# ──────────────────────────────────────────────────────────────────────────
#  ENDPOINTS
# ──────────────────────────────────────────────────────────────────────────

@app.route("/ping", methods=["POST"])
def do_ping():
    """
    POST /ping
    Body JSON: { "src": "srv_web" | "10.0.10.80",
                 "dst": "srv_db"  | "10.0.10.33",
                 "count": 4 }
    """
    if _net is None:
        return jsonify({"ok": False, "error": "Mininet no disponible"}), 503

    data = request.get_json(force=True)
    src_id = data.get("src", "").strip()
    dst_id = data.get("dst", "").strip()
    count = min(max(int(data.get("count", 4)), 1), 20)

    src_name, src_ip = _resolve(src_id)
    dst_name, dst_ip = _resolve(dst_id)

    if src_name is None:
        return jsonify({"ok": False, "error": f"Host origen no reconocido: {src_id}"}), 400
    if dst_name is None:
        return jsonify({"ok": False, "error": f"Host destino no reconocido: {dst_id}"}), 400

    try:
        with _mn_lock:
            host = _net.get(src_name)
            output = host.cmd(f"ping -c {count} -W 1 {dst_ip}")
            
        success = " 0% packet loss" in output
        return jsonify({
            "ok": True,
            "success": success,
            "src": src_name,
            "src_ip": src_ip,
            "dst": dst_name,
            "dst_ip": dst_ip,
            "count": count,
            "output": output,
        })
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/hosts", methods=["GET"])
def list_hosts():
    """GET /hosts — devuelve la lista de hosts disponibles."""
    hosts = []
    for name, ip in sorted(_name_to_ip.items(), key=lambda x: x[1]):
        hosts.append({"name": name, "ip": ip})
    return jsonify(hosts)


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "mininet": _net is not None})


@app.route("/run_tests", methods=["POST"])
def run_tests_endpoint():
    """POST /run_tests — ejecuta la batería completa de microsegmentación."""
    if _net is None:
        return jsonify({"ok": False, "error": "Mininet no disponible"}), 503

    try:
        import io
        import sys
        from test_microsegmentacion import run_tests

        # Capturar stdout para devolver los mensajes
        capture = io.StringIO()
        old_stdout = sys.stdout
        sys.stdout = capture

        with _mn_lock:
            results = run_tests(_net)

        sys.stdout = old_stdout
        output = capture.getvalue()

        # Contar resultados
        total = len(results)
        passed = sum(1 for s, *_ in results if "PASS" in s)
        failed = total - passed

        return jsonify({
            "ok": True,
            "output": output,
            "total": total,
            "passed": passed,
            "failed": failed,
        })
    except Exception as e:
        import sys
        sys.stdout = sys.__stdout__
        return jsonify({"ok": False, "error": str(e)}), 500


# ──────────────────────────────────────────────────────────────────────────
#  ARRANQUE
# ──────────────────────────────────────────────────────────────────────────

def start_api(net, host="0.0.0.0", port=5000):
    """Inicia el servidor Flask en un hilo daemon."""
    global _net
    _net = net
    _load_host_map()

    thread = threading.Thread(
        target=lambda: app.run(host=host, port=port, debug=False, use_reloader=False),
        daemon=True,
    )
    thread.start()
    print(f"*** API Mininet escuchando en http://{host}:{port}")
    return thread
