import React from 'react';
import {spring, interpolate} from 'remotion';
import {VizData} from '../types';
import {hexToRgb} from './utils';

interface HistogramVizProps {
  viz: VizData;
  accentHex: string;
  localFrame: number;
  fps: number;
}

export const HistogramViz: React.FC<HistogramVizProps> = ({viz, accentHex, localFrame, fps}) => {
  const data = viz.data ?? [0.3, 0.6, 1, 0.8, 0.5, 0.3, 0.15];
  const labels = viz.labels ?? data.map((_, i) => String(i + 1));
  const {r, g, b} = hexToRgb(accentHex);

  const plotLeft = 50, plotRight = 850, plotBottom = 360, plotTop = 20;
  const plotW = plotRight - plotLeft;
  const plotH = plotBottom - plotTop;
  const barGap = 8;
  const barW = (plotW - barGap * (data.length - 1)) / data.length;

  const axisOpacity = interpolate(localFrame, [0, 10], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });

  return (
    <svg viewBox="0 0 900 480" width={900} height={480} style={{overflow: 'visible'}}>
      {/* X-axis */}
      <line
        x1={plotLeft} y1={plotBottom} x2={plotRight} y2={plotBottom}
        stroke="rgba(255,255,255,0.25)" strokeWidth={2} opacity={axisOpacity}
      />

      {data.map((val, i) => {
        const barProgress = spring({
          frame: Math.max(0, localFrame - i * 3),
          fps,
          config: {damping: 12, stiffness: 120},
          from: 0,
          to: 1,
        });
        const barHeight = val * plotH * barProgress;
        const x = plotLeft + i * (barW + barGap);
        const y = plotBottom - barHeight;

        const opacity = interpolate(Math.max(0, localFrame - i * 3), [0, 8], [0, 1], {
          extrapolateLeft: 'clamp',
          extrapolateRight: 'clamp',
        });

        return (
          <g key={i} opacity={opacity}>
            {/* Bar fill */}
            <rect
              x={x} y={y} width={barW} height={barHeight}
              fill={`rgba(${r},${g},${b},0.3)`}
              rx={4}
            />
            {/* Bar top glow line */}
            <rect
              x={x} y={y} width={barW} height={3}
              fill={accentHex}
              rx={2}
              style={{filter: `drop-shadow(0 0 6px rgba(${r},${g},${b},0.9))`}}
            />
            {/* Label */}
            <text
              x={x + barW / 2} y={plotBottom + 30}
              textAnchor="middle"
              fill="rgba(255,255,255,0.7)"
              fontSize={20}
              fontFamily="system-ui, -apple-system, sans-serif"
            >
              {labels[i]}
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
