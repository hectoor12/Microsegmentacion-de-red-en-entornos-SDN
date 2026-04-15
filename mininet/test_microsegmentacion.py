# test_microsegmentacion.py — Bateria de pruebas de microsegmentacion SDN
# Autor: Hector Munoz Rubio
# TFG — Microsegmentacion de red en entornos SDN

#!/usr/bin/python
"""
Ejecutar DENTRO de Mininet:
  mininet> py exec(open('test_microsegmentacion.py').read())
  mininet> py run_tests(net)
"""
import time

def run_tests(net):

    # ================================================================
    #  DEFINICIÓN DE TESTS
    # ================================================================

    TESTS = [
        # ──── INTRA-VENTAS (misma zona, debe funcionar) ────
        ("hv1",      "10.0.1.2",   True,  "INTRA-VENTAS",  "hv1 → hv2 (Sitio A)"),
        ("hv2",      "10.0.1.1",   True,  "INTRA-VENTAS",  "hv2 → hv1 (Sitio A)"),
        ("hv1",      "10.0.1.3",   True,  "INTRA-VENTAS",  "hv1 → hv3 (cross-site)"),
        ("hv1",      "10.0.1.4",   True,  "INTRA-VENTAS",  "hv1 → hv4 (cross-site)"),
        ("hv3",      "10.0.1.1",   True,  "INTRA-VENTAS",  "hv3 → hv1 (cross-site)"),
        ("hv3",      "10.0.1.4",   True,  "INTRA-VENTAS",  "hv3 → hv4 (Sitio B)"),
        ("hv4",      "10.0.1.3",   True,  "INTRA-VENTAS",  "hv4 → hv3 (Sitio B)"),

        # ──── INTRA-IT (misma zona, debe funcionar) ────
        ("hit1",     "10.0.2.2",   True,  "INTRA-IT",      "hit1 → hit2 (Sitio A)"),
        ("hit2",     "10.0.2.1",   True,  "INTRA-IT",      "hit2 → hit1 (Sitio A)"),
        ("hit1",     "10.0.2.3",   True,  "INTRA-IT",      "hit1 → hit3 (cross-site)"),
        ("hit3",     "10.0.2.1",   True,  "INTRA-IT",      "hit3 → hit1 (cross-site)"),
        ("hit3",     "10.0.2.4",   True,  "INTRA-IT",      "hit3 → hit4 (Sitio B)"),
        ("hit4",     "10.0.2.3",   True,  "INTRA-IT",      "hit4 → hit3 (Sitio B)"),

        # ──── INTRA-DB_SERVER (replicación, debe funcionar) ────
        ("srv_db",   "10.0.10.50", True,  "INTRA-DB",      "srv_db → backup"),
        ("backup",   "10.0.10.33", True,  "INTRA-DB",      "backup → srv_db"),

        # ──── VENTAS → WEB_SERVER (permitido) ────
        ("hv1",      "10.0.10.80", True,  "VENTAS→WEB",    "hv1 → srv_web (cross-site)"),
        ("hv2",      "10.0.10.80", True,  "VENTAS→WEB",    "hv2 → srv_web (cross-site)"),
        ("hv3",      "10.0.10.80", True,  "VENTAS→WEB",    "hv3 → srv_web (cross-site)"),
        ("hv4",      "10.0.10.80", True,  "VENTAS→WEB",    "hv4 → srv_web (cross-site)"),

        # ──── IT → WEB_SERVER (permitido) ────
        ("hit1",     "10.0.10.80", True,  "IT→WEB",        "hit1 → srv_web"),
        ("hit2",     "10.0.10.80", True,  "IT→WEB",        "hit2 → srv_web"),
        ("hit3",     "10.0.10.80", True,  "IT→WEB",        "hit3 → srv_web (cross-site)"),
        ("hit4",     "10.0.10.80", True,  "IT→WEB",        "hit4 → srv_web (cross-site)"),

        # ──── IT → DB_SERVER (permitido) ────
        ("hit1",     "10.0.10.33", True,  "IT→DB",         "hit1 → srv_db (cross-site)"),
        ("hit2",     "10.0.10.33", True,  "IT→DB",         "hit2 → srv_db (cross-site)"),
        ("hit1",     "10.0.10.50", True,  "IT→DB",         "hit1 → backup (cross-site)"),
        ("hit3",     "10.0.10.33", True,  "IT→DB",         "hit3 → srv_db (Sitio B)"),
        ("hit4",     "10.0.10.50", True,  "IT→DB",         "hit4 → backup (Sitio B)"),

        # ──── IT → VENTAS (permitido) ────
        ("hit1",     "10.0.1.1",   True,  "IT→VENTAS",     "hit1 → hv1 (Sitio A)"),
        ("hit1",     "10.0.1.2",   True,  "IT→VENTAS",     "hit1 → hv2 (Sitio A)"),
        ("hit2",     "10.0.1.1",   True,  "IT→VENTAS",     "hit2 → hv1 (Sitio A)"),
        ("hit3",     "10.0.1.3",   True,  "IT→VENTAS",     "hit3 → hv3 (Sitio B)"),
        ("hit3",     "10.0.1.4",   True,  "IT→VENTAS",     "hit3 → hv4 (Sitio B)"),
        ("hit1",     "10.0.1.3",   True,  "IT→VENTAS",     "hit1 → hv3 (cross-site)"),

        # ──── IT → HONEYPOT (permitido) ────
        ("hit1",     "10.0.66.77", True,  "IT→HONEYPOT",   "hit1 → honeypot (Sitio A)"),
        ("hit2",     "10.0.66.77", True,  "IT→HONEYPOT",   "hit2 → honeypot (Sitio A)"),
        ("hit3",     "10.0.66.78", True,  "IT→HONEYPOT",   "hit3 → honeypot2 (Sitio B)"),
        ("hit1",     "10.0.66.78", True,  "IT→HONEYPOT",   "hit1 → honeypot2 (cross-site)"),

        # ──── IT → IDS (permitido) ────
        ("hit1",     "10.0.66.90", True,  "IT→IDS",        "hit1 → ids (cross-site)"),
        ("hit2",     "10.0.66.90", True,  "IT→IDS",        "hit2 → ids (cross-site)"),
        ("hit3",     "10.0.66.90", True,  "IT→IDS",        "hit3 → ids (Sitio B)"),
        ("hit4",     "10.0.66.90", True,  "IT→IDS",        "hit4 → ids (Sitio B)"),

        # ──── VENTAS → IDS (permitido) ────
        ("hv1",      "10.0.66.90", True,  "VENTAS→IDS",    "hv1 → ids (cross-site)"),
        ("hv2",      "10.0.66.90", True,  "VENTAS→IDS",    "hv2 → ids (cross-site)"),
        ("hv3",      "10.0.66.90", True,  "VENTAS→IDS",    "hv3 → ids (Sitio B)"),

        # ──── WEB_SERVER → IDS (permitido) ────
        ("srv_web",  "10.0.66.90", True,  "WEB→IDS",       "srv_web → ids (cross-site)"),

        # ──── DB_SERVER → IDS (permitido) ────
        ("srv_db",   "10.0.66.90", True,  "DB→IDS",        "srv_db → ids (Sitio B)"),
        ("backup",   "10.0.66.90", True,  "DB→IDS",        "backup → ids (Sitio B)"),

        # ──── ATTACKER → HONEYPOT (permitido) ────
        ("attacker", "10.0.66.77", True,  "ATTACKER→HPOT", "attacker → honeypot (Sitio A)"),
        ("attacker", "10.0.66.78", True,  "ATTACKER→HPOT", "attacker → honeypot2 (cross-site)"),

        # ════════════════════════════════════════════════════════════════
        #  BLOQUEADOS
        # ════════════════════════════════════════════════════════════════

        # ──── VENTAS → IT (bloqueado) ────
        ("hv1",      "10.0.2.1",   False, "BLOQ VENTAS→IT",    "hv1 → hit1"),
        ("hv1",      "10.0.2.2",   False, "BLOQ VENTAS→IT",    "hv1 → hit2"),
        ("hv2",      "10.0.2.1",   False, "BLOQ VENTAS→IT",    "hv2 → hit1"),
        ("hv3",      "10.0.2.3",   False, "BLOQ VENTAS→IT",    "hv3 → hit3"),
        ("hv3",      "10.0.2.4",   False, "BLOQ VENTAS→IT",    "hv3 → hit4"),

        # ──── VENTAS → DB_SERVER (bloqueado) ────
        ("hv1",      "10.0.10.33", False, "BLOQ VENTAS→DB",    "hv1 → srv_db (cross-site)"),
        ("hv2",      "10.0.10.50", False, "BLOQ VENTAS→DB",    "hv2 → backup (cross-site)"),
        ("hv3",      "10.0.10.33", False, "BLOQ VENTAS→DB",    "hv3 → srv_db (Sitio B)"),

        # ──── VENTAS → HONEYPOT (bloqueado) ────
        ("hv1",      "10.0.66.77", False, "BLOQ VENTAS→HPOT",  "hv1 → honeypot"),
        ("hv3",      "10.0.66.78", False, "BLOQ VENTAS→HPOT",  "hv3 → honeypot2"),

        # ──── VENTAS → ATTACKER (bloqueado) ────
        ("hv1",      "10.0.66.66", False, "BLOQ VENTAS→ATK",   "hv1 → attacker"),
        ("hv3",      "10.0.66.66", False, "BLOQ VENTAS→ATK",   "hv3 → attacker (cross-site)"),

        # ──── ATTACKER → todo excepto HONEYPOT (bloqueado) ────
        ("attacker", "10.0.1.1",   False, "BLOQ ATTACKER",     "attacker → hv1"),
        ("attacker", "10.0.1.3",   False, "BLOQ ATTACKER",     "attacker → hv3 (cross-site)"),
        ("attacker", "10.0.2.1",   False, "BLOQ ATTACKER",     "attacker → hit1"),
        ("attacker", "10.0.2.3",   False, "BLOQ ATTACKER",     "attacker → hit3 (cross-site)"),
        ("attacker", "10.0.10.80", False, "BLOQ ATTACKER",     "attacker → srv_web"),
        ("attacker", "10.0.10.33", False, "BLOQ ATTACKER",     "attacker → srv_db (cross-site)"),
        ("attacker", "10.0.66.90", False, "BLOQ ATTACKER",     "attacker → ids (cross-site)"),

        # ──── HONEYPOT → todos (bloqueado, no inicia) ────
        ("honeypot", "10.0.1.1",   False, "BLOQ HONEYPOT",     "honeypot → hv1"),
        ("honeypot", "10.0.2.1",   False, "BLOQ HONEYPOT",     "honeypot → hit1"),
        ("honeypot", "10.0.10.80", False, "BLOQ HONEYPOT",     "honeypot → srv_web"),
        ("honeypot", "10.0.10.33", False, "BLOQ HONEYPOT",     "honeypot → srv_db (cross-site)"),
        ("honeypot", "10.0.66.66", False, "BLOQ HONEYPOT",     "honeypot → attacker"),
        ("honeypot", "10.0.66.90", False, "BLOQ HONEYPOT",     "honeypot → ids (cross-site)"),
        ("honeypot2","10.0.1.1",   False, "BLOQ HONEYPOT",     "honeypot2 → hv1 (cross-site)"),
        ("honeypot2","10.0.2.3",   False, "BLOQ HONEYPOT",     "honeypot2 → hit3"),
        ("honeypot2","10.0.66.66", False, "BLOQ HONEYPOT",     "honeypot2 → attacker (cross-site)"),

        # ──── WEB_SERVER → todos excepto IDS (bloqueado, no inicia) ────
        ("srv_web",  "10.0.1.1",   False, "BLOQ WEB→OTROS",    "srv_web → hv1"),
        ("srv_web",  "10.0.2.1",   False, "BLOQ WEB→OTROS",    "srv_web → hit1"),
        ("srv_web",  "10.0.10.33", False, "BLOQ WEB→OTROS",    "srv_web → srv_db (cross-site)"),
        ("srv_web",  "10.0.66.66", False, "BLOQ WEB→OTROS",    "srv_web → attacker"),
        ("srv_web",  "10.0.66.77", False, "BLOQ WEB→OTROS",    "srv_web → honeypot"),

        # ──── DB_SERVER → todos excepto DB_SERVER e IDS (bloqueado) ────
        ("srv_db",   "10.0.1.1",   False, "BLOQ DB→OTROS",     "srv_db → hv1 (cross-site)"),
        ("srv_db",   "10.0.2.1",   False, "BLOQ DB→OTROS",     "srv_db → hit1 (cross-site)"),
        ("srv_db",   "10.0.10.80", False, "BLOQ DB→OTROS",     "srv_db → srv_web (cross-site)"),
        ("srv_db",   "10.0.66.66", False, "BLOQ DB→OTROS",     "srv_db → attacker (cross-site)"),
        ("srv_db",   "10.0.66.77", False, "BLOQ DB→OTROS",     "srv_db → honeypot (cross-site)"),
        ("backup",   "10.0.1.1",   False, "BLOQ DB→OTROS",     "backup → hv1 (cross-site)"),
        ("backup",   "10.0.10.80", False, "BLOQ DB→OTROS",     "backup → srv_web (cross-site)"),

        # ──── IDS → todos (bloqueado, solo recibe) ────
        ("ids",      "10.0.1.1",   False, "BLOQ IDS→OTROS",    "ids → hv1 (cross-site)"),
        ("ids",      "10.0.2.1",   False, "BLOQ IDS→OTROS",    "ids → hit1 (cross-site)"),
        ("ids",      "10.0.10.80", False, "BLOQ IDS→OTROS",    "ids → srv_web (cross-site)"),
        ("ids",      "10.0.10.33", False, "BLOQ IDS→OTROS",    "ids → srv_db"),
        ("ids",      "10.0.66.66", False, "BLOQ IDS→OTROS",    "ids → attacker (cross-site)"),
        ("ids",      "10.0.66.77", False, "BLOQ IDS→OTROS",    "ids → honeypot (cross-site)"),
        ("ids",      "10.0.66.78", False, "BLOQ IDS→OTROS",    "ids → honeypot2"),
    ]

    # ================================================================
    #  EJECUCIÓN
    # ================================================================

    passed = 0
    failed = 0
    results = []
    category_stats = {}

    print("\n" + "=" * 80)
    print("  🛡️  BATERÍA DE PRUEBAS - MICROSEGMENTACIÓN SDN (STATEFUL)")
    print("=" * 80)

    current_category = None
    for src_name, dst_ip, should_pass, category, desc in TESTS:

        # Cabecera de categoría
        if category != current_category:
            current_category = category
            category_stats[category] = {"passed": int(0), "failed": int(0)}
            print(f"\n  {'─' * 70}")
            print(f"  📂 {category}")
            print(f"  {'─' * 70}")

        host = net.get(src_name)
        if host is None:
            print(f"  ⚠️  Host '{src_name}' no encontrado en la topología, saltando...")
            continue

        output = host.cmd(f'ping -c 1 -W 2 {dst_ip}')
        reachable = '1 received' in output or 'bytes from' in output

        if should_pass:
            ok = reachable
            expected = "PERMITIDO"
        else:
            ok = not reachable
            expected = "BLOQUEADO"

        status = "✅ PASS" if ok else "❌ FAIL"
        if ok:
            passed += 1
            category_stats[category]["passed"] += 1
        else:
            failed += 1
            category_stats[category]["failed"] += 1

        results.append((status, desc, expected, category))

        icon = "🟢" if expected == "PERMITIDO" else "🔴"
        ping_result = "OK ✓" if reachable else "Sin respuesta ✗"
        print(f"  {status}  {icon} {desc:<40} | Esperado: {expected:<10} | Ping: {ping_result}")

        time.sleep(0.3)

    # ================================================================
    #  RESUMEN POR CATEGORÍA
    # ================================================================

    print("\n" + "=" * 80)
    print("  📊 RESUMEN POR CATEGORÍA")
    print("=" * 80)

    for cat, stats in category_stats.items():
        total_cat = stats["passed"] + stats["failed"]
        pct_cat = (stats["passed"] / total_cat) * 100 if total_cat > 0 else 0
        icon = "✅" if stats["failed"] == 0 else "❌"
        print(f"  {icon} {cat:<25} {stats['passed']}/{total_cat} ({pct_cat:.0f}%)")

    # ================================================================
    #  RESUMEN FINAL
    # ================================================================

    total = passed + failed
    pct = (passed / total) * 100 if total > 0 else 0

    print("\n" + "=" * 80)
    if failed == 0:
        print(f"  🎉 RESULTADO FINAL: {passed}/{total} ({pct:.0f}%) - TODAS LAS PRUEBAS SUPERADAS")
    elif pct >= 80:
        print(f"  ⚠️  RESULTADO FINAL: {passed}/{total} ({pct:.0f}%) - {failed} pruebas fallidas")
    else:
        print(f"  🚨 RESULTADO FINAL: {passed}/{total} ({pct:.0f}%) - REVISAR CONFIGURACIÓN")

    # Listar los fallos
    if failed > 0:
        print(f"\n  {'─' * 70}")
        print(f"  ❌ PRUEBAS FALLIDAS:")
        print(f"  {'─' * 70}")
        for status, desc, expected, cat in results:
            if status == "❌ FAIL":
                print(f"     • [{cat}] {desc} (esperado: {expected})")

    print("=" * 80 + "\n")

    return results
