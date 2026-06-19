export function hexToRgb(hex: string): {r: number; g: number; b: number} {
  const cleaned = hex.replace('#', '');
  const fullHex =
    cleaned.length === 3
      ? cleaned
          .split('')
          .map((c) => c + c)
          .join('')
      : cleaned;
  const r = parseInt(fullHex.substring(0, 2), 16);
  const g = parseInt(fullHex.substring(2, 4), 16);
  const b = parseInt(fullHex.substring(4, 6), 16);
  return {r, g, b};
}

export function darkenHex(hex: string, factor: number): string {
  const {r, g, b} = hexToRgb(hex);
  const dr = Math.max(0, Math.round(r * (1 - factor)));
  const dg = Math.max(0, Math.round(g * (1 - factor)));
  const db = Math.max(0, Math.round(b * (1 - factor)));
  return (
    '#' +
    [dr, dg, db]
      .map((v) => v.toString(16).padStart(2, '0'))
      .join('')
  );
}

export const ACCENT_COLORS: Record<string, string> = {
  hook: '#FF4444',
  fact: '#FFD700',
  explanation: '#4FC3F7',
  warning: '#FF7043',
  tip: '#66BB6A',
  takeaway: '#CE93D8',
};
