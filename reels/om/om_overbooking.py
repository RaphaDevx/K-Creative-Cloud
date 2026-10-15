"""OM Reel: Revenue Management - Overbooking (Newsvendor-Logik, Normalverteilung der No-Shows)."""
import numpy as np
from scipy.stats import norm
from _common import *

C = 100
C_EMPTY, C_DENIED = 200, 300
CR = C_EMPTY / (C_EMPTY + C_DENIED)
MU_NS, SIG_NS = 10, 3
Z = norm.ppf(CR)
X = MU_NS + Z * SIG_NS
assert CR == 0.4 and abs(Z + 0.2533) < 1e-3 and abs(X - 9.24) < 0.01

META = dict(
    slug="om-overbooking", title="Revenue Management: Overbooking",
    subtitle="Wie viele Buchungen über Kapazität? c_leer / (c_leer + c_verweigert)",
    description="Overbooking im Revenue Management: Kosten eines leeren Platzes vs. Verweigerung, optimale Überbuchung über die Wahrscheinlichkeit P = c_leer/(c_leer + c_verweigert), Rechenbeispiel mit normalverteilten No-Shows (Annahme).",
    block="Block 5 — Revenue Management", topics=["Revenue Management", "Overbooking", "No-Shows", "Kapazität", "Critical Ratio"],
    level=LEVEL, sort_order=100)

def draw(ax):
    x = np.linspace(0, 20, 400)
    pdf = norm.pdf(x, MU_NS, SIG_NS)
    ax.plot(x, pdf, color="#f1f1f4", lw=2.5)
    m = x <= X
    ax.fill_between(x[m], pdf[m], color="#f97316", alpha=0.5)
    ax.axvline(X, color="#f97316", lw=2.5)
    ax.text(6.6, 0.012, "Fläche = 0,4", color="#f1f1f4", ha="center", fontsize=13)
    ax.text(X + 0.4, 0.125, "x* ≈ 9,2", color="#f97316", fontsize=13)
    ax.set_yticks([]); ax.set_xlabel("No-Shows (Ø 10, σ 3)"); ax.set_ylim(0, 0.15)

REEL = Reel(slug="om_overbooking", kicker="OM · REVENUE MANAGEMENT", beats=[
    Beat("Ein leerer Flugplatz ist verlorener Umsatz, denn er lässt sich nicht lagern. Deshalb verkaufen Airlines und Hotels mehr Plätze, als es gibt: Overbooking.",
         [kicker("Revenue Management"), title("Overbooking")]),
    Beat("Zwei Kosten stehen sich gegenüber. Ein leerer Platz, weil jemand nicht erscheint. Oder verweigerter Service, weil mehr Gäste kommen als Plätze da sind.",
         [callout("No-Show = leerer Platz\nKosten c leer", color=BLUE, size=54),
          callout("Zu viele Gäste = Verweigerung\nKosten c verweigert", color=RED, size=54)], clear=True),
    Beat("Das Optimum: Die Wahrscheinlichkeit, dass mehr Gäste kommen als Plätze da sind, entspricht c leer geteilt durch c leer plus c verweigert.",
         [math(r"P(\mathrm{Gäste}>C)", size=84, id="a"), math(r"=\frac{c_{leer}}{c_{leer}+c_{verweigert}}", size=84, color=ORANGE, id="b")], clear=True),
    Beat("Beispiel: hundert Plätze. Ein leerer Platz kostet zweihundert, eine Verweigerung dreihundert. Das ergibt null Komma vier.",
         [math(r"\frac{200}{200+300}=0{,}4", size=90, color=ORANGE),
          text("C = 100 Plätze", color=GRAY, size=48)], clear=True),
    Beat("Die No-Shows nehmen wir als normalverteilt an: Mittelwert zehn, Sigma drei. Gesucht ist die Überbuchung, bei der die Fläche links null Komma vier beträgt.",
         [plot(draw, height=640)], clear=True),
    Beat("Der z-Wert zu null Komma vier ist minus null Komma zwei fünf. Überbuchung gleich zehn minus null Komma zwei fünf mal drei, rund neun Plätze. Also bis zu hundertneun Buchungen annehmen.",
         [math(r"x^*=\mu+z\sigma=10-0{,}25\cdot3\approx9", size=70, id="a"),
          math(r"\approx 109\ \mathrm{Buchungen}", size=70, color=GREEN, id="b")], clear=True),
    Beat("Merke: Je teurer ein leerer Platz im Verhältnis zur Verweigerung, desto stärker wird überbucht.",
         [kicker("Merke"), math(r"CR=\frac{c_{leer}}{c_{leer}+c_{verweigert}}", size=80, color=ORANGE),
          text("hohes CR: mehr Overbooking", color=WHITE, size=56, bold=True)], clear=True),
])
