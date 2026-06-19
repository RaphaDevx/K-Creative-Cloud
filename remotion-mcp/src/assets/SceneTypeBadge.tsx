import React from 'react';
import {spring} from 'remotion';

interface SceneTypeBadgeProps {
  type: string;
  accentColor: string;
  localFrame: number;
  fps: number;
}

const TYPE_LABELS: Record<string, string> = {
  hook: 'HOOK',
  fact: 'FACT',
  explanation: 'INSIGHT',
  warning: 'MYTH-BUST',
  tip: 'PRO TIP',
  takeaway: 'TAKEAWAY',
};

export const SceneTypeBadge: React.FC<SceneTypeBadgeProps> = ({type, accentColor, localFrame, fps}) => {
  const scale = spring({
    frame: localFrame,
    fps,
    config: {damping: 8, stiffness: 220},
    from: 0,
    to: 1,
  });

  const label = TYPE_LABELS[type] ?? type.toUpperCase();

  const hex = accentColor.replace('#', '');
  const r = parseInt(hex.slice(0, 2), 16);
  const g = parseInt(hex.slice(2, 4), 16);
  const b = parseInt(hex.slice(4, 6), 16);

  const luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255;
  const textColor = luminance > 0.55 ? '#000000' : '#ffffff';

  return (
    <div
      style={{
        position: 'absolute',
        top: 112,
        left: 0,
        right: 0,
        display: 'flex',
        justifyContent: 'center',
        transform: `scale(${scale})`,
      }}
    >
      <div
        style={{
          backgroundColor: accentColor,
          color: textColor,
          fontFamily: 'system-ui, -apple-system, sans-serif',
          fontSize: 30,
          fontWeight: 800,
          letterSpacing: 4,
          paddingTop: 10,
          paddingBottom: 10,
          paddingLeft: 30,
          paddingRight: 30,
          borderRadius: 100,
          boxShadow: `0 0 20px rgba(${r},${g},${b},0.5)`,
        }}
      >
        {label}
      </div>
    </div>
  );
};
