#!/usr/bin/env python3
"""Piggy im Stil der Referenzen (flach, braune Kontur, weiches Rosa) als eigene SVG-Zeichnung.
Original-Zeichnung (keine Pause der KI-Referenzen). Erzeugt SVG-Bausteine; build_ref_variants.py setzt die Icons zusammen."""

OUT = "#6E2F2B"      # Kontur (dunkles Rotbraun)
PINK = "#FFB8C6"     # Marken-Rosa
PINK_L = "#FFD3DC"
PINK_D = "#F598AC"
PINK_DD = "#E8788F"
HOOF = "#5A3A3A"
SW = 13

DEFS = f'''<defs>
<radialGradient id="gBody" cx="0.35" cy="0.3" r="0.85"><stop offset="0" stop-color="{PINK_L}"/><stop offset="0.55" stop-color="{PINK}"/><stop offset="1" stop-color="{PINK_D}"/></radialGradient>
<radialGradient id="gHead" cx="0.4" cy="0.3" r="0.85"><stop offset="0" stop-color="#FFD9E1"/><stop offset="0.55" stop-color="{PINK}"/><stop offset="1" stop-color="{PINK_D}"/></radialGradient>
<linearGradient id="gEar" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{PINK}"/><stop offset="1" stop-color="{PINK_D}"/></linearGradient>
<radialGradient id="gSnout" cx="0.4" cy="0.3" r="0.9"><stop offset="0" stop-color="#FFC8D2"/><stop offset="1" stop-color="{PINK_D}"/></radialGradient>
<radialGradient id="gCheek"><stop offset="0" stop-color="#F0607A" stop-opacity="0.7"/><stop offset="1" stop-color="#F0607A" stop-opacity="0"/></radialGradient>
<radialGradient id="gEye" cx="0.4" cy="0.35" r="0.8"><stop offset="0" stop-color="#8A5A3C"/><stop offset="1" stop-color="#3D2216"/></radialGradient>
<linearGradient id="gCoin" x1="0" y1="0" x2="0.3" y2="1"><stop offset="0" stop-color="#FFE29A"/><stop offset="0.55" stop-color="#FFC247"/><stop offset="1" stop-color="#FF9F0A"/></linearGradient>
</defs>'''


def st(fill, w=SW, extra=""):
    return f'fill="{fill}" stroke="{OUT}" stroke-width="{w}" stroke-linejoin="round" stroke-linecap="round" {extra}'


def pig(coin=False, head_only=False):
    """Figur nach rechts blickend, Koordinaten ca. 100..940 x 150..900."""
    g = []
    # Schwanz (Ringel)
    g.append(f'<path d="M200 570 C165 585 135 565 140 535 C145 505 185 500 195 525 C203 545 175 555 168 538 C163 522 180 515 188 524" fill="none" stroke="{OUT}" stroke-width="{SW+3}" stroke-linecap="round"/>')
    g.append(f'<path d="M200 570 C165 585 135 565 140 535 C145 505 185 500 195 525 C203 545 175 555 168 538 C163 522 180 515 188 524" fill="none" stroke="{PINK_D}" stroke-width="{SW-6}" stroke-linecap="round"/>')
    # hintere Beine
    g.append(f'<path d="M330 720 C320 790 322 840 318 868 C350 884 400 884 410 862 C406 830 412 790 420 740 Z" {st(PINK_D)}/>')
    g.append(f'<path d="M318 868 C322 892 410 896 412 866 C390 880 345 880 318 868Z" {st(HOOF)}/>')
    # Rumpf
    g.append(f'<path d="M180 600 C175 440 300 350 470 350 C640 350 760 450 745 620 C735 760 620 800 470 800 C310 800 185 745 180 600 Z" {st("url(#gBody)")}/>')
    # Münzschlitz
    g.append(f'<path d="M345 420 C380 405 440 400 500 404" fill="none" stroke="{OUT}" stroke-width="28" stroke-linecap="round"/>')
    g.append(f'<path d="M352 420 C385 408 440 404 495 407" fill="none" stroke="#8C4540" stroke-width="13" stroke-linecap="round"/>')
    # Glanz Rücken
    g.append('<path d="M250 470 C275 430 320 410 355 408" fill="none" stroke="#FFFFFF" stroke-opacity="0.55" stroke-width="16" stroke-linecap="round"/>')
    # vordere Beine
    g.append(f'<path d="M545 740 C550 800 548 840 552 872 C590 888 640 886 648 862 C640 830 645 790 650 745 Z" {st(PINK)}/>')
    g.append(f'<path d="M552 872 C556 898 648 898 648 866 C625 884 580 884 552 872Z" {st(HOOF)}/>')
    g.append(f'<path d="M690 715 C698 780 700 830 702 866 C735 880 785 876 792 852 C788 820 790 780 782 712 Z" {st(PINK_D)}/>')
    g.append(f'<path d="M702 866 C706 892 790 894 792 856 C770 876 728 878 702 866Z" {st(HOOF)}/>')
    g.append('<!--HEAD-->')
    # ferneres Ohr (hinter dem Kopf, klappt nach aussen um)
    g.append(f'<path d="M705 345 C698 268 748 212 812 204 C856 198 896 214 912 248 C886 238 862 262 852 300 C842 340 818 372 790 385 Z" {st("url(#gEar)")}/>')
    g.append(f'<path d="M742 330 C750 288 780 252 815 240 C802 272 800 302 786 345 Z" fill="{PINK_DD}" opacity="0.6"/>')
    # Kopf
    g.append(f'<path d="M440 560 C430 400 540 305 690 305 C830 305 925 400 915 540 C905 680 800 760 665 760 C530 760 445 690 440 560 Z" {st("url(#gHead)")}/>')
    # Haarbüschel
    g.append(f'<path d="M610 312 C600 280 615 262 630 252 C632 272 645 285 655 306" {st(PINK_D, 11)}/>')
    # nahes Ohr (hängt nach vorn)
    g.append(f'<path d="M485 380 C470 320 520 255 585 255 C640 258 665 320 645 380 C625 420 545 440 485 380 Z" {st("url(#gEar)")}/>')
    g.append(f'<path d="M515 365 C515 320 545 285 585 285 C575 320 590 360 560 395 C540 398 522 385 515 365Z" fill="{PINK_DD}" opacity="0.55"/>')
    # Wangen
    g.append('<ellipse cx="620" cy="600" rx="62" ry="40" fill="url(#gCheek)"/>')
    g.append('<ellipse cx="885" cy="520" rx="50" ry="36" fill="url(#gCheek)"/>')
    # Augen
    g.append(f'<ellipse cx="660" cy="500" rx="60" ry="72" fill="#FFFFFF" stroke="{OUT}" stroke-width="{SW-3}"/>')
    g.append('<ellipse cx="668" cy="506" rx="46" ry="56" fill="url(#gEye)"/><ellipse cx="672" cy="508" rx="26" ry="32" fill="#2A140D"/>')
    g.append('<circle cx="688" cy="480" r="15" fill="#FFFFFF"/><circle cx="650" cy="535" r="7" fill="#FFFFFF" opacity="0.9"/>')
    g.append(f'<path d="M610 440 C625 425 660 418 690 428" fill="none" stroke="{OUT}" stroke-width="10" stroke-linecap="round"/>')
    g.append(f'<ellipse cx="840" cy="448" rx="36" ry="52" fill="#FFFFFF" stroke="{OUT}" stroke-width="{SW-4}"/>')
    g.append('<ellipse cx="846" cy="452" rx="28" ry="40" fill="url(#gEye)"/><ellipse cx="848" cy="454" rx="16" ry="23" fill="#2A140D"/><circle cx="858" cy="436" r="10" fill="#FFFFFF"/>')
    g.append(f'<path d="M800 395 C815 385 845 385 860 395" fill="none" stroke="{OUT}" stroke-width="9" stroke-linecap="round"/>')
    # Schnauze
    g.append(f'<ellipse cx="800" cy="595" rx="98" ry="76" {st("url(#gSnout)")}/>')
    g.append(f'<ellipse cx="770" cy="597" rx="12" ry="22" fill="{OUT}"/><ellipse cx="832" cy="597" rx="12" ry="22" fill="{OUT}"/>')
    g.append('<ellipse cx="760" cy="555" rx="26" ry="10" fill="#FFFFFF" opacity="0.45"/>')
    # Mund (offen, lächelnd)
    g.append(f'<path d="M690 668 C705 725 765 740 815 705 C795 695 760 692 722 672 C710 666 698 664 690 668 Z" fill="#B0364A" stroke="{OUT}" stroke-width="{SW-3}" stroke-linejoin="round"/>')
    g.append('<path d="M722 704 C745 722 782 722 806 706 C788 698 752 696 722 704Z" fill="#F58A9A"/>')
    if coin:
        g.append(f'<g transform="translate(405 235) rotate(-14)"><ellipse cx="0" cy="0" rx="70" ry="70" {st("url(#gCoin)")}/><ellipse cx="0" cy="0" rx="48" ry="48" fill="none" stroke="#E08A00" stroke-width="8" opacity="0.8"/><path d="M-26 -20 C-12 -42 18 -44 30 -30" fill="none" stroke="#FFFFFF" stroke-opacity="0.75" stroke-width="9" stroke-linecap="round"/></g>')
    if head_only:
        g = g[g.index('<!--HEAD-->'):]
    return "\n".join(g)


def shadow(cx=520, cy=900, rx=360, ry=36, op=0.16):
    return f'<ellipse cx="{cx}" cy="{cy}" rx="{rx}" ry="{ry}" fill="#7A3B00" opacity="{op}"/>'
