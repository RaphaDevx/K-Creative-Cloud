"""OM Reel: Exponential Smoothing (einfach). Zahlen werden berechnet, nicht getippt."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "video-shorts-mcp"))
from beat_reel import *

ALPHA = 0.3
Y = [100, 110, 104, 120, 115]
F = [Y[0]]                                   # Initialisierung F1 = y1
for t in range(1, len(Y) + 1):
    F.append(ALPHA * Y[t - 1] + (1 - ALPHA) * F[t - 1])   # F_{t+1} = a*y_t + (1-a)*F_t
f = lambda v: f"{v:.1f}".replace(".", ",")
rows = [[t + 1, Y[t], f(F[t])] for t in range(len(Y))]     # Periode, Ist, Prognose (F_t)
# F[t] gehoert zu Periode t+1 -> hier Index-Versatz beachten
rows = [[p + 1, Y[p], f(F[p])] for p in range(len(Y))]
F_NEXT = F[len(Y)]
assert abs(F[2] - 103.0) < 1e-9 and abs(F_NEXT - 110.317) < 1e-9

META = dict(
    slug="om-exp-smoothing", title="Exponential Smoothing",
    subtitle="Neue Prognose = α · Ist + (1 − α) · alte Prognose",
    description="Einfaches Exponential Smoothing Schritt für Schritt: Formel, Startwert F1 = y1, Rechenbeispiel mit α = 0,3, Wirkung von α und die Prüfungsfalle beim Fehlermass.",
    block="Block 1 — Forecasting", topics=["Exponential Smoothing", "Alpha", "Prognose", "Zeitreihen", "Forecasting"],
    level="Prüfungsrelevant ⚡", sort_order=40)

REEL = Reel(slug="om_exp_smoothing", kicker="OM · FORECASTING", beats=[
    Beat("Exponentielle Glättung, englisch Exponential Smoothing: Die neue Prognose ist ein Mix aus dem, was gerade passiert ist, und der alten Prognose.",
         [kicker("Forecasting"), title("Exponential\nSmoothing")]),
    Beat("Die Formel: Prognose für morgen gleich Alpha mal Ist-Wert von heute, plus eins minus Alpha, mal Prognose von heute.",
         [math(r"F_{t+1}=\alpha\cdot y_t+(1-\alpha)\cdot F_t", id="f")], clear=True),
    Beat("Alpha liegt zwischen null und eins. Hohes Alpha reagiert schnell, aber nervös. Tiefes Alpha glättet stark, hinkt aber hinterher.",
         [math(r"0<\alpha<1", color=ORANGE),
          callout("Alpha hoch = reagiert schnell\nAlpha tief = glättet stark", color=BLUE)]),
    Beat("Startwert: Die erste Prognose ist einfach der erste Ist-Wert. Rechnen wir mit Alpha gleich null Komma drei.",
         [math(r"F_1=y_1", color=GREEN), math(r"\alpha=0{,}3", color=ORANGE)], clear=True),
    Beat("Die Nachfrage: hundert, hundertzehn, hundertvier, hundertzwanzig, hundertfünfzehn.",
         [table(["Periode", "Ist y", "Prognose F"], [[p + 1, Y[p], f(F[0]) if p == 0 else "?"] for p in range(5)], hl={(0, 2): GREEN}, id="t")], clear=True),
    Beat("Periode zwei: null Komma drei mal hundert, plus null Komma sieben mal hundert, ergibt hundert.",
         [table(["Periode", "Ist y", "Prognose F"], [r if i < 2 else [r[0], r[1], "?"] for i, r in enumerate(rows)], hl={(1, 2): GREEN}, id="t"),
          math(r"0{,}3\cdot100+0{,}7\cdot100=100", id="calc")]),
    Beat("Periode drei: null Komma drei mal hundertzehn, plus null Komma sieben mal hundert, ergibt hundertdrei.",
         [table(["Periode", "Ist y", "Prognose F"], [r if i < 3 else [r[0], r[1], "?"] for i, r in enumerate(rows)], hl={(2, 2): GREEN}, id="t"),
          math(r"0{,}3\cdot110+0{,}7\cdot100=103", id="calc")]),
    Beat("Und so weiter. Für Periode sechs ergibt sich eine Prognose von etwa hundertzehn Komma drei.",
         [table(["Periode", "Ist y", "Prognose F"], rows + [[6, "?", f(F_NEXT)]], hl={(5, 2): GREEN}, id="t"),
          math(r"0{,}3\cdot115+0{,}7\cdot108{,}3=110{,}3", id="calc")]),
    Beat("Achtung in der Prüfung: Der Fehler wird ab Periode zwei gerechnet, nicht ab Periode eins, weil der Startwert gesetzt ist.",
         [callout("Fehlermasse (MAD, MSE, MAPE) bei ES ab Periode 2 – Startwert F1 = y1 hat keinen Fehler.", color=RED,
                  label="Prüfungsfalle")]),
    Beat("Merke: Neue Prognose gleich Alpha mal Ist, plus eins minus Alpha mal alte Prognose. In Excel: Alpha mal Ist-Zelle plus eins minus Alpha mal Prognose-Zelle.",
         [], clear=True),
])
REEL.beats[-1].show = [kicker("Merke"), math(r"F_{t+1}=\alpha\,y_t+(1-\alpha)\,F_t"),
                       text("Startwert F₁ = y₁", color=GRAY)]
