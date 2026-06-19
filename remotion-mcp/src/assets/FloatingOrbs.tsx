import React from 'react';
import {useCurrentFrame, useVideoConfig} from 'remotion';

interface FloatingOrbsProps {
  accentColor: string;
}

export const FloatingOrbs: React.FC<FloatingOrbsProps> = ({accentColor}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const t = frame / fps;

  const hex = accentColor.replace('#', '');
  const r = parseInt(hex.slice(0, 2), 16);
  const g = parseInt(hex.slice(2, 4), 16);
  const b = parseInt(hex.slice(4, 6), 16);

  const orbs = [
    {x: 15, y: 20, size: 320, speed: 0.28, phase: 0, opacity: 0.09},
    {x: 82, y: 68, size: 260, speed: 0.18, phase: 2.1, opacity: 0.07},
    {x: 50, y: 48, size: 420, speed: 0.14, phase: 4.2, opacity: 0.05},
    {x: 22, y: 78, size: 210, speed: 0.35, phase: 1.0, opacity: 0.08},
    {x: 78, y: 22, size: 290, speed: 0.22, phase: 3.3, opacity: 0.06},
  ];

  return (
    <div style={{position: 'absolute', top: 0, left: 0, right: 0, bottom: 0, overflow: 'hidden'}}>
      {orbs.map((orb, i) => {
        const floatX = Math.sin(t * orb.speed + orb.phase) * 35;
        const floatY = Math.cos(t * orb.speed * 0.7 + orb.phase) * 45;
        return (
          <div
            key={i}
            style={{
              position: 'absolute',
              left: `${orb.x}%`,
              top: `${orb.y}%`,
              width: orb.size,
              height: orb.size,
              transform: `translate(${floatX}px, ${floatY}px) translate(-50%, -50%)`,
              borderRadius: '50%',
              background: `radial-gradient(circle, rgba(${r},${g},${b},${orb.opacity * 2.2}) 0%, rgba(${r},${g},${b},${orb.opacity}) 40%, transparent 70%)`,
              filter: 'blur(25px)',
            }}
          />
        );
      })}
    </div>
  );
};
