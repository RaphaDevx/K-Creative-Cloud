"""OM Reel: Forecast-Fehlermasse MAD, MSE, MAPE (+ ME). Alle Zahlen berechnet."""
from _common import *

Y = [120, 130, 110, 140]
F = [110, 135, 120, 130]
E_ = [y - f for y, f in zip(Y, F)]
n = len(Y)
MAD = sum(abs(e) for e in E_) / n
MSE = sum(e * e for e in E_) / n
MAPE = sum(abs(e) / y for e, y in zip(E_, Y)) / n * 100
ME = sum(E_) / n
assert (MAD, MSE) == (8.75, 81.25) and abs(MAPE - 7.1033) < 1e-3 and ME == 1.25

HEAD = ["t", "Ist y", "Prog. F", "e = y−F"]
def rows(cols=4, absx=False, sq=False):
    out = []
    for i in range(n):
        r = [i + 1, Y[i], F[i], f"{E_[i]:+d}".replace("-", "−")]
        if absx: r.append(abs(E_[i]))
        if sq: r.append(E_[i] ** 2)
        out.append(r)
    return out

META = dict(
    slug="om-fehlermasse-mad-mse-mape", title="Fehlermasse: MAD, MSE, MAPE",
    subtitle="Wie gut ist die Prognose? Drei Masse, ein Rechenbeispiel",
    description="Prognosefehler messen: Fehler e = Ist − Prognose, MAD (Mittel der Beträge), MSE (Mittel der Quadrate), MAPE (relativ in %) mit Zahlenbeispiel und den Prüfungsfallen (MAPE-Formel, Ist = 0, ME als Bias).",
    block="Block 1 — Forecasting", topics=["MAD", "MSE", "MAPE", "Prognosefehler", "Forecasting", "Bias"],
    level=LEVEL, sort_order=50)

REEL = Reel(slug="om_fehlermasse", kicker="OM · FORECASTING", beats=[
    Beat("Wie gut ist eine Prognose? Dafür gibt es drei Fehlermasse: M A D, M S E und M A P E.",
         [kicker("Forecasting"), title("MAD · MSE\nMAPE")]),
    Beat("Ausgangspunkt ist immer der Fehler: Ist-Wert minus Prognose. Hier vier Perioden.",
         [math(r"e_t=y_t-F_t", size=80, id="f"),
          table(HEAD, rows(), id="t")], clear=True),
    Beat("M A D: das Mittel der Beträge. Beträge zehn, fünf, zehn und zehn, Summe fünfunddreissig, durch vier, ergibt acht Komma sieben fünf.",
         [math(r"\mathrm{MAD}=\frac{1}{T}\sum|e_t|", size=76, id="f"), math(r"=\frac{35}{4}=8{,}75", size=84, color=ORANGE, id="r"),
          table(HEAD + ["|e|"], rows(absx=True), hl={(i, 4): ORANGE for i in range(n)}, size=48, id="t")], clear=True),
    Beat("M S E: das Mittel der Fehlerquadrate. Hundert, fünfundzwanzig, hundert, hundert, Summe dreihundertfünfundzwanzig, durch vier, ergibt einundachtzig Komma zwei fünf. Grosse Fehler zählen deutlich stärker.",
         [math(r"\mathrm{MSE}=\frac{1}{T}\sum e_t^2", size=76, id="f"), math(r"=\frac{325}{4}=81{,}25", size=84, color=BLUE, id="r"),
          table(HEAD + ["e²"], rows(sq=True), hl={(i, 4): BLUE for i in range(n)}, size=48, id="t")], clear=True),
    Beat("M A P E: der Betrag des Fehlers geteilt durch den Ist-Wert, gemittelt. Das gibt sieben Komma eins Prozent und ist unabhängig von der Einheit.",
         [math(r"\mathrm{MAPE}=\frac{1}{T}\sum\frac{|e_t|}{y_t}", size=76, id="f"), math(r"\approx 7{,}1\,\%", size=84, color=GREEN, id="r"),
          table(["t", "|e|", "y", "|e|/y"], [[i + 1, abs(E_[i]), Y[i], de(abs(E_[i]) / Y[i] * 100) + " %"] for i in range(n)],
                hl={(i, 3): GREEN for i in range(n)}, size=52, id="t")], clear=True),
    Beat("Prüfungsfallen: Beim M A P E wird nicht quadriert. M A D und M A P E funktionieren nicht, wenn der Ist-Wert null sein kann. Und der Mittelwert der Fehler, M E, zeigt nur den Bias, weil sich Plus und Minus aufheben.",
         [callout("MAPE = |e| / y  (nicht e² / y)", color=RED, label="Falle 1", size=46),
          callout("y = 0 möglich: MAD/MAPE ungeeignet", color=RED, label="Falle 2", size=46),
          callout("ME = Bias (Plus/Minus heben sich auf): hier ME = +1,25", color=YELLOW, label="Falle 3", size=46)], clear=True),
    Beat("Merke: M A D in Einheiten, M S E bestraft Ausreisser, M A P E in Prozent. Bei Moving Average und Exponential Smoothing nur Perioden mit Prognose mitrechnen.",
         [kicker("Merke"), text("MAD – Einheiten", color=ORANGE, size=64, bold=True),
          text("MSE – bestraft grosse Fehler", color=BLUE, size=64, bold=True),
          text("MAPE – in Prozent", color=GREEN, size=64, bold=True)], clear=True),
])
