# K-Creative Desktop — UX Redesign & Icon Designer Integration
# Gates ledger for session 2026-09-16 (updated: single-window architecture)

Scope: Icon Designer module (`icon-designer.html`) fully wired into Electron — IPC bridge,
dashboard navigation, package bundling, and FastAPI WebSocket/HTTP canvas endpoints.

---

## G1: Pre-build validator passes all checks

  CHECK: node /home/raphael/K-Dev/Projekte/K-Creative-Cloud/desktop/scripts/validate.js
  EXPECT: All checks passed

---

## G2: icon-designer.html is in package.json build.files[]

  CHECK: node -e "const p=require('./package.json');console.log(p.build.files.includes('icon-designer.html')?'PRESENT':'MISSING')"
  CWD: /home/raphael/K-Dev/Projekte/K-Creative-Cloud/desktop
  EXPECT: PRESENT

---

## G3: main.js defines DESIGNER_URL constant

  CHECK: node -e "const s=require('fs').readFileSync('./main.js','utf8');console.log(s.includes('DESIGNER_URL')?'OK':'MISSING')"
  CWD: /home/raphael/K-Dev/Projekte/K-Creative-Cloud/desktop
  EXPECT: OK

---

## G4: Canvas IPC handlers registered in main.js (no separate designer window)

  CHECK: node -e "const s=require('fs').readFileSync('./main.js','utf8');const h=['canvas-exec','canvas-get-state','canvas-load-state'];const missing=h.filter(c=>!s.includes(\"'\"+c+\"'\"));const noSep=!s.includes('designerWindow = new BrowserWindow');console.log(missing.length===0&&noSep?'ALL_PRESENT':'MISSING: '+missing.join(',')+(noSep?'':' +separateWindow'))"
  CWD: /home/raphael/K-Dev/Projekte/K-Creative-Cloud/desktop
  EXPECT: ALL_PRESENT

---

## G5: preload.js exposes canvas bridge methods (no openDesigner — single-window)

  CHECK: node -e "const s=require('fs').readFileSync('./preload.js','utf8');const m=['canvasExec','canvasGetState','canvasLoadState'];const miss=m.filter(x=>!s.includes(x));const noOpen=!s.includes('openDesigner');console.log(miss.length===0&&noOpen?'ALL_PRESENT':'FAIL')"
  CWD: /home/raphael/K-Dev/Projekte/K-Creative-Cloud/desktop
  EXPECT: ALL_PRESENT

---

## G6: dashboard.html has inline Icon Designer nav item (nav('designer'), no external window)

  CHECK: node -e "const s=require('fs').readFileSync('./dashboard.html','utf8');const ok=s.includes(\"nav('designer')\")&&s.includes('Icon Designer')&&!s.includes('openDesignerWindow');console.log(ok?'OK':'MISSING')"
  CWD: /home/raphael/K-Dev/Projekte/K-Creative-Cloud/desktop
  EXPECT: OK

---

## G7: FastAPI /ws/canvas WebSocket endpoint defined in server.py

  CHECK: node -e "const s=require('fs').readFileSync('../studio/server.py','utf8');console.log(s.includes('@app.websocket(\"/ws/canvas\")')?'OK':'MISSING')"
  CWD: /home/raphael/K-Dev/Projekte/K-Creative-Cloud/desktop
  EXPECT: OK

---

## G8: FastAPI /api/canvas/exec POST endpoint defined in server.py

  CHECK: node -e "const s=require('fs').readFileSync('../studio/server.py','utf8');console.log(s.includes('@app.post(\"/api/canvas/exec\")')?'OK':'MISSING')"
  CWD: /home/raphael/K-Dev/Projekte/K-Creative-Cloud/desktop
  EXPECT: OK

---

## G9: FastAPI /api/canvas/state GET endpoint defined in server.py

  CHECK: node -e "const s=require('fs').readFileSync('../studio/server.py','utf8');console.log(s.includes('@app.get(\"/api/canvas/state\")')?'OK':'MISSING')"
  CWD: /home/raphael/K-Dev/Projekte/K-Creative-Cloud/desktop
  EXPECT: OK

---

## G10: icon-designer.html WebSocket handler uses typed message format

The WS handler must dispatch on `msg.type === 'exec'` and respond to `get-state`,
not treat every incoming message as a bare canvas command.

  CHECK: node -e "const s=require('fs').readFileSync('./icon-designer.html','utf8');const ok=s.includes(\"msg.type === 'exec'\")&&s.includes(\"msg.type === 'get-state'\");console.log(ok?'OK':'MISSING')"
  CWD: /home/raphael/K-Dev/Projekte/K-Creative-Cloud/desktop
  EXPECT: OK

---

## G11: openDesigner() in main.js creates a separate BrowserWindow (not reuses mainWindow)

  CHECK: node -e "const s=require('fs').readFileSync('./main.js','utf8');const ok=s.includes('designerWindow = new BrowserWindow');console.log(ok?'OK':'MISSING')"
  CWD: /home/raphael/K-Dev/Projekte/K-Creative-Cloud/desktop
  EXPECT: OK

---

## G12: Build-dmg-mac.sh Step 0 runs validate.js before sync

  CHECK: node -e "const s=require('fs').readFileSync('./scripts/build-dmg-mac.sh','utf8');const i0=s.indexOf('[0/8]');const i1=s.indexOf('[1/8]');console.log(i0>-1&&i0<i1&&s.includes('validate.js')?'OK':'MISSING')"
  CWD: /home/raphael/K-Dev/Projekte/K-Creative-Cloud/desktop
  EXPECT: OK

---

---

## G13: Vibe-Chat dock present in dashboard.html

  CHECK: node -e "const s=require('fs').readFileSync('./dashboard.html','utf8');const ok=s.includes('vibe-dock')&&s.includes('toggleVibeDock')&&s.includes('sendVibe')&&s.includes('vibe-pill');console.log(ok?'OK':'MISSING')"
  CWD: /home/raphael/K-Dev/Projekte/K-Creative-Cloud/desktop
  EXPECT: OK

---

## G14: Activity bar with AI Cursor toggle in dashboard.html

  CHECK: node -e "const s=require('fs').readFileSync('./dashboard.html','utf8');const ok=s.includes('activity-bar')&&s.includes('toggleAiCursor')&&s.includes('setActivity');console.log(ok?'OK':'MISSING')"
  CWD: /home/raphael/K-Dev/Projekte/K-Creative-Cloud/desktop
  EXPECT: OK

---

## G15: Designer opens as inline tab (no separate BrowserWindow), lazy iframe load

  CHECK: node -e "const s=require('fs').readFileSync('./dashboard.html','utf8');const ok=s.includes('lazyLoadDesigner')&&s.includes('designer-frame')&&s.includes('studio-mode');console.log(ok?'OK':'MISSING')"
  CWD: /home/raphael/K-Dev/Projekte/K-Creative-Cloud/desktop
  EXPECT: OK

---

## G16: Update check interval is 30 minutes (not 4 hours)

  CHECK: node -e "const s=require('fs').readFileSync('./main.js','utf8');const ok=s.includes('30 * 60 * 1000')&&!s.includes('4 * 60 * 60 * 1000');console.log(ok?'OK':'MISSING')"
  CWD: /home/raphael/K-Dev/Projekte/K-Creative-Cloud/desktop
  EXPECT: OK

---

---

## G17: logo-creator.html is in package.json build.files[]

  CHECK: node -e "const p=require('./package.json');console.log(p.build.files.includes('logo-creator.html')?'PRESENT':'MISSING')"
  CWD: /home/raphael/K-Dev/Projekte/K-Creative-Cloud/desktop
  EXPECT: PRESENT

---

## G18: dashboard.html has Logo Creator nav + tab + lazyLoadLogo

  CHECK: node -e "const s=require('fs').readFileSync('./dashboard.html','utf8');const ok=s.includes(\"nav('logo')\")&&s.includes('logo-frame')&&s.includes('lazyLoadLogo')&&s.includes('Logo Creator');console.log(ok?'OK':'MISSING')"
  CWD: /home/raphael/K-Dev/Projekte/K-Creative-Cloud/desktop
  EXPECT: OK

---

## G19: logo-creator.html has superellipse math, Fibonacci grid, trace panel

  CHECK: node -e "const s=require('fs').readFileSync('./logo-creator.html','utf8');const ok=s.includes('squirclePath')&&s.includes('drawFibonacciGrid')&&s.includes('runTrace')&&s.includes('ImageTracer')&&s.includes('PHI');console.log(ok?'OK':'MISSING')"
  CWD: /home/raphael/K-Dev/Projekte/K-Creative-Cloud/desktop
  EXPECT: OK

---

## G20: STUDIO_TABS includes 'logo' in dashboard.html

  CHECK: node -e "const s=require('fs').readFileSync('./dashboard.html','utf8');const ok=s.includes(\"STUDIO_TABS = new Set(['designer', 'logo'])\");console.log(ok?'OK':'MISSING')"
  CWD: /home/raphael/K-Dev/Projekte/K-Creative-Cloud/desktop
  EXPECT: OK

---

## Summary

Total gates: 20
Required handoffs: 0

Pending work (out of scope for these gates — tracked separately):
- Video/Motion Engine module (Remotion + FFmpeg)
- Audio/Sound Engine module (Tone.js + FastAPI)
- Raster/Photo editing module
- Server-side SVG validation + render endpoint in server.py (/api/canvas/render)
