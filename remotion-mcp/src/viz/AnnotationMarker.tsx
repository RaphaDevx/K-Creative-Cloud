import React from 'react';
import {spring, interpolate} from 'remotion';
import {hexToRgb} from './utils';

interface AnnotationMarkerProps {
  label: string;
  svgX: number;
  color: string;
  localFrame: number;
  fps: number;
  delayFrames?: number;
  yTop?: number;
  yBase?: number;
}

export const AnnotationMarker: React.FC<AnnotationMarkerProps> = ({
  label,
  svgX,
  color,
  localFrame,
  fps,
  delayFrames = 0,
  yTop = 20,
  yBase = 360,
}) => {
  const delayed = Math.max(0, localFrame - delayFrames);

  const opacity = interpolate(delayed, [0, 10], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });

  const lineHeight = spring({
    frame: delayed,
    fps,
    config: {damping: 14, stiffness: 120},
    from: 0,
    to: 1,
  });

  const labelY = spring({
    frame: delayed,
    fps,
    config: {damping: 12, stiffness: 100},
    from: yTop - 30,
    to: yTop - 8,
  });

  const {r, g, b} = hexToRgb(color);
  const lineLen = (yBase - yTop) * lineHeight;

  return (
    <g opacity={opacity}>
      <line
        x1={svgX}
        y1={yBase}
        x2={svgX}
        y2={yBase - lineLen}
        stroke={color}
        strokeWidth={2.5}
        strokeDasharray="6 3"
        style={{filter: `drop-shadow(0 0 6px rgba(${r},${g},${b},0.8))`}}
      />
      <text
        x={svgX}
        y={labelY}
        textAnchor="middle"
        fill={color}
        fontSize={22}
        fontWeight="700"
        fontFamily="system-ui, -apple-system, sans-serif"
        style={{filter: `drop-shadow(0 0 8px rgba(${r},${g},${b},0.9))`}}
      >
        {label}
      </text>
    </g>
  );
};
