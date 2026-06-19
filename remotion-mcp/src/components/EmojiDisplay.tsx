import React from 'react';
import {spring} from 'remotion';

interface EmojiDisplayProps {
  emoji: string;
  accentColor: string;
  localFrame: number;
  fps: number;
}

export const EmojiDisplay: React.FC<EmojiDisplayProps> = ({emoji, accentColor, localFrame, fps}) => {
  const scale = spring({
    frame: localFrame,
    fps,
    config: {damping: 8, stiffness: 130},
    from: 0,
    to: 1,
  });

  const rotation = spring({
    frame: localFrame,
    fps,
    config: {damping: 10, stiffness: 100},
    from: -18,
    to: 0,
  });

  const t = localFrame / fps;
  const floatY = Math.sin(t * 1.4) * 10;

  const hex = accentColor.replace('#', '');
  const r = parseInt(hex.slice(0, 2), 16);
  const g = parseInt(hex.slice(2, 4), 16);
  const b = parseInt(hex.slice(4, 6), 16);

  return (
    <div
      style={{
        position: 'absolute',
        top: 360,
        left: 90,
        right: 90,
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
        transform: `scale(${scale}) rotate(${rotation}deg) translateY(${floatY}px)`,
        transformOrigin: 'center center',
      }}
    >
      <div
        style={{
          position: 'absolute',
          width: 220,
          height: 220,
          borderRadius: '50%',
          background: `radial-gradient(circle, rgba(${r},${g},${b},0.35) 0%, transparent 70%)`,
          filter: 'blur(30px)',
        }}
      />
      <div
        style={{
          fontSize: 145,
          lineHeight: 1,
          fontFamily: '"Noto Color Emoji", "Apple Color Emoji", "Segoe UI Emoji", system-ui, sans-serif',
          filter: `drop-shadow(0 0 18px rgba(${r},${g},${b},0.55))`,
          position: 'relative',
        }}
      >
        {emoji}
      </div>
    </div>
  );
};
