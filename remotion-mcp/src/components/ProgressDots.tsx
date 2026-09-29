import React from 'react';

interface ProgressDotsProps {
  currentScene: number;
  totalScenes: number;
  accentColor: string;
}

export const ProgressDots: React.FC<ProgressDotsProps> = ({currentScene, totalScenes, accentColor}) => {
  return (
    <div
      style={{
        position: 'absolute',
        top: 62,
        left: 0,
        right: 0,
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
        gap: 18,
      }}
    >
      {Array.from({length: totalScenes}).map((_, i) => {
        const isActive = i === currentScene;
        return (
          <div
            key={i}
            style={{
              width: isActive ? 20 : 10,
              height: isActive ? 20 : 10,
              borderRadius: '50%',
              backgroundColor: isActive ? accentColor : 'rgba(255,255,255,0.22)',
              boxShadow: isActive ? `0 0 14px ${accentColor}, 0 0 5px ${accentColor}` : 'none',
              flexShrink: 0,
            }}
          />
        );
      })}
    </div>
  );
};
