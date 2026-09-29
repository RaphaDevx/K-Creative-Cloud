import React from 'react';
import {useCurrentFrame, useVideoConfig, spring, interpolate} from 'remotion';
import {SceneData} from '../types';
import {DotGrid} from '../assets/DotGrid';
import {ProgressBar} from '../components/ProgressBar';
import {ProgressDots} from '../components/ProgressDots';

interface SceneKineticProps {
  scene: SceneData;
  startFrame: number;
  globalProgress: number;
  currentSceneIndex: number;
  totalScenes: number;
}

const DIRECTIONS = [
  {x: -120, y: 0},
  {x: 120, y: 0},
  {x: 0, y: -80},
  {x: 60, y: 60},
  {x: -60, y: -60},
];

export const SceneKinetic: React.FC<SceneKineticProps> = ({
  scene,
  startFrame,
  globalProgress,
  currentSceneIndex,
  totalScenes,
}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const localFrame = frame - startFrame;

  const hex = scene.accent_hex.replace('#', '');
  const r = parseInt(hex.slice(0, 2), 16);
  const g = parseInt(hex.slice(2, 4), 16);
  const b = parseInt(hex.slice(4, 6), 16);

  const words = scene.headline.toUpperCase().split(' ');

  // Sweep line across screen
  const sweepX = interpolate(localFrame, [0, 12], [-1080, 1080], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });

  return (
    <>
      {/* Dark bg with tint */}
      <div style={{position: 'absolute', inset: 0, backgroundColor: `rgba(${r},${g},${b},0.08)`}} />
      <DotGrid opacity={0.05} />

      {/* Accent sweep line */}
      <div style={{
        position: 'absolute',
        top: 0,
        left: 0,
        bottom: 0,
        width: 4,
        backgroundColor: scene.accent_hex,
        boxShadow: `0 0 30px 10px rgba(${r},${g},${b},0.6)`,
        transform: `translateX(${sweepX}px)`,
      }} />

      {/* Large scene type label (faint watermark) */}
      <div style={{
        position: 'absolute',
        top: 90,
        left: 0,
        right: 0,
        textAlign: 'center',
        fontFamily: 'system-ui, sans-serif',
        fontSize: 28,
        fontWeight: 800,
        letterSpacing: 8,
        color: `rgba(${r},${g},${b},0.5)`,
        textTransform: 'uppercase',
      }}>
        {scene.type}
      </div>

      {/* Word-by-word kinetic headline */}
      <div style={{
        position: 'absolute',
        top: 680,
        left: 60,
        right: 60,
        display: 'flex',
        flexWrap: 'wrap',
        justifyContent: 'center',
        alignItems: 'center',
        gap: 16,
      }}>
        {words.map((word, i) => {
          const wordDelay = i * 4;
          const wordFrame = Math.max(0, localFrame - wordDelay);
          const dir = DIRECTIONS[i % DIRECTIONS.length];

          const tx = spring({frame: wordFrame, fps, config: {damping: 10, stiffness: 180}, from: dir.x, to: 0});
          const ty = spring({frame: wordFrame, fps, config: {damping: 10, stiffness: 180}, from: dir.y, to: 0});
          const sc = spring({frame: wordFrame, fps, config: {damping: 9, stiffness: 200}, from: 0.4, to: 1});
          const op = interpolate(wordFrame, [0, 5], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
          const isAccent = i % 2 === 1;

          return (
            <span
              key={i}
              style={{
                fontFamily: 'system-ui, sans-serif',
                fontSize: 108,
                fontWeight: 900,
                lineHeight: 1.05,
                color: isAccent ? scene.accent_hex : '#ffffff',
                textShadow: isAccent
                  ? `0 0 40px rgba(${r},${g},${b},0.8), 4px 4px 0 rgba(0,0,0,0.7)`
                  : '4px 4px 0 rgba(0,0,0,0.7)',
                transform: `translate(${tx}px, ${ty}px) scale(${sc})`,
                opacity: op,
                display: 'inline-block',
              }}
            >
              {word}
            </span>
          );
        })}
      </div>

      {/* Subtext */}
      <div style={{
        position: 'absolute',
        top: 1200,
        left: 80,
        right: 80,
        textAlign: 'center',
        fontFamily: 'system-ui, sans-serif',
        fontSize: 42,
        color: 'rgba(220,220,220,0.85)',
        lineHeight: 1.4,
        opacity: interpolate(Math.max(0, localFrame - 20), [0, 12], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'}),
      }}>
        {scene.subtext}
      </div>

      <ProgressDots currentScene={currentSceneIndex} totalScenes={totalScenes} accentColor={scene.accent_hex} />
      <ProgressBar progress={globalProgress} accentColor={scene.accent_hex} />
    </>
  );
};
