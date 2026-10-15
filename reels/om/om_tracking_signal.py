"""OM Reel: Tracking Signal = RSFE / MAD (Bias-Erkennung)."""
from _common import *

E_ = [10, 15, 12, 20]                        # Fehler e = Ist - Prognose, immer positiv => Prognose zu tief
n = len(E_)
RSFE = [sum(E_[:i + 1]) for i in range(n)]
MADc = [sum(abs(e) for e in E_[:i + 1]) / (i + 1) for i in range(n)]
TS = [RSFE[i] / MADc[i] for i in range(n)]
assert RSFE == [10, 25, 37, 57] and all(abs(TS[i] - (i + 1)) < 1e-9 for i in range(n)) and abs(MADc[3] - 14.25) < 1e-9
LIMIT = 4

META = dict(
    slug="om-tracking-signal", title="Tracking Signal",
    subtitle="Ist die Prognose verzerrt? TS = RSFE / MAD",
    description="Tracking Signal erkennt systematische Über- oder Unterschätzung: laufende Summe der Fehler (RSFE) geteilt durch MAD, Rechenbeispiel, Kontrollgrenzen (häufig ±4 MAD) und Abgrenzung zum MAD.",
    block="Block 1 — Forecasting", topics=["Tracking Signal", "RSFE", "MAD", "Bias", "Forecasting"],
    level=LEVEL, sort_order=60)

def draw(ax):
    xs = list(range(1, n + 1))
    ax.axhspan(-LIMIT, LIMIT, color="#22c55e", alpha=0.10)
    ax.axhline(LIMIT, color="#ef4444", lw=2); ax.axhline(-LIMIT, color="#ef4444", lw=2)
    ax.plot(xs, TS, color="#f97316", lw=3, marker="o", ms=9)
    for x, v in zip(xs, TS):
        ax.annotate(de(v), (x, v), textcoords="offset points", xytext=(0, 12), ha="center", color="#f1f1f4", fontsize=11)
    ax.set_ylim(-6, 6.5); ax.set_xticks(xs); ax.set_xlabel("Periode t"); ax.set_ylabel("Tracking Signal")
    ax.text(0.55, LIMIT + 0.3, "+4", color="#ef4444", fontsize=11); ax.text(0.55, -LIMIT - 0.9, "−4", color="#ef4444", fontsize=11)

tab = lambda k: table(["t", "e", "RSFE", "MAD", "TS"],
                      [[i + 1, E_[i], RSFE[i], de(MADc[i], 2), de(TS[i])] for i in range(k)],
                      hl={(i, 4): ORANGE for i in range(k)}, size=50, id="t")

REEL = Reel(slug="om_tracking_signal", kicker="OM · FORECASTING", beats=[
    Beat("Eine Prognose kann im Schnitt gut sein und trotzdem immer in dieselbe Richtung danebenliegen. Das erkennt der Tracking Signal.",
         [kicker("Forecasting"), title("Tracking\nSignal")]),
    Beat("Die Formel: laufende Summe der Fehler, geteilt durch den M A D. Die laufende Summe heisst R S F E, Running Sum of Forecast Errors.",
         [math(r"\mathrm{TS}_t=\frac{\mathrm{RSFE}_t}{\mathrm{MAD}_t}=\frac{\sum e_i}{\mathrm{MAD}_t}", size=70)], clear=True),
    Beat("Beispiel: Die Fehler sind in vier Perioden immer positiv: zehn, fünfzehn, zwölf, zwanzig. Die Prognose liegt also ständig zu tief.",
         [table(["t", "e"], [[i + 1, f"+{E_[i]}"] for i in range(n)], size=54, id="t")], clear=True),
    Beat("Periode eins: R S F E zehn, M A D zehn, Tracking Signal eins. Periode zwei: fünfundzwanzig durch zwölf Komma fünf, ergibt zwei.",
         [tab(2)], clear=True),
    Beat("Periode vier: R S F E siebenundfünfzig, M A D vierzehn Komma zwei fünf, Tracking Signal vier.",
         [tab(4)], clear=True),
    Beat("Üblich sind Kontrollgrenzen von plus minus vier M A D, je nach Aufgabenstellung auch drei. Wird die Grenze erreicht, ist die Prognose systematisch verzerrt und das Modell gehört überprüft.",
         [plot(draw, height=640)], clear=True),
    Beat("Merke: Der M A D misst die Grösse der Fehler, der Tracking Signal die Richtung. Liegt er ausserhalb der Grenzen, steckt ein Bias drin.",
         [kicker("Merke"), math(r"\mathrm{TS}=\frac{\mathrm{RSFE}}{\mathrm{MAD}}", size=90, color=ORANGE),
          text("ausserhalb ±4: Bias", color=WHITE, size=60, bold=True)], clear=True),
])
