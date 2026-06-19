import React from 'react';
import {spring, interpolate} from 'remotion';
import {VizData} from '../types';
import {hexToRgb} from './utils';

interface BarChartVizProps {
  viz: VizData;
  accentHex: string;
  localFrame: number;
  fps: number;
}

export const BarChartViz: React.FC<BarChartVizProps> = ({viz, accentHex, localFrame, fps}) => {
  const data = viz.data ?? [0.4, 0.7, 1.0, 0.55];
  const labels = viz.labels ?? data.map((_, i) => `Gruppe ${i + 1}`);
  const {r, g, b} = hexToRgb(accentHex);

  const plotLeft = 80, plotRight = 850, plotBottom = 340, plotTop = 30;
  const plotH = plotBottom - plotTop;
  const barH = Math.min(55, (plotH - (data.length - 1) * 12) / data.length);
  const barGap = 12;
  const maxBarW = plotRight - plotLeft;

  const axisOpacity = interpolate(localFrame, [0, 10], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });

  return (
    <svg viewBox="0 0 900 480" width={900} height={480} style={{overflow: 'visible'}}>
      {/* Y-axis */}
      <line
        x1={plotLeft} y1={plotTop} x2={plotLeft} y2={plotBottom}
        stroke="rgba(255,255,255,0.25)" strokeWidth={2} opacity={axisOpacity}
      />

      {data.map((val, i) => {
        const barProgress = spring({
          frame: Math.max(0, localFrame - i * 4),
          fps,
          config: {damping: 14, stiffness: 110},
          from: 0,
          to: 1,
        });
        const barW = val * maxBarW * barProgress;
        const totalRowH = barH + barGap;
        const y = plotTop + i * totalRowH + (plotH - data.length * totalRowH) / 2;

        const opacity = interpolate(Math.max(0, localFrame - i * 4), [0, 8], [0, 1], {
          extrapolateLeft: 'clamp',
          extrapolateRight: 'clamp',
        });

        const intensity = 0.25 + val * 0.45;

        return (
          <g key={i} opacity={opacity}>
            {/* Background track */}
            <rect
              x={plotLeft} y={y} width={maxBarW} height={barH}
              fill="rgba(255,255,255,0.05)" rx={6}
            />
            {/* Bar fill */}
            <rect
              x={plotLeft} y={y} width={barW} height={barH}
              fill={`rgba(${r},${g},${b},${intensity})`} rx={6}
            />
            {/* Right edge glow */}
            <rect
              x={plotLeft + barW - 4} y={y} width={4} height={barH}
              fill={accentHex} rx={2}
              style={{filter: `drop-shadow(0 0 8px rgba(${r},${g},${b},0.9))`}}
            />
            {/* Label */}
            <text
              x={plotLeft - 10} y={y + barH / 2 + 7}
              textAnchor="end"
              fill="rgba(255,255,255,0.8)"
              fontSize={22}
              fontFamily="system-ui, -apple-system, sans-serif"
            >
              {labels[i]}
            </text>
            {/* Value */}
            <text
              x={plotLeft + barW + 14} y={y + barH / 2 + 7}
              textAnchor="start"
              fill={accentHex}
              fontSize={22}
              fontWeight="700"
              fontFamily="system-ui, -apple-system, sans-serif"
            >
              {Math.round(val * 100)}%
            </text>
          </g>
        );
      })}

      {viz.caption && (
        <text
          x={450} y={460}
          textAnchor="middle"
          fill="rgba(255,255,255,0.55)"
          fontSize={20}
          fontFamily="'Courier New', monospace"
          opacity={axisOpacity}
        >
          {viz.caption}
        </text>
      )}
    </svg>
  );
};
