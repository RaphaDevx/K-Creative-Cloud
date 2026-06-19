import React from 'react';

interface DotGridProps {
  opacity?: number;
}

export const DotGrid: React.FC<DotGridProps> = ({opacity = 0.035}) => {
  return (
    <div
      style={{
        position: 'absolute',
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        backgroundImage: 'radial-gradient(circle, rgba(255,255,255,0.8) 1px, transparent 1px)',
        backgroundSize: '44px 44px',
        opacity,
      }}
    />
  );
};
