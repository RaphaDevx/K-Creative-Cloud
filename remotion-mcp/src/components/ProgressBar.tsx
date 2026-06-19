import React from 'react';

interface ProgressBarProps {
  progress: number;
  accentColor: string;
}

export const ProgressBar: React.FC<ProgressBarProps> = ({progress, accentColor}) => {
  const pct = `${Math.min(1, Math.max(0, progress)) * 100}%`;
  return (
    <div
      style={{
        position: 'absolute',
        bottom: 0,
        left: 0,
        right: 0,
        height: 6,
        backgroundColor: 'rgba(255,255,255,0.07)',
      }}
    >
      <div
        style={{
          height: '100%',
          width: pct,
          background: `linear-gradient(90deg, ${accentColor}88, ${accentColor})`,
          boxShadow: `0 0 10px ${accentColor}, 0 0 4px ${accentColor}`,
        }}
      />
    </div>
  );
};
