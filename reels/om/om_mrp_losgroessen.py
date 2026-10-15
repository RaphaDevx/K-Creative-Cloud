"""OM Reel: MRP - Brutto/Netto, Lead-Time-Offset, Losgroessen (Lot-for-Lot vs. fixe Losgroesse). Plan wird berechnet."""
from _common import *

GROSS = [20, 30, 0, 40, 10, 50]
ONHAND0, LT, LOT = 40, 1, 60
WEEKS = len(GROSS)

def mrp(lot):
    """lot=None -> Lot-for-Lot. Rueckgabe: end-Bestand, Netto, Receipts je Woche."""
    oh, net, rec, end = ONHAND0, [], [], []
    for g in GROSS:
        n_ = max(0, g - oh)
        r = 0
        if n_ > 0:
            r = n_ if lot is None else -(-n_ // lot) * lot      # aufrunden auf Vielfaches von lot
        oh = oh + r - g
        net.append(n_); rec.append(r); end.append(oh)
    return end, net, rec

def release(rec):
    rel = [0] * WEEKS
    for i, r in enumerate(rec):
        if r:
            rel[i - LT] = r      # Bestelldatum = Bedarfsdatum - Lead Time (rueckwaerts!)
    return rel

e1, n1, r1 = mrp(None); rel1 = release(r1)
e2, n2, r2 = mrp(LOT);  rel2 = release(r2)
assert n1 == [0, 10, 0, 40, 10, 50] and e1 == [20, 0, 0, 0, 0, 0]
assert r1 == [0, 10, 0, 40, 10, 50] and rel1 == [10, 0, 40, 10, 50, 0]
assert r2 == [0, 60, 0, 0, 0, 60] and rel2 == [60, 0, 0, 0, 60, 0] and e2 == [20, 50, 50, 10, 0, 10]

META = dict(
    slug="om-mrp-brutto-netto-losgroessen", title="MRP: Nettobedarf & Losgrössen",
    subtitle="Brutto → Netto → Lead-Time-Offset → Release, Lot-for-Lot vs. fixe Losgrösse",
    description="MRP-Rechnung Schritt für Schritt: Nettobedarf = Brutto − Lagerbestand − Scheduled Receipts, Bestellung um die Lead Time rückwärts verschieben, Lot-for-Lot gegenüber fixer Losgrösse 60 (2 statt 4 Bestellungen, Restbestand 10).",
    block="Block 3 — Production Management", topics=["MRP", "Bruttobedarf", "Nettobedarf", "Losgrösse", "Lead Time", "Lot-for-Lot"],
    level=LEVEL, sort_order=110)

HEAD = ["", "W1", "W2", "W3", "W4", "W5", "W6"]
z = lambda v: "–" if v == 0 else str(v)
def tab(rows, hl=None, id="t", size=56):
    return table(HEAD, rows, hl=hl, size=size, id=id)
R_GROSS = ["Brutto"] + [z(g) if g else "0" for g in GROSS]
R_END = lambda e: ["Bestand"] + [str(x) for x in e]
R_NET = lambda n_: ["Netto"] + [z(x) for x in n_]
R_REC = lambda r: ["Eingang"] + [z(x) for x in r]
R_REL = lambda r: ["Release"] + [z(x) for x in r]

REEL = Reel(slug="om_mrp_losgroessen", kicker="OM · PRODUCTION", beats=[
    Beat("M R P beantwortet drei Fragen: Was brauche ich, wie viel und wann muss ich bestellen? Wir rechnen ein Beispiel.",
         [kicker("Production Management"), title("MRP I")]),
    Beat("Nettobedarf gleich Bruttobedarf minus Lagerbestand minus bereits geplante Eingänge. Das Bestelldatum ist das Bedarfsdatum minus Lead Time.",
         [math(r"\mathrm{Netto}=\mathrm{Brutto}-\mathrm{Lager}-\mathrm{Receipts}", size=62, id="a"),
          text("Receipts = Scheduled Receipts (schon geplante Eingänge)", color=GRAY, size=38, id="a2"),
          spacer(30),
          math(r"\mathrm{Bestelldatum}=\mathrm{Bedarf}-LT", size=76, color=ORANGE, id="b")], clear=True),
    Beat("Beispiel: Anfangsbestand vierzig, Lead Time eine Woche. Der Bruttobedarf pro Woche: zwanzig, dreissig, null, vierzig, zehn, fünfzig.",
         [tab([R_GROSS], id="t"), text("Anfangsbestand 40 · LT = 1 Woche", color=GRAY, size=44)], clear=True),
    Beat("Woche eins: Der Bestand reicht, Nettobedarf null, es bleiben zwanzig. Woche zwei: dreissig gebraucht, nur zwanzig da. Nettobedarf zehn.",
         [tab([R_GROSS, R_END([e1[0]] + [""] * 5)[:7], R_NET([0, 10, 0, 0, 0, 0])], hl={(2, 2): ORANGE}),
          text("Anfangsbestand 40 · LT = 1 Woche", color=GRAY, size=44)], clear=True),
    Beat("So geht es weiter. Nettobedarf: null, zehn, null, vierzig, zehn, fünfzig. Bestellen wir genau diese Menge, ist das Lot for Lot.",
         [tab([R_GROSS, R_NET(n1), R_REC(r1)], hl={(1, i + 1): ORANGE for i in range(WEEKS) if n1[i]}),
          text("Lot-for-Lot: Eingang = Nettobedarf", color=WHITE, size=46, bold=True)], clear=True),
    Beat("Jetzt der Offset: Die Bestellung wird um die Lead Time nach vorn verschoben. Eingang in Woche zwei heisst Release in Woche eins. Rückwärts, nicht vorwärts.",
         [tab([R_NET(n1), R_REC(r1), R_REL(rel1)], hl={(2, i + 1): GREEN for i in range(WEEKS) if rel1[i]}),
          text("Release = Eingangswoche − LT", color=WHITE, size=46, bold=True)], clear=True),
    Beat("Mit fixer Losgrösse sechzig wird nur zweimal bestellt: Eingang sechzig in Woche zwei und in Woche sechs. Release in Woche eins und fünf. Dafür bleiben am Ende zehn Stück im Lager.",
         [tab([R_NET(n2), R_REC(r2), R_REL(rel2), R_END(e2)],
              hl={(2, 1): GREEN, (2, 5): GREEN, (3, 6): YELLOW}),
          text("Losgrösse 60: 2 Bestellungen, Restbestand 10", color=WHITE, size=46, bold=True)], clear=True),
    Beat("Der Trade-off: Lot for Lot bedeutet vier Bestellungen und kein Restlager. Die fixe Losgrösse spart Bestellungen, kostet aber Lagerhaltung. Die Lead Time wird immer abgezogen.",
         [table(["", "Lot-for-Lot", "Los 60"], [["Bestellungen", "4", "2"], ["Restbestand W6", "0", "10"]], size=56,
                hl={(0, 2): GREEN, (1, 1): GREEN}, id="t"),
          callout("Lead Time abziehen – nicht addieren!", color=RED, label="Prüfungsfalle", size=50)], clear=True),
])
