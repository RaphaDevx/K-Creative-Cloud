import {hexToRgb} from '../utils/colors';

export {hexToRgb};

function erf(x: number): number {
  const t = 1 / (1 + 0.3275911 * Math.abs(x));
  const poly = t * (0.254829592 + t * (-0.284496736 + t * (1.421413741 + t * (-1.453152027 + t * 1.061405429))));
  const res = 1 - poly * Math.exp(-x * x);
  return x >= 0 ? res : -res;
}

function normalPdf(x: number): number {
  return Math.exp(-0.5 * x * x) / Math.sqrt(2 * Math.PI);
}

function normalCdf(x: number): number {
  return 0.5 * (1 + erf(x / Math.sqrt(2)));
}

export function skewNormalPdf(x: number, alpha: number): number {
  return 2 * normalPdf(x) * normalCdf(alpha * x);
}

export function buildCurvePath(
  alpha: number,
  xMin: number,
  xMax: number,
  numPoints = 200,
): {d: string; fillD: string} {
  const pts: {x: number; y: number}[] = [];
  for (let i = 0; i <= numPoints; i++) {
    const xVal = xMin + (i / numPoints) * (xMax - xMin);
    pts.push({x: xVal, y: skewNormalPdf(xVal, alpha)});
  }
  const maxY = Math.max(...pts.map((p) => p.y));

  // SVG plot area: x [50,850], y axis top=20 bottom=360
  const svgLeft = 50, svgRight = 850, yBase = 360, yTop = 20;
  const svgW = svgRight - svgLeft;
  const svgH = yBase - yTop;

  const toSvg = (xVal: number, yVal: number) => ({
    sx: svgLeft + ((xVal - xMin) / (xMax - xMin)) * svgW,
    sy: yBase - (yVal / maxY) * svgH,
  });

  const pathPts = pts.map((p) => toSvg(p.x, p.y));
  const d = pathPts.map((p, i) => `${i === 0 ? 'M' : 'L'}${p.sx.toFixed(1)},${p.sy.toFixed(1)}`).join(' ');

  const first = pathPts[0];
  const last = pathPts[pathPts.length - 1];
  const fillD = `M${svgLeft},${yBase} L${first.sx.toFixed(1)},${first.sy.toFixed(1)} ${pathPts
    .slice(1)
    .map((p) => `L${p.sx.toFixed(1)},${p.sy.toFixed(1)}`)
    .join(' ')} L${last.sx.toFixed(1)},${yBase} Z`;

  return {d, fillD};
}

export function markerXtoSvg(value: number): number {
  return 50 + value * 800;
}
