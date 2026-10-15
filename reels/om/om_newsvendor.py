"""OM Reel: Newsvendor mit Critical Ratio."""
import numpy as np
from scipy.stats import norm
from _common import *

PRICE, COST, SALV = 20, 12, 8
CU, CO = PRICE - COST, COST - SALV
CR = CU / (CU + CO)
MU, SIG = 500, 100
Z = norm.ppf(CR)
Q = MU + Z * SIG
assert (CU, CO) == (8, 4) and abs(CR - 2 / 3) < 1e-12 and abs(Z - 0.4307) < 1e-3 and round(Q) == 543

META = dict(
    slug="om-newsvendor", title="Newsvendor: Critical Ratio",
    subtitle="Q* = μ + z·σ mit z = NORM.S.INV(CR)",
    description="Newsvendor-Modell: Underage- und Overage-Kosten, Critical Ratio CR = cu/(cu+co), z-Wert, optimale Menge Q* = μ + z·σ mit Zahlenbeispiel und den Prüfungsfallen (σ statt σ², z·μ).",
    block="Block 2 — Inventory Management", topics=["Newsvendor", "Critical Ratio", "Underage", "Overage", "NORM.S.INV"],
    level=LEVEL, sort_order=90)

def draw(ax):
    x = np.linspace(200, 800, 400)
    pdf = norm.pdf(x, MU, SIG)
    ax.plot(x, pdf, color="#f1f1f4", lw=2.5)
    m = x <= Q
    ax.fill_between(x[m], pdf[m], color="#f97316", alpha=0.5)
    ax.axvline(Q, color="#f97316", lw=2.5)
    ax.axvline(MU, color="#9aa0ad", lw=1.5, ls="--")
    ax.text(380, 0.0009, "Fläche = CR\n= 66,7 %", color="#f1f1f4", ha="center", fontsize=12)
    ax.text(Q + 12, 0.0036, "Q* ≈ 543", color="#f97316", fontsize=13)
    ax.text(MU - 12, 0.0042, "μ = 500", color="#9aa0ad", fontsize=11, ha="right")
    ax.set_yticks([]); ax.set_xlabel("Nachfrage"); ax.set_ylim(0, 0.0046)

REEL = Reel(slug="om_newsvendor", kicker="OM · INVENTORY", beats=[
    Beat("Newsvendor: Du bestellst einmal, bevor du die Nachfrage kennst. Zu wenig kostet Gewinn, zu viel bleibt liegen. Wie viel ist optimal?",
         [kicker("Inventory Management"), title("Newsvendor")]),
    Beat("Zuerst die zwei Kosten. Underage: eine Einheit zu wenig, entgangener Gewinn. Overage: eine Einheit zu viel, Kosten minus Restwert.",
         [math(r"c_u=p-c", size=76, id="u"), math(r"c_o=c-s", size=76, id="o"),
          text("p Preis · c Einkauf · s Restwert", color=GRAY, size=44)], clear=True),
    Beat("Beispiel: Preis zwanzig, Einkauf zwölf, Restwert acht. Underage acht, Overage vier. Die Critical Ratio ist acht durch zwölf, also zwei Drittel.",
         [math(r"CR=\frac{c_u}{c_u+c_o}", size=84), math(r"=\frac{8}{8+4}=\frac{2}{3}\approx0{,}667", size=84, color=ORANGE)], clear=True),
    Beat("Das ist der optimale Servicegrad. Daraus der z-Wert: NORM.S.INV von null Komma sechs sechs sieben ergibt null Komma vier drei.",
         [math(r"CR\approx0{,}667", size=70, id="a"), math(r"z^*=\Phi^{-1}(CR)\approx0{,}43", size=70, color=ORANGE, id="b"),
          text("Excel: =NORM.S.INV(CR)", color=GRAY, size=48, id="c")], clear=True),
    Beat("Die optimale Menge: Mittelwert plus z mal Sigma. Bei Mittelwert fünfhundert und Sigma hundert sind das rund fünfhundertdreiundvierzig.",
         [math(r"Q^*=\mu+z^*\cdot\sigma", size=84), math(r"=500+0{,}43\cdot100\approx543", size=76, color=GREEN)], clear=True),
    Beat("Die Fläche links von Q Stern ist genau die Critical Ratio.",
         [plot(draw, height=640)], clear=True),
    Beat("Prüfungsfallen: Setze die Standardabweichung ein, nicht die Varianz. Und rechne nicht z mal Mittelwert, sondern Mittelwert plus z mal Sigma.",
         [callout("σ einsetzen, nicht σ²", color=RED, label="Falle 1", size=52),
          callout("= μ + z·σ  (nicht z·μ)", color=RED, label="Falle 2", size=52)], clear=True),
    Beat("Merke: Critical Ratio gleich c u durch c u plus c o. Menge gleich Mittelwert plus z Sigma.",
         [kicker("Merke"), math(r"CR=\frac{c_u}{c_u+c_o}", size=84, color=ORANGE), math(r"Q^*=\mu+z^*\sigma", size=84)], clear=True),
])
