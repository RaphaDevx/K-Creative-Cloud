/*
 * Piggy Brand Core — Vektor-Kunst: Signet, Wortmarke, Accessoires, Logo/App-Icon/Splash.
 * Alle Farben kommen aus artColors(tokens, variant) → keine Hex-Werte in diesem File.
 * Koordinaten: Signet-Rahmen = viewBox(-44 -60 600 600), Kopfzentrum (256,292), rx 182, ry 160.
 */
(function (g) {
  'use strict';
  const PB = (g.PiggyBrand = g.PiggyBrand || {});
  const mix = (a, b, t) => PB.mix(a, b, t);

  // ------------------------------------------------------------ geometry anchors
  const A = {
    cx: 256, cy: 292, rx: 182, ry: 160,
    eyeL: [186, 262], eyeR: [326, 262],
    frame: { x: -44, y: -60, w: 600, h: 600 },
  };
  const headTopY = (x) => A.cy - A.ry * Math.sqrt(Math.max(0, 1 - Math.pow((x - A.cx) / A.rx, 2)));

  function rng(seed) {
    let s = seed >>> 0;
    return () => {
      s = (s + 0x6d2b79f5) >>> 0;
      let t = s;
      t = Math.imul(t ^ (t >>> 15), t | 1);
      t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
  }
  const f1 = (n) => Math.round(n * 10) / 10;

  // ------------------------------------------------------------ signet parts
  function signetDefs(c, u) {
    const m = c.m;
    return `
<radialGradient id="${u}-head" cx="0.36" cy="0.28" r="0.82"><stop offset="0" stop-color="${mix(m.skinLight, '#ffffff', 0.25)}"/><stop offset="0.42" stop-color="${m.skin}"/><stop offset="1" stop-color="${m.skinShade}"/></radialGradient>
<radialGradient id="${u}-ear" cx="0.45" cy="0.35" r="0.9"><stop offset="0" stop-color="${m.skinLight}"/><stop offset="0.6" stop-color="${m.skin}"/><stop offset="1" stop-color="${m.skinShade}"/></radialGradient>
<radialGradient id="${u}-snout" cx="0.42" cy="0.28" r="0.85"><stop offset="0" stop-color="${mix(m.snout, '#ffffff', 0.45)}"/><stop offset="0.65" stop-color="${m.snout}"/><stop offset="1" stop-color="${m.skinShade}"/></radialGradient>
<linearGradient id="${u}-coin" x1="0" y1="0" x2="0.3" y2="1"><stop offset="0" stop-color="${mix(m.coin, '#ffffff', 0.35)}"/><stop offset="0.55" stop-color="${m.coin}"/><stop offset="1" stop-color="${m.coinShade}"/></linearGradient>
<radialGradient id="${u}-cheek"><stop offset="0" stop-color="${m.cheek}" stop-opacity="0.75"/><stop offset="1" stop-color="${m.cheek}" stop-opacity="0"/></radialGradient>
<clipPath id="${u}-coinclip"><rect x="150" y="-20" width="212" height="176"/></clipPath>`;
  }

  function earsSvg(c, u) {
    const m = c.m;
    const one = `<path d="M146,214 C112,160 88,98 104,66 Q114,48 136,58 C178,80 222,116 246,156 Z" fill="url(#${u}-ear)"/>
<path d="M158,190 C134,150 118,108 126,86 Q132,76 144,82 C172,100 200,124 218,152 Z" fill="${m.earInner}" opacity="0.9"/>`;
    return `<g>${one}</g><g transform="matrix(-1 0 0 1 512 0)">${one}</g>`;
  }

  function headSvg(c, u, opts) {
    const m = c.m;
    const eye = (x, y, closed) => closed
      ? `<path d="M${x - 24},${y + 4} Q${x},${y - 22} ${x + 24},${y + 4}" fill="none" stroke="${m.eye}" stroke-width="10" stroke-linecap="round"/>`
      : `<ellipse cx="${x}" cy="${y}" rx="28" ry="35" fill="${m.eye}"/>
<circle cx="${x - 9}" cy="${y - 13}" r="11" fill="${m.eyeHighlight}"/><circle cx="${x + 9}" cy="${y + 14}" r="4.5" fill="${m.eyeHighlight}" opacity="0.9"/>`;
    const coin = opts.coin === false ? '' : `
<g clip-path="url(#${u}-coinclip)">
  <circle cx="256" cy="112" r="44" fill="url(#${u}-coin)" stroke="${m.coinShade}" stroke-width="6"/>
  <circle cx="256" cy="112" r="28" fill="none" stroke="${m.coinShade}" stroke-width="5" opacity="0.55"/>
  <path d="M232,94 Q244,80 262,78" fill="none" stroke="#ffffff" stroke-width="7" stroke-linecap="round" opacity="0.65"/>
</g>`;
    return `
<ellipse cx="${A.cx}" cy="${A.cy}" rx="${A.rx}" ry="${A.ry}" fill="url(#${u}-head)"/>
<ellipse cx="168" cy="196" rx="52" ry="22" transform="rotate(-32 168 196)" fill="#ffffff" opacity="0.5"/>
<circle cx="132" cy="236" r="9" fill="#ffffff" opacity="0.45"/>
${coin}
<rect x="210" y="146" width="92" height="22" rx="11" fill="${m.slot}"/>
<path d="M220,172 Q256,178 292,172" fill="none" stroke="${mix(m.skinLight, '#ffffff', 0.3)}" stroke-width="5" stroke-linecap="round" opacity="0.8"/>
<ellipse cx="136" cy="322" rx="40" ry="26" fill="url(#${u}-cheek)"/>
<ellipse cx="376" cy="322" rx="40" ry="26" fill="url(#${u}-cheek)"/>
${eye(A.eyeL[0], A.eyeL[1], opts.wink === 'L')}
${eye(A.eyeR[0], A.eyeR[1], opts.wink === 'R')}
<ellipse cx="256" cy="336" rx="68" ry="50" fill="url(#${u}-snout)"/>
<ellipse cx="236" cy="312" rx="20" ry="9" fill="#ffffff" opacity="0.55"/>
<ellipse cx="232" cy="338" rx="11" ry="17" fill="${m.nostril}"/>
<ellipse cx="280" cy="338" rx="11" ry="17" fill="${m.nostril}"/>
<path d="M226,404 Q256,428 286,404" fill="none" stroke="${m.mouth}" stroke-width="9" stroke-linecap="round"/>`;
  }

  // ------------------------------------------------------------ accessories (signet coords) + backgrounds (canvas coords)
  const ACC = {};
  const BG = {};

  // --- Hüte & Kopfschmuck
  ACC.partyHat = (c, u) => ({
    front: `<g transform="translate(314,150) rotate(20)">
  <clipPath id="${u}-ph"><path d="M-64,0 Q0,24 64,0 L7,-172 Q0,-182 -7,-172 Z"/></clipPath>
  <path d="M-64,0 Q0,24 64,0 L7,-172 Q0,-182 -7,-172 Z" fill="${c.a.violet}"/>
  <g clip-path="url(#${u}-ph)" stroke="${c.a.gold}" stroke-width="18" fill="none">
    <path d="M-80,-30 L80,-70"/><path d="M-80,-90 L80,-130"/><path d="M-80,-150 L80,-190"/></g>
  <path d="M-64,0 Q0,24 64,0" fill="none" stroke="${c.a.violetDark}" stroke-width="12" stroke-linecap="round"/>
  <path d="M-30,-40 L-6,-150" stroke="#ffffff" stroke-width="8" stroke-linecap="round" opacity="0.35"/>
  <circle cx="0" cy="-180" r="24" fill="${c.a.pink}"/><circle cx="-7" cy="-188" r="8" fill="#ffffff" opacity="0.6"/>
</g>`,
  });

  ACC.dominoMask = (c) => ({
    front: `<g>
  <path d="M118,262 C112,212 206,204 256,238 C306,204 400,212 394,262 C400,314 318,318 256,290 C194,318 112,314 118,262 Z M151,262 a35,31 0 1,0 70,0 a35,31 0 1,0 -70,0 Z M291,262 a35,31 0 1,0 70,0 a35,31 0 1,0 -70,0 Z" fill="${c.a.violet}" fill-rule="evenodd" stroke="${c.a.violetDark}" stroke-width="6" stroke-linejoin="round"/>
  <g fill="${c.a.gold}"><circle cx="256" cy="252" r="8"/><circle cx="146" cy="226" r="6"/><circle cx="366" cy="226" r="6"/><circle cx="140" cy="296" r="5"/><circle cx="372" cy="296" r="5"/></g>
  <path d="M118,258 C90,262 72,284 60,318 M118,266 C96,286 90,310 94,340" fill="none" stroke="${c.a.pink}" stroke-width="10" stroke-linecap="round"/>
  <path d="M394,258 C430,230 438,180 430,140" fill="none" stroke="${c.a.gold}" stroke-width="12" stroke-linecap="round"/>
  <path d="M430,140 C450,120 470,120 478,98 C452,100 432,110 430,140 Z" fill="${c.a.mint}"/>
</g>`,
  });

  ACC.roundGlasses = (c) => ({
    front: `<g fill="#ffffff" fill-opacity="0.22" stroke="${c.a.dark}" stroke-width="9">
  <circle cx="186" cy="264" r="46"/><circle cx="326" cy="264" r="46"/></g>
<path d="M232,258 Q256,242 280,258" fill="none" stroke="${c.a.dark}" stroke-width="9" stroke-linecap="round"/>
<path d="M140,256 L96,236 M372,256 L416,236" stroke="${c.a.dark}" stroke-width="8" stroke-linecap="round"/>
<path d="M160,244 Q170,232 184,230 M300,244 Q310,232 324,230" fill="none" stroke="#ffffff" stroke-width="6" stroke-linecap="round" opacity="0.8"/>`,
  });

  ACC.receipt = (c) => ({
    front: `<g transform="translate(368,378) rotate(14)">
  <path d="M0,0 H112 V132 l-14,12 -14,-12 -14,12 -14,-12 -14,12 -14,-12 -14,12 -14,-12 Z" fill="#ffffff" stroke="${c.a.dark}" stroke-opacity="0.25" stroke-width="4" stroke-linejoin="round"/>
  <g stroke="${c.a.dark}" stroke-opacity="0.35" stroke-width="7" stroke-linecap="round"><path d="M18,24 H94"/><path d="M18,48 H70"/><path d="M18,72 H84"/></g>
  <path d="M18,104 H94" stroke="${c.a.gold}" stroke-width="10" stroke-linecap="round"/>
</g>`,
  });

  ACC.bunnyEars = (c) => ({
    back: `<g transform="rotate(-14 204 150)"><ellipse cx="204" cy="36" rx="38" ry="112" fill="#ffffff"/><ellipse cx="204" cy="46" rx="19" ry="82" fill="${c.a.pink}" opacity="0.8"/></g>
<g transform="rotate(16 308 150)"><ellipse cx="308" cy="36" rx="38" ry="112" fill="#ffffff"/><ellipse cx="308" cy="46" rx="19" ry="82" fill="${c.a.pink}" opacity="0.8"/></g>`,
    front: `<path d="M104,210 Q256,96 408,210" fill="none" stroke="${c.a.mint}" stroke-width="16" stroke-linecap="round"/>`,
  });

  ACC.easterEgg = (c, u) => ({
    front: `<g transform="translate(84,448) rotate(-12)">
  <clipPath id="${u}-egg"><path d="M0,-58 C34,-58 46,-10 46,14 C46,44 26,60 0,60 C-26,60 -46,44 -46,14 C-46,-10 -34,-58 0,-58 Z"/></clipPath>
  <path d="M0,-58 C34,-58 46,-10 46,14 C46,44 26,60 0,60 C-26,60 -46,44 -46,14 C-46,-10 -34,-58 0,-58 Z" fill="${c.a.blue}"/>
  <g clip-path="url(#${u}-egg)"><path d="M-60,4 l12,-12 12,12 12,-12 12,12 12,-12 12,12 12,-12 12,12 12,-12" fill="none" stroke="#ffffff" stroke-width="9" stroke-linejoin="round"/>
  <g fill="${c.a.gold}"><circle cx="-18" cy="-28" r="6"/><circle cx="14" cy="-34" r="6"/><circle cx="-10" cy="34" r="6"/><circle cx="20" cy="30" r="6"/></g></g>
  <ellipse cx="-16" cy="-30" rx="8" ry="14" fill="#ffffff" opacity="0.45"/>
</g>`,
  });

  ACC.heartBalloon = (c) => ({
    extendsRight: true,
    back: `<path d="M406,470 C470,400 440,300 470,190" fill="none" stroke="${c.a.dark}" stroke-width="4" stroke-linecap="round" opacity="0.7"/>
<path d="M470,194 C404,150 396,86 440,72 C460,66 470,80 470,92 C470,80 480,66 500,72 C544,86 536,150 470,194 Z" fill="${c.a.red}"/>
<ellipse cx="444" cy="100" rx="12" ry="20" transform="rotate(-30 444 100)" fill="#ffffff" opacity="0.5"/>`,
  });

  ACC.swimRing = (c) => ({
    back: `<path d="M62,452 A194,58 0 0,1 450,452" fill="none" stroke="#ffffff" stroke-width="48"/>
<path d="M62,452 A194,58 0 0,1 450,452" pathLength="100" fill="none" stroke="${c.a.red}" stroke-width="48" stroke-dasharray="12.5 12.5"/>`,
    front: `<path d="M450,452 A194,58 0 0,1 62,452" fill="none" stroke="#ffffff" stroke-width="48"/>
<path d="M450,452 A194,58 0 0,1 62,452" pathLength="100" fill="none" stroke="${c.a.red}" stroke-width="48" stroke-dasharray="12.5 12.5" stroke-dashoffset="6"/>
<path d="M120,486 Q256,520 392,486" fill="none" stroke="#ffffff" stroke-width="8" stroke-linecap="round" opacity="0.6"/>`,
  });

  ACC.strawHat = (c) => {
    const straw = mix(c.a.gold, '#ffffff', 0.45), strawD = mix(c.a.gold, c.a.brown, 0.25);
    return {
      hidesCoin: true,
      front: `<g transform="rotate(-7 256 124)">
  <ellipse cx="256" cy="128" rx="214" ry="44" fill="${straw}" stroke="${strawD}" stroke-width="6"/>
  <path d="M152,122 C150,34 362,34 360,122 Z" fill="${straw}" stroke="${strawD}" stroke-width="6" stroke-linejoin="round"/>
  <path d="M152,98 C212,112 300,112 360,98 L361,122 C300,136 212,136 151,122 Z" fill="${c.a.pink}"/>
  <path d="M120,140 Q256,176 392,140 M200,70 Q256,56 312,70" fill="none" stroke="${strawD}" stroke-width="4" stroke-linecap="round" opacity="0.5"/>
  <circle cx="330" cy="104" r="14" fill="${c.a.red}"/><circle cx="330" cy="104" r="5" fill="${c.a.gold}"/>
</g>`,
    };
  };

  ACC.swissFlag = (c) => ({
    extendsRight: true,
    front: `<g transform="translate(-26 0)"><path d="M444,500 L452,68" stroke="${c.a.brown}" stroke-width="11" stroke-linecap="round"/>
<circle cx="452" cy="60" r="11" fill="${c.a.gold}"/>
<path d="M454,76 C488,64 520,92 552,78 L552,172 C520,186 488,158 454,170 Z" fill="${c.a.red}"/>
<g fill="#ffffff"><rect x="494" y="96" width="18" height="58" rx="3"/><rect x="474" y="116" width="58" height="18" rx="3"/></g></g>`,
  });

  ACC.cowBell = (c) => ({
    front: `<path d="M104,396 Q256,508 408,396" fill="none" stroke="${c.a.red}" stroke-width="28" stroke-linecap="round"/>
<path d="M104,396 Q256,508 408,396" pathLength="100" fill="none" stroke="#ffffff" stroke-width="7" stroke-linecap="round" stroke-dasharray="0.1 8"/>
<path d="M214,478 Q214,446 256,446 Q298,446 298,478 L310,528 Q256,544 202,528 Z" fill="${c.a.gold}" stroke="${mix(c.a.gold, c.a.brown, 0.5)}" stroke-width="6" stroke-linejoin="round"/>
<path d="M210,500 Q256,512 302,500" fill="none" stroke="${mix(c.a.gold, c.a.brown, 0.5)}" stroke-width="6"/>
<path d="M232,468 Q236,456 250,454" fill="none" stroke="#ffffff" stroke-width="6" stroke-linecap="round" opacity="0.7"/>`,
  });

  ACC.flowerCrown = (c) => {
    const xs = [118, 158, 206, 256, 306, 354, 394];
    const cols = [c.a.white, c.a.pink, c.a.gold, c.a.blue, c.a.pink, c.a.white, c.a.violet];
    let leaves = '', flowers = '';
    xs.forEach((x, i) => {
      const y = headTopY(x) + 10;
      if (i < xs.length - 1) {
        const mx = (x + xs[i + 1]) / 2, my = headTopY(mx) + 4;
        leaves += `<ellipse cx="${f1(mx)}" cy="${f1(my)}" rx="18" ry="9" transform="rotate(${i % 2 ? 25 : -25} ${f1(mx)} ${f1(my)})" fill="${c.a.green}"/>`;
      }
      let petals = '';
      for (let k = 0; k < 5; k++) {
        const a = (k / 5) * Math.PI * 2 - Math.PI / 2;
        petals += `<circle cx="${f1(x + Math.cos(a) * 14)}" cy="${f1(y + Math.sin(a) * 14)}" r="13" fill="${cols[i]}"/>`;
      }
      flowers += petals + `<circle cx="${x}" cy="${f1(y)}" r="9" fill="${i === 2 ? c.a.orange : c.a.gold}"/>`;
    });
    return { front: `<g stroke="${c.a.dark}" stroke-opacity="0.12" stroke-width="2">${leaves}${flowers}</g>` };
  };

  ACC.witchHat = (c) => ({
    hidesCoin: true,
    front: `<g transform="rotate(-8 256 130)">
  <path d="M170,124 C200,60 222,4 240,-40 C262,-20 300,-30 336,-12 C300,24 330,80 344,124 Z" fill="${c.a.violetDark}" stroke-linejoin="round"/>
  <ellipse cx="256" cy="128" rx="178" ry="34" fill="${c.a.violetDark}"/>
  <path d="M176,106 C230,118 290,118 340,106 L344,124 C290,138 230,138 172,124 Z" fill="${c.a.orange}"/>
  <rect x="242" y="104" width="30" height="28" rx="6" fill="none" stroke="${c.a.gold}" stroke-width="6"/>
  <path d="M110,134 Q256,158 400,130" fill="none" stroke="#ffffff" stroke-width="5" stroke-linecap="round" opacity="0.25"/>
</g>`,
  });

  ACC.lantern = (c, u) => {
    const body = mix(c.a.orange, '#ffffff', 0.45);
    return {
      extendsRight: true,
      back: `<radialGradient id="${u}-glow"><stop offset="0" stop-color="${c.a.gold}" stop-opacity="0.85"/><stop offset="1" stop-color="${c.a.gold}" stop-opacity="0"/></radialGradient>
<circle cx="470" cy="300" r="110" fill="url(#${u}-glow)"/>`,
      front: `<path d="M540,520 C520,380 500,200 470,92" fill="none" stroke="${c.a.brown}" stroke-width="10" stroke-linecap="round"/>
<path d="M470,96 L470,236" stroke="${c.a.dark}" stroke-width="3" opacity="0.7"/>
<path d="M428,248 C428,222 512,222 512,248 C532,304 502,346 470,348 C438,346 408,304 428,248 Z" fill="${body}" stroke="${c.a.rust}" stroke-width="5"/>
<path d="M470,264 l9,19 21,2 -16,14 5,21 -19,-11 -19,11 5,-21 -16,-14 21,-2 Z" fill="${c.a.gold}" stroke="${c.a.orange}" stroke-width="3" stroke-linejoin="round"/>
<path d="M458,228 C452,212 460,204 470,200 C476,212 474,222 470,230 M476,226 C486,214 498,214 504,220" fill="${c.a.green}" stroke="${c.a.green}" stroke-width="6" stroke-linecap="round"/>`,
    };
  };

  ACC.santaHat = (c) => ({
    extendsRight: true,
    hidesCoin: true,
    front: `<path d="M144,164 C168,52 300,8 374,40 C434,66 458,132 460,196 C432,160 404,140 384,154 L370,160 Z" fill="${c.a.red}"/>
<path d="M190,120 C230,70 300,52 350,62" fill="none" stroke="#ffffff" stroke-width="10" stroke-linecap="round" opacity="0.25"/>
<path d="M112,172 C150,126 362,126 400,172 C410,198 384,210 362,200 C300,176 212,176 150,200 C128,210 102,198 112,172 Z" fill="#ffffff"/>
<circle cx="460" cy="204" r="28" fill="#ffffff"/>`,
  });

  ACC.sunglasses = (c) => {
    const lens = `<path d="M134,236 Q134,222 152,222 L226,222 Q244,222 242,240 L236,270 Q230,300 196,300 L172,300 Q140,300 136,272 Z" fill="${c.a.dark}"/>
<path d="M156,238 L182,238 M154,254 L166,254" stroke="#ffffff" stroke-width="7" stroke-linecap="round" opacity="0.55"/>`;
    return {
      front: `<g>${lens}</g><g transform="matrix(-1 0 0 1 512 0)">${lens}</g>
<path d="M242,234 Q256,226 270,234" fill="none" stroke="${c.a.dark}" stroke-width="9" stroke-linecap="round"/>
<path d="M136,232 L100,222 M376,232 L412,222" stroke="${c.a.dark}" stroke-width="8" stroke-linecap="round"/>`,
    };
  };

  ACC.scarf = (c) => ({
    front: `<g transform="translate(0 -34)"><path d="M340,462 L370,542 L420,526 L394,452 Z" fill="${c.a.rust}"/>
<path d="M376,540 l-4,14 M392,536 l-2,14 M408,530 l0,14" stroke="${c.a.rust}" stroke-width="6" stroke-linecap="round"/>
<path d="M96,404 C170,470 342,470 416,404 L426,446 C352,514 160,514 86,446 Z" fill="${c.a.rust}"/>
<path d="M92,424 C168,490 344,490 420,424" fill="none" stroke="${c.a.orange}" stroke-width="10"/>
<path d="M352,480 L386,470" stroke="${c.a.orange}" stroke-width="10"/></g>`,
  });

  ACC.beanie = (c) => ({
    hidesCoin: true,
    front: `<path d="M162,196 C152,58 360,58 350,196 Z" fill="${c.a.blue}"/>
<g stroke="${c.a.blueDark}" stroke-width="6" stroke-linecap="round" opacity="0.35"><path d="M210,178 C206,130 218,100 234,88"/><path d="M256,178 L256,76"/><path d="M302,178 C306,130 294,100 278,88"/></g>
<rect x="150" y="160" width="212" height="48" rx="24" fill="${c.a.blueDark}"/>
<circle cx="256" cy="64" r="30" fill="#ffffff"/><circle cx="246" cy="54" r="9" fill="#ffffff" opacity="0.8"/>`,
  });

  ACC.skiGoggles = (c, u) => ({
    front: `<linearGradient id="${u}-gog" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="${c.a.gold}"/><stop offset="0.5" stop-color="${c.a.orange}"/><stop offset="1" stop-color="${c.a.violet}"/></linearGradient>
<rect x="150" y="176" width="212" height="14" rx="7" fill="${c.a.dark}" opacity="0.85"/>
<path d="M196,158 H316 Q340,158 340,183 Q340,208 316,208 H284 Q274,208 268,198 Q256,188 244,198 Q238,208 228,208 H196 Q172,208 172,183 Q172,158 196,158 Z" fill="url(#${u}-gog)" stroke="#ffffff" stroke-width="7" stroke-linejoin="round"/>
<path d="M192,174 L210,174" stroke="#ffffff" stroke-width="5" stroke-linecap="round" opacity="0.7"/>`,
  });

  // --- Hintergründe (Canvas-Koordinaten W×H) — nur App-Icon & Splash
  function scatter(seed, n, W, H, fn, avoid) {
    const r = rng(seed);
    let out = '';
    for (let i = 0; i < n; i++) {
      const x = r() * W, y = r() * H, s = 0.6 + r() * 0.8, rot = r() * 360, k = r();
      if (avoid && Math.hypot(x - W / 2, (y - H * 0.55) * 1.2) < avoid) continue;
      out += fn(f1(x), f1(y), s, f1(rot), k, i);
    }
    return out;
  }
  const palette5 = (c) => [c.a.gold, c.a.pink, c.a.blue, c.a.mint, c.a.violet];

  BG.confetti = (c, W, H) => scatter(11, 70, W, H, (x, y, s, rot, k, i) => {
    const col = palette5(c)[i % 5];
    return k < 0.5
      ? `<rect x="${x}" y="${y}" width="${f1(28 * s)}" height="${f1(12 * s)}" rx="${f1(6 * s)}" transform="rotate(${rot} ${x} ${y})" fill="${col}"/>`
      : `<circle cx="${x}" cy="${y}" r="${f1(8 * s)}" fill="${col}"/>`;
  }, W * 0.3);
  BG.coins = (c, W, H) => scatter(5, 26, W, H, (x, y, s) =>
    `<circle cx="${x}" cy="${y}" r="${f1(26 * s)}" fill="${c.m.coin}" stroke="${c.m.coinShade}" stroke-width="${f1(6 * s)}"/><circle cx="${x}" cy="${y}" r="${f1(14 * s)}" fill="none" stroke="${c.m.coinShade}" stroke-width="${f1(4 * s)}" opacity="0.5"/>`, W * 0.33);
  BG.petals = (c, W, H) => scatter(21, 40, W, H, (x, y, s, rot, k, i) =>
    `<ellipse cx="${x}" cy="${y}" rx="${f1(16 * s)}" ry="${f1(9 * s)}" transform="rotate(${rot} ${x} ${y})" fill="${[c.a.white, c.a.pink, c.a.mint][i % 3]}" opacity="0.9"/>`, W * 0.3);
  BG.hearts = (c, W, H) => scatter(9, 26, W, H, (x, y, s, rot, k, i) =>
    `<path transform="translate(${x} ${y}) rotate(${f1(rot / 8 - 20)}) scale(${f1(s)})" d="M0,22 C-30,2 -30,-24 -12,-26 C-4,-27 0,-20 0,-14 C0,-20 4,-27 12,-26 C30,-24 30,2 0,22 Z" fill="${[c.a.red, c.a.pink][i % 2]}" opacity="0.85"/>`, W * 0.33);
  BG.waves = (c, W, H) => {
    let s = '';
    [[0.72, c.a.blue, 0.45], [0.8, c.a.blue, 0.7], [0.88, c.a.blueDark, 0.6]].forEach(([yy, col, op], j) => {
      const y = H * yy, a = H * 0.025;
      let d = `M0,${f1(y)}`;
      for (let x = 0; x <= W; x += W / 8) d += ` Q${f1(x + W / 32 + j * 20)},${f1(y - a)} ${f1(x + W / 16 + j * 20)},${f1(y)} T${f1(x + W / 8 + j * 20)},${f1(y)}`;
      s += `<path d="${d} V${H} H0 Z" fill="${col}" opacity="${op}"/>`;
    });
    return s;
  };
  BG.sun = (c, W, H) => {
    const cx = W * 0.82, cy = H * 0.17, r = W * 0.085;
    let rays = '';
    for (let i = 0; i < 12; i++) {
      const a = (i / 12) * Math.PI * 2;
      rays += `<path d="M${f1(cx + Math.cos(a) * r * 1.35)},${f1(cy + Math.sin(a) * r * 1.35)} L${f1(cx + Math.cos(a) * r * 1.8)},${f1(cy + Math.sin(a) * r * 1.8)}"/>`;
    }
    return `<g stroke="${c.a.gold}" stroke-width="${f1(W * 0.02)}" stroke-linecap="round">${rays}</g><circle cx="${f1(cx)}" cy="${f1(cy)}" r="${f1(r)}" fill="${c.a.gold}"/>`;
  };
  BG.fireworks = (c, W, H) => {
    const bursts = [[0.2, 0.2, c.a.gold], [0.8, 0.16, c.a.red], [0.86, 0.62, c.a.white], [0.14, 0.66, c.a.pink]];
    return bursts.map(([bx, by, col], j) => {
      const cx = W * bx, cy = H * by, r1 = W * 0.03, r2 = W * 0.1;
      let s = '';
      for (let i = 0; i < 12; i++) {
        const a = (i / 12) * Math.PI * 2 + j * 0.3;
        s += `<path d="M${f1(cx + Math.cos(a) * r1)},${f1(cy + Math.sin(a) * r1)} L${f1(cx + Math.cos(a) * r2)},${f1(cy + Math.sin(a) * r2)}"/>`;
        s += `<circle cx="${f1(cx + Math.cos(a) * r2 * 1.2)}" cy="${f1(cy + Math.sin(a) * r2 * 1.2)}" r="${f1(W * 0.006)}" fill="${col}" stroke="none"/>`;
      }
      return `<g stroke="${col}" stroke-width="${f1(W * 0.01)}" stroke-linecap="round">${s}</g>`;
    }).join('');
  };
  BG.mountains = (c, W, H) => {
    const g1 = mix(c.a.green, '#ffffff', 0.2), g2 = c.a.green;
    return `<path d="M${-W * 0.1},${H} L${W * 0.22},${H * 0.62} L${W * 0.36},${H * 0.74} L${W * 0.55},${H * 0.5} L${W * 0.8},${H * 0.72} L${W * 0.92},${H * 0.64} L${W * 1.1},${H} Z" fill="${g1}" opacity="0.9"/>
<path d="M${W * 0.47},${H * 0.58} L${W * 0.55},${H * 0.5} L${W * 0.63},${H * 0.58} L${W * 0.58},${H * 0.57} L${W * 0.55},${H * 0.6} L${W * 0.52},${H * 0.57} Z" fill="#ffffff"/>
<path d="M${W * 0.16},${H * 0.68} L${W * 0.22},${H * 0.62} L${W * 0.28},${H * 0.67} L${W * 0.22},${H * 0.66} Z" fill="#ffffff"/>
<path d="M0,${H * 0.86} Q${W * 0.5},${H * 0.78} ${W},${H * 0.86} V${H} H0 Z" fill="${g2}"/>`;
  };
  BG.bats = (c, W, H) => {
    const moon = `<circle cx="${W * 0.8}" cy="${H * 0.18}" r="${W * 0.08}" fill="${mix(c.a.gold, '#ffffff', 0.5)}"/>`;
    return moon + scatter(3, 9, W, H * 0.5, (x, y, s) =>
      `<path transform="translate(${x} ${y}) scale(${f1(s * W / 1024)})" d="M0,0 C-10,-14 -24,-14 -40,-6 C-32,-2 -30,6 -34,12 C-24,6 -14,8 -8,14 C-4,6 4,6 8,14 C14,8 24,6 34,12 C30,6 32,-2 40,-6 C24,-14 10,-14 0,0 Z" fill="${c.a.dark}" opacity="0.8"/>`, W * 0.22);
  };
  BG.stars = (c, W, H) => scatter(17, 34, W, H * 0.7, (x, y, s, rot, k) =>
    k < 0.7 ? `<circle cx="${x}" cy="${y}" r="${f1(4 * s)}" fill="${mix(c.a.gold, '#ffffff', 0.6)}"/>`
      : `<path transform="translate(${x} ${y}) scale(${f1(s)})" d="M0,-16 C2,-4 4,-2 16,0 C4,2 2,4 0,16 C-2,4 -4,2 -16,0 C-4,-2 -2,-4 0,-16 Z" fill="${mix(c.a.gold, '#ffffff', 0.4)}"/>`, W * 0.25);
  BG.leaves = (c, W, H) => scatter(13, 30, W, H, (x, y, s, rot, k, i) =>
    `<g transform="translate(${x} ${y}) rotate(${rot}) scale(${f1(s * 1.2)})"><path d="M0,-26 C18,-10 18,10 0,26 C-18,10 -18,-10 0,-26 Z" fill="${[c.a.orange, c.a.rust, c.a.brown][i % 3]}"/><path d="M0,-20 L0,30" stroke="${c.a.brown}" stroke-width="3" opacity="0.5"/></g>`, W * 0.3);
  BG.snow = (c, W, H) => scatter(31, 60, W, H, (x, y, s, rot, k) =>
    k < 0.8 ? `<circle cx="${x}" cy="${y}" r="${f1(7 * s)}" fill="#ffffff" opacity="0.9"/>`
      : `<g transform="translate(${x} ${y}) rotate(${rot})" stroke="#ffffff" stroke-width="5" stroke-linecap="round"><path d="M0,-18 V18 M-15.6,-9 L15.6,9 M-15.6,9 L15.6,-9"/></g>`, W * 0.26);

  // ------------------------------------------------------------ wordmark
  const WM = { x: -12, y: -112, w: 1024, h: 440 };
  function wordmarkSvg(c, u, opts) {
    const L = c.logo;
    const letters = [
      { d: 'M22,22 V300 M178,100 A78,78 0 1,1 22,100 A78,78 0 1,1 178,100', cx: 100, rot: -4, dy: 0 },
      { d: 'M258,22 V178', cx: 258, rot: 3, dy: -6 },
      { d: 'M494,100 A78,78 0 1,1 338,100 A78,78 0 1,1 494,100 M494,22 V222 A78,78 0 0,1 348.5,261', cx: 416, rot: -3, dy: 4 },
      { d: 'M730,100 A78,78 0 1,1 574,100 A78,78 0 1,1 730,100 M730,22 V222 A78,78 0 0,1 584.5,261', cx: 652, rot: 4, dy: -4 },
      { d: 'M810,22 V100 A78,78 0 0,0 966,100 M966,22 V222 A78,78 0 0,1 820.5,261', cx: 888, rot: -2, dy: 2 },
    ];
    const bounce = opts.bounce !== false;
    const glyphs = (color, dy0) => letters.map((l) =>
      `<path d="${l.d}" transform="${bounce ? `translate(0 ${l.dy + dy0}) rotate(${l.rot} ${l.cx} 100)` : `translate(0 ${dy0})`}" stroke="${color}"/>`).join('');
    const dot = (dy0, fill, stroke) => `<circle cx="${bounce ? 262 : 258}" cy="${-64 + dy0 + (bounce ? -6 : 0)}" r="34" fill="${fill}" stroke="${stroke}" stroke-width="7"/>`;
    return `<g fill="none" stroke-width="44" stroke-linecap="round" stroke-linejoin="round">
  ${glyphs(L.wordmarkDepth, 12)}
  ${glyphs(L.wordmark, 0)}
</g>
${dot(12, L.wordmarkDepth, L.wordmarkDepth)}
${dot(0, `url(#${u}-coin)`, L.iDotShade)}
<path d="M${bounce ? 244 : 240},${bounce ? -86 : -80} Q${bounce ? 252 : 248},${bounce ? -96 : -90} ${bounce ? 266 : 262},${bounce ? -96 : -90}" fill="none" stroke="#ffffff" stroke-width="7" stroke-linecap="round" opacity="0.7"/>`;
  }

  // ------------------------------------------------------------ composition
  function resolveAcc(variant) {
    const ids = (variant && variant.accessories) || [];
    return ids.map((a) => (typeof a === 'string' ? a : a.id)).filter((id) => ACC[id]);
  }
  function resolveBg(variant) {
    const ids = (variant && variant.background) || [];
    return (Array.isArray(ids) ? ids : [ids]).filter((id) => BG[id]);
  }

  /** Signet-Gruppe (Rahmen-Koordinaten) inkl. Accessoires. */
  function signetGroup(c, variant, u, opts) {
    opts = opts || {};
    const accs = resolveAcc(variant).map((id) => ACC[id](c, u + '-' + id));
    const earsOver = accs.some((a) => a.earsOver);
    return `<g>
${accs.map((a) => a.back || '').join('\n')}
${earsSvg(c, u)}
${headSvg(c, u, { coin: accs.some((a) => a.hidesCoin) ? false : opts.coin, wink: opts.wink })}
${accs.map((a) => a.front || '').join('\n')}
${earsOver ? earsSvg(c, u) : ''}
</g>`;
  }

  const svgOpen = (vb, w, h) => `<svg xmlns="http://www.w3.org/2000/svg" viewBox="${vb}"${w ? ` width="${w}" height="${h}"` : ''}>`;
  let UID = 0;
  const nextUid = (p) => (p || 'pg') + (++UID).toString(36);

  function renderSignet(raw, variant, opts) {
    opts = opts || {};
    const c = PB.artColors(raw, variant), u = opts.uid || nextUid('sg');
    const F = A.frame;
    return `${svgOpen(`${F.x} ${F.y} ${F.w} ${F.h}`, opts.size, opts.size)}<defs>${signetDefs(c, u)}</defs>${signetGroup(c, variant, u, opts)}</svg>`;
  }

  function renderWordmark(raw, variant, opts) {
    opts = opts || {};
    const c = PB.artColors(raw, variant), u = opts.uid || nextUid('wm');
    return `${svgOpen(`${WM.x} ${WM.y} ${WM.w} ${WM.h}`)}<defs>${signetDefs(c, u)}</defs>${wordmarkSvg(c, u, opts)}</svg>`;
  }

  /** layout: 'horizontal' | 'stacked' */
  function renderLogo(raw, variant, opts) {
    opts = opts || {};
    const layout = opts.layout || 'horizontal';
    const c = PB.artColors(raw, variant), u = opts.uid || nextUid('lg');
    const F = A.frame;
    const sig = (x, y, s) => `<g transform="translate(${x} ${y}) scale(${s}) translate(${-F.x} ${-F.y})">${signetGroup(c, variant, u, opts)}</g>`;
    const wm = (x, y, s) => `<g transform="translate(${x} ${y}) scale(${s}) translate(${-WM.x} ${-WM.y})">${wordmarkSvg(c, u, opts)}</g>`;
    let vb, body;
    if (layout === 'stacked') {
      const ws = 0.5;
      vb = `0 0 600 ${Math.round(600 + WM.h * ws - 40)}`;
      body = sig(0, 0, 1) + wm((600 - WM.w * ws) / 2, 540, ws);
    } else {
      const ws = 0.64;
      // Wortmarke: x-Höhen-Mitte (y=100) auf Kopfzentrum ausrichten; Accessoires rechts → mehr Abstand
      const wy = (A.cy - F.y) - (100 - WM.y) * ws;
      const wx = resolveAcc(variant).some((id) => ACC[id](c, u).extendsRight) ? 630 : 560;
      vb = `0 0 ${Math.round(wx + WM.w * ws + 44)} 600`;
      body = sig(0, 0, 1) + wm(wx, wy, ws);
    }
    return `${svgOpen(vb)}<defs>${signetDefs(c, u)}</defs>${body}</svg>`;
  }

  /** App-Icon (quadratisch, randlos; iOS maskiert selbst). adaptive=true → Android-Vordergrund transparent im 66%-Safe-Bereich. */
  function renderAppIcon(raw, variant, opts) {
    opts = opts || {};
    const W = 1024, c = PB.artColors(raw, variant), u = opts.uid || nextUid('ic');
    const F = A.frame;
    const s = opts.adaptive ? 1.02 : 1.72;
    const hx = W / 2, hy = opts.adaptive ? 540 : 590;
    const tx = hx - (A.cx - F.x) * s, ty = hy - (A.cy - F.y) * s;
    const I = c.icon;
    const bg = opts.adaptive ? '' : `
<radialGradient id="${u}-bg" cx="0.5" cy="0.42" r="0.75"><stop offset="0" stop-color="${I.bgFrom}"/><stop offset="0.75" stop-color="${I.bgTo}"/><stop offset="1" stop-color="${I.bgRim}"/></radialGradient>`;
    const layers = opts.adaptive ? '' : `<rect width="${W}" height="${W}" fill="url(#${u}-bg)"/>
${resolveBg(variant).map((id) => BG[id](c, W, W)).join('\n')}
<ellipse cx="${hx}" cy="${hy + A.ry * s * 0.9}" rx="${A.rx * s * 0.78}" ry="${26 * s}" fill="#000000" opacity="0.12"/>`;
    return `${svgOpen(`0 0 ${W} ${W}`, opts.size, opts.size)}<defs>${signetDefs(c, u)}${bg}</defs>${layers}
<g transform="translate(${f1(tx)} ${f1(ty)}) scale(${s}) translate(${-F.x} ${-F.y})">${signetGroup(c, variant, u, opts)}</g></svg>`;
  }

  /** Splash: transparentes Logo (Expo splash.image, resizeMode contain) oder volle Fläche (screen=true, 1284×2778). */
  function renderSplash(raw, variant, opts) {
    opts = opts || {};
    const c = PB.artColors(raw, variant), u = opts.uid || nextUid('sp');
    if (opts.screen) c.logo = Object.assign({}, c.logo, { wordmark: c.splash.wordmark, wordmarkDepth: c.splash.wordmarkDepth });
    const F = A.frame;
    const inner = (x, y, sw) => {
      const ws = 0.56;
      return `<g transform="translate(${x} ${y}) scale(${sw})"><g transform="translate(${-F.x} ${-F.y})">${signetGroup(c, variant, u, opts)}</g>
<g transform="translate(${(600 - WM.w * ws) / 2} 540) scale(${ws}) translate(${-WM.x} ${-WM.y})">${wordmarkSvg(c, u, opts)}</g></g>`;
    };
    if (!opts.screen) {
      return `${svgOpen('0 0 1024 1024')}<defs>${signetDefs(c, u)}</defs>${inner(212, 150, 1)}</svg>`;
    }
    const W = 1284, H = 2778, sw = 1.4;
    const bgc = c.splash.bg;
    return `${svgOpen(`0 0 ${W} ${H}`)}<defs>${signetDefs(c, u)}</defs><rect width="${W}" height="${H}" fill="${bgc}"/>
<g opacity="0.55">${resolveBg(variant).map((id) => BG[id](c, W, H)).join('\n')}</g>
${inner((W - 600 * sw) / 2, H * 0.3, sw)}</svg>`;
  }

  Object.assign(PB, {
    ART_ANCHORS: A, ACCESSORIES: ACC, BACKGROUNDS: BG,
    renderSignet, renderWordmark, renderLogo, renderAppIcon, renderSplash,
  });
  if (typeof module !== 'undefined' && module.exports) module.exports = PB;
})(typeof globalThis !== 'undefined' ? globalThis : this);
