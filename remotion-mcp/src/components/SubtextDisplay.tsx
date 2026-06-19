import React from 'react';
import {spring, interpolate} from 'remotion';

interface SubtextDisplayProps {
  text: string;
  accentColor: string;
  localFrame: number;
  fps: number;
}

export const SubtextDisplay: React.FC<SubtextDisplayProps> = ({text, accentColor, localFrame, fps}) => {
  const delayedFrame = Math.max(0, localFrame - 12);

  const translateY = spring({
    frame: delayedFrame,
    fps,
    config: {damping: 14, stiffness: 100},
    from: 30,
    to: 0,
  });

  const opacity = interpolate(delayedFrame, [0, 10], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });

  const hex = accentColor.replace('#', '');
  const r = parseInt(hex.slice(0, 2), 16);
  const g = parseInt(hex.slice(2, 4), 16);
  const b = parseInt(hex.slice(4, 6), 16);

  return (
    <div
      style={{
        position: 'absolute',
        top: 1140,
        left: 90,
        right: 90,
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
        transform: `translateY(${translateY}px)`,
        opacity,
      }}
    >
      <div
        style={{
          maxWidth: 860,
          textAlign: 'center',
          fontFamily: 'system-ui, -apple-system, sans-serif',
          fontSize: 40,
          fontWeight: 400,
          color: 'rgba(240,240,240,0.95)',
          lineHeight: 1.5,
          wordWrap: 'break-word',
          overflowWrap: 'break-word',
          backgroundColor: `rgba(${r},${g},${b},0.13)`,
          border: `1px solid rgba(${r},${g},${b},0.28)`,
          borderRadius: 20,
          paddingTop: 28,
          paddingBottom: 28,
          paddingLeft: 40,
          paddingRight: 40,
        }}
      >
        {text}
      </div>
    </div>
  );
};
