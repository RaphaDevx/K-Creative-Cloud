import React from 'react';
import {spring, interpolate} from 'remotion';

interface HeadlineTextProps {
  text: string;
  accentColor: string;
  localFrame: number;
  fps: number;
}

export const HeadlineText: React.FC<HeadlineTextProps> = ({text, accentColor, localFrame, fps}) => {
  const translateY = spring({
    frame: localFrame,
    fps,
    config: {damping: 12, stiffness: 120},
    from: 60,
    to: 0,
  });

  const opacity = interpolate(localFrame, [0, 8], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });

  const words = text.toUpperCase().split(' ');

  const hex = accentColor.replace('#', '');
  const r = parseInt(hex.slice(0, 2), 16);
  const g = parseInt(hex.slice(2, 4), 16);
  const b = parseInt(hex.slice(4, 6), 16);

  return (
    <div
      style={{
        position: 'absolute',
        top: 760,
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
          maxWidth: 900,
          textAlign: 'center',
          fontFamily: 'system-ui, -apple-system, sans-serif',
          fontSize: 92,
          fontWeight: '900',
          lineHeight: 1.15,
          letterSpacing: 1,
          wordWrap: 'break-word',
          overflowWrap: 'break-word',
        }}
      >
        {words.map((word, i) => {
          const isAccent = i % 2 === 1;
          return (
            <span
              key={i}
              style={{
                color: isAccent ? accentColor : '#ffffff',
                textShadow: isAccent
                  ? `0 0 35px rgba(${r},${g},${b},0.7), 3px 3px 0px rgba(0,0,0,0.65)`
                  : '3px 3px 0px rgba(0,0,0,0.65)',
              }}
            >
              {word}
              {i < words.length - 1 ? ' ' : ''}
            </span>
          );
        })}
      </div>
    </div>
  );
};
