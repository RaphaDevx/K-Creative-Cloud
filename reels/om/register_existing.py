#!/usr/bin/env python3
"""Registriert die bereits im Bucket `videos` liegenden, englisch gesprochenen OM-Reels im Katalog (einmalig).
Die Variante om_sc_without_postponement_latex bewusst NICHT: dort ist die Formel abgeschnitten (Wurzel fehlt)."""
import os, sys, json
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "video-shorts-mcp"))
from publish_k_learning import publish

EXISTING = [
    ("om_mrp1_material_requirements.mp4", dict(
        slug="om-mrp1-material-requirements", title="MRP I: Gross → Net → Offset → Release",
        subtitle="Materialbedarfsplanung in 4 Schritten (englisch gesprochen)",
        description="MRP I: Nettobedarf = Bruttobedarf − Lagerbestand − Scheduled Receipts, Lead-Time-Offset rückwärts, Multi-Level-BOM top-down. Englisch gesprochen.",
        block="Block 3 — Production Management",
        topics=["MRP", "Nettobedarf", "Lead Time Offset", "BOM", "Planned Order Release"], sort_order=10)),
    ("om_sc_without_postponement.mp4", dict(
        slug="om-sc-without-postponement", title="Postponement: Risk Pooling",
        subtitle="4 Märkte, 0 Pooling — Newsvendor mit Lead Time (englisch gesprochen)",
        description="Ohne Postponement puffert jedes Land allein: Q* = (LT+1)·μ + z·σ·√(LT+1), Variationskoeffizient, Pooling-Effekt. Englisch gesprochen.",
        block="Block 2 — Inventory Management",
        topics=["Postponement", "Risk Pooling", "Newsvendor", "Lead Time", "Variationskoeffizient"], sort_order=20)),
    ("om_bullwhip_effect.mp4", dict(
        slug="om-bullwhip-effect", title="Der Bullwhip-Effekt",
        subtitle="Stabile Nachfrage, totales Chaos in der Supply Chain (englisch gesprochen)",
        description="Warum kleine Nachfrageschwankungen entlang der Supply Chain verstärkt werden: Treiber, Konsequenzen, Gegenmassnahmen. Englisch gesprochen.",
        block="Block 4 — Supply Chain Management",
        topics=["Bullwhip-Effekt", "Supply Chain", "Informationsaustausch", "Order Batching", "CPFR"], sort_order=30)),
]
if __name__ == "__main__":
    src = os.environ["EXISTING_DIR"]          # Ordner mit den MP4 (Kopie von FS_26/OM/Reels)
    for fn, meta in EXISTING:
        print(json.dumps(publish(os.path.join(src, fn), meta, register_only=True), ensure_ascii=False))
