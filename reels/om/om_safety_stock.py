"""OM Reel: Safety Stock und Reorder Point."""
from math import sqrt
import numpy as np
from scipy.stats import norm
from _common import *

d_, SIG, L, SL = 100, 20, 4, 0.95
Z = norm.ppf(SL)
SS = Z * SIG * sqrt(L)
ROP = d_ * L + SS
assert abs(Z - 1.6449) < 1e-3 and abs(SS - 65.79) < 0.01 and abs(ROP - 465.79) < 0.01

META = dict(
    slug="om-safety-stock-rop", title="Safety Stock & Reorder Point",
    subtitle="SS = z · σ · √L — wann bestellen, damit es reicht?",
    description="Sicherheitsbestand und Bestellpunkt: SS = z·σ·√L, ROP = d·L + SS, z aus dem Servicegrad (NORM.S.INV), Rechenbeispiel mit 95 % Servicegrad und die Falle √L statt L.",
    block="Block 2 — Inventory Management", topics=["Safety Stock", "Reorder Point", "Servicegrad", "z-Wert", "Lead Time"],
    level=LEVEL, sort_order=80)

def draw(ax):
    x = np.linspace(-3.6, 3.6, 400)
    ax.plot(x, norm.pdf(x), color="#f1f1f4", lw=2.5)
    m = x <= Z
    ax.fill_between(x[m], norm.pdf(x[m]), color="#22c55e", alpha=0.45)
    ax.fill_between(x[~m], norm.pdf(x[~m]), color="#ef4444", alpha=0.45)
    ax.axvline(Z, color="#f97316", lw=2.5)
    ax.text(-1.0, 0.1, "95 % der Fälle\nabgedeckt", color="#f1f1f4", ha="center", fontsize=12)
    ax.text(Z + 0.12, 0.30, "z = 1,645", color="#f97316", fontsize=13)
    ax.text(2.55, 0.06, "5 %\nStockout", color="#f1f1f4", ha="center", fontsize=11)
    ax.set_yticks([]); ax.set_xlabel("Standardabweichungen"); ax.set_ylim(0, 0.45)

REEL = Reel(slug="om_safety_stock", kicker="OM · INVENTORY", beats=[
    Beat("Während der Lieferzeit kann die Nachfrage höher ausfallen als erwartet. Dagegen hilft der Sicherheitsbestand, und er bestimmt den Bestellpunkt.",
         [kicker("Inventory Management"), title("Safety Stock\n& ROP", size=96)]),
    Beat("Sicherheitsbestand gleich z mal Sigma mal Wurzel aus L. Der Bestellpunkt ist die erwartete Nachfrage während der Lieferzeit plus Sicherheitsbestand.",
         [math(r"SS=z\cdot\sigma_d\cdot\sqrt{L}", size=84, color=ORANGE, id="a"),
          math(r"ROP=\bar{d}\cdot L+SS", size=84, id="b")], clear=True),
    Beat("Das z kommt aus dem Servicegrad. Bei fünfundneunzig Prozent liefert Excel mit NORM.S.INV den Wert eins Komma sechs vier fünf.",
         [plot(draw, height=640), text("z = NORM.S.INV(0,95) = 1,645", color=WHITE, size=50, bold=True)], clear=True),
    Beat("Beispiel: Nachfrage hundert pro Woche, Sigma zwanzig pro Woche, Lieferzeit vier Wochen.",
         [table(["", "Wert"], [["d (Ø)", "100 / Woche"], ["σ", "20 / Woche"], ["L", "4 Wochen"], ["Servicegrad", "95 %"]], size=54, id="t")], clear=True),
    Beat("Sicherheitsbestand: eins Komma sechs vier fünf mal zwanzig mal Wurzel aus vier, ergibt rund sechsundsechzig Stück.",
         [table(["", "Wert"], [["d (Ø)", "100 / Woche"], ["σ", "20 / Woche"], ["L", "4 Wochen"], ["Servicegrad", "95 %"]], size=40, id="t"),
          math(r"SS=1{,}645\cdot20\cdot\sqrt{4}\approx66", size=70, color=GREEN, id="c")]),
    Beat("Bestellpunkt: hundert mal vier gleich vierhundert, plus sechsundsechzig, ergibt rund vierhundertsechsundsechzig. Sinkt der Bestand auf diesen Wert, wird nachbestellt.",
         [table(["", "Wert"], [["d (Ø)", "100 / Woche"], ["σ", "20 / Woche"], ["L", "4 Wochen"], ["Servicegrad", "95 %"]], size=40, id="t"),
          math(r"ROP=100\cdot4+66\approx466", size=70, color=GREEN, id="c")]),
    Beat("Prüfungsfalle: Es ist die Wurzel aus L, nicht L selbst. Und Sigma und L müssen in derselben Zeiteinheit stehen.",
         [callout("√L, nicht L!\nσ und L in derselben Zeiteinheit", color=RED, label="Prüfungsfalle", size=54)], clear=True),
    Beat("Merke: Sicherheitsbestand gleich z Sigma Wurzel L, Bestellpunkt gleich Nachfrage in der Lieferzeit plus Sicherheitsbestand.",
         [kicker("Merke"), math(r"ROP=\bar{d}L+z\,\sigma_d\sqrt{L}", size=76, color=ORANGE)], clear=True),
])
