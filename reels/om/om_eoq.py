"""OM Reel: EOQ (Andler) mit Kostenkurven."""
from math import sqrt
import numpy as np
from _common import *

D, S, H = 3600, 50, 4
Q = sqrt(2 * D * S / H)
N = D / Q
ORD, HOLD = N * S, Q / 2 * H
assert Q == 300 and N == 12 and ORD == 600 and HOLD == 600

META = dict(
    slug="om-eoq", title="EOQ: Optimale Bestellmenge",
    subtitle="Q* = √(2·D·S / H) — Bestell- und Lagerkosten im Gleichgewicht",
    description="Economic Order Quantity: Formel, Variablen D, S, H, Rechenbeispiel (Q* = 300), Kostenkurven mit Minimum bei gleichen Bestell- und Lagerkosten und die Prüfungsfalle Zeiteinheit.",
    block="Block 2 — Inventory Management", topics=["EOQ", "Bestellmenge", "Lagerkosten", "Bestellkosten", "Andler"],
    level=LEVEL, sort_order=70)

def draw(ax):
    q = np.linspace(60, 700, 300)
    ax.plot(q, D / q * S, color="#38bdf8", lw=2.5, label="Bestellkosten D/Q·S")
    ax.plot(q, q / 2 * H, color="#22c55e", lw=2.5, label="Lagerkosten Q/2·H")
    ax.plot(q, D / q * S + q / 2 * H, color="#f97316", lw=3.5, label="Gesamtkosten")
    ax.plot([Q], [ORD + HOLD], "o", color="#f1f1f4", ms=11)
    ax.axvline(Q, color="#9aa0ad", ls="--", lw=1.5)
    ax.annotate("Q* = 300", (Q, ORD + HOLD), textcoords="offset points", xytext=(14, 24), color="#f1f1f4", fontsize=13)
    ax.set_ylim(0, 2600); ax.set_xlabel("Bestellmenge Q"); ax.set_ylabel("Kosten CHF / Jahr")
    ax.legend(facecolor="#1c202c", edgecolor="#4a5066", labelcolor="#f1f1f4", fontsize=10, loc="upper right")

REEL = Reel(slug="om_eoq", kicker="OM · INVENTORY", beats=[
    Beat("Wie viel soll ich auf einmal bestellen? Zu oft bestellen kostet Bestellkosten, zu viel bestellen kostet Lagerkosten. Die optimale Menge liefert die E O Q Formel.",
         [kicker("Inventory Management"), title("EOQ")]),
    Beat("Q Stern gleich Wurzel aus zwei mal D mal S, geteilt durch H.",
         [math(r"Q^*=\sqrt{\frac{2\cdot D\cdot S}{H}}", size=100)], clear=True),
    Beat("D ist die Jahresnachfrage, S die Bestellkosten pro Bestellung und H die Lagerkosten pro Stück und Jahr.",
         [table(["", "Bedeutung", "Beispiel"], [["D", "Nachfrage / Jahr", "3600"], ["S", "Kosten / Bestellung", "50 CHF"],
                                                 ["H", "Lager / Stück / Jahr", "4 CHF"]], size=46, id="t")]),
    Beat("Einsetzen: zwei mal dreitausendsechshundert mal fünfzig, geteilt durch vier, ergibt neunzigtausend. Die Wurzel daraus ist dreihundert.",
         [math(r"Q^*=\sqrt{\frac{2\cdot3600\cdot50}{4}}", size=84, id="f"), math(r"=\sqrt{90\,000}=300", size=90, color=ORANGE, id="f2"),
          text("12 Bestellungen pro Jahr, Ø Lager Q*/2 = 150", color=WHITE, size=46, id="n")], clear=True),
    Beat("Im Optimum sind Bestellkosten und Lagerkosten gleich gross: je sechshundert Franken, zusammen zwölfhundert.",
         [plot(draw, height=700)], clear=True),
    Beat("Prüfungsfalle: D, S und H müssen in derselben Zeiteinheit stehen. Alle pro Jahr oder alle pro Woche, sonst stimmt das Ergebnis nicht.",
         [callout("D, S, H in derselben Zeiteinheit\n(alle /Jahr oder alle /Woche)", color=RED, label="Prüfungsfalle", size=54)], clear=True),
    Beat("Merke: E O Q gleich Wurzel aus zwei D S durch H. In Excel: Wurzel von zwei mal D mal S durch H.",
         [kicker("Merke"), math(r"Q^*=\sqrt{\frac{2DS}{H}}", size=100, color=ORANGE),
          text("Excel: =SQRT(2*D*S/H)", color=GRAY, size=48)], clear=True),
])
