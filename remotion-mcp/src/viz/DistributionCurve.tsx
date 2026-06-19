import React from 'react';
import {spring, interpolate} from 'remotion';
import {VizData, VizMarker} from '../types';
import {hexToRgb, buildCurvePath, markerXtoSvg} from './utils';
import {AnnotationMarker} from './AnnotationMarker';

// Default marker positions per skew type (pedagogically correct)
const DEFAULT_MARKERS: Record<string, VizMarker[]> = {
  left: [
    {label: 'Mittelwert', value: 0.40, color: '#FF6B9D'},
    {label: 'Median',     value: 0.50, color: '#FFD700'},
    {label: 'Modus',      value: 0.62, color: '#4FC3F7'},
  ],
  right: [
    {label: 'Modus',      value: 0.38, color: '#4FC3F7'},
    {label: 'Median',     value: 0.50, color: '#FFD700'},
    {label: 'Mittelwert', value: 0.60, color: '#FF6B9D'},
  ],
  none: [
    {label: 'μ = Median = Modus', value: 0.50, color: '#FFD700'},
  ],
};

interface DistributionCurveProps {
  viz: VizData;
  accentHex: string;
  localFrame: number;
  fps: number;
}

export const DistributionCurve: React.FC<DistributionCurveProps> = ({
  viz,
  accentHex,
  localFrame,
  fps,
}) => {
  const skewKey = viz.skew ?? 'none';
  const alpha = skewKey === 'left' ? -4 : skewKey === 'right' ? 4 : 0;
  const xRange: [number, number] = skewKey === 'none' ? [-3.5, 3.5] : [-3.5, 3.5];

  const {d: strokeD, fillD} = buildCurvePath(alpha, xRange[0], xRange[1]);
  const markers = viz.markers ?? DEFAULT_MARKERS[skewKey];

  const {r, g, b} = hexToRgb(accentHex);

  // Curve draw-in: strokeDashoffset 1→0
  const drawProgress = spring({
    frame: localFrame,
    fps,
    config: {damping: 18, stiffness: 80},
    from: 1,
    to: 0,
  });

  // Fill fade-in (delayed)
  const fillOpacity = interpolate(Math.max(0, localFrame - 8), [0, 20], [0, 0.22], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });

  // X-axis fade
  const axisOpacity = interpolate(localFrame, [0, 12], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });

  return (
    <svg
      viewBox="0 0 900 480"
      width={900}
      height={480}
      style={{overflow: 'visible'}}
    >
      {/* Filled area */}
      <path
        d={fillD}
        fill={`rgba(${r},${g},${b},${fillOpacity})`}
      />

      {/* Glow under curve */}
      <path
        d={fillD}
        fill={`rgba(${r},${g},${b},0.08)`}
        style={{filter: `blur(12px)`}}
      />

      {/* Curve stroke — animated draw-in via pathLength */}
      <path
        d={strokeD}
        fill="none"
        stroke={accentHex}
        strokeWidth={4}
        pathLength={1}
        strokeDasharray={1}
        strokeDashoffset={drawProgress}
        strokeLinecap="round"
        style={{filter: `drop-shadow(0 0 10px rgba(${r},${g},${b},0.9))`}}
      />

      {/* X-axis line */}
      <line
        x1={50} y1={360} x2={850} y2={360}
        stroke="rgba(255,255,255,0.25)"
        strokeWidth={2}
        opacity={axisOpacity}
      />

      {/* Annotation markers */}
      {markers.map((m, i) => (
        <AnnotationMarker
          key={m.label}
          label={m.label}
          svgX={markerXtoSvg(m.value)}
          color={m.color ?? accentHex}
          localFrame={localFrame}
          fps={fps}
          delayFrames={18 + i * 6}
          yTop={20}
          yBase={360}
        />
      ))}

      {/* Caption / LaTeX note */}
      {viz.caption && (
        <text
          x={450}
          y={460}
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
