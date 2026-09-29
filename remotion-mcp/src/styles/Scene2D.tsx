import React from 'react';
import {useCurrentFrame, useVideoConfig, spring, interpolate} from 'remotion';
import {SceneData} from '../types';
import {CharacterDisplay} from '../assets/characters/CharacterDisplay';
import {DotGrid} from '../assets/DotGrid';
import {ProgressBar} from '../components/ProgressBar';
import {ProgressDots} from '../components/ProgressDots';
import {SceneTypeBadge} from '../assets/SceneTypeBadge';

interface Scene2DProps {
  scene: SceneData;
  startFrame: number;
  globalProgress: number;
  currentSceneIndex: number;
  totalScenes: number;
  characterId?: string;
}

export const Scene2D: React.FC<Scene2DProps> = ({
  scene,
  startFrame,
  globalProgress,
  currentSceneIndex,
  totalScenes,
  characterId = 'default',
}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const localFrame = frame - startFrame;

  const hex = scene.accent_hex.replace('#', '');
  const r = parseInt(hex.slice(0, 2), 16);
  const g = parseInt(hex.slice(2, 4), 16);
  const b = parseInt(hex.slice(4, 6), 16);

  // Speech bubble entrance
  const bubbleFrame = Math.max(0, localFrame - 4);
  const bubbleScale = spring({frame: bubbleFrame, fps, config: {damping: 10, stiffness: 160}, from: 0, to: 1});
  const bubbleOp = interpolate(bubbleFrame, [0, 6], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});

  // Subtext entrance
  const subtextFrame = Math.max(0, localFrame - 16);
  const subtextOp = interpolate(subtextFrame, [0, 10], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  const subtextY = spring({frame: subtextFrame, fps, config: {damping: 14, stiffness: 100}, from: 30, to: 0});

  return (
    <>
      {/* Light-ish background */}
      <div style={{position: 'absolute', inset: 0, backgroundColor: '#0d0d12'}} />
      <DotGrid opacity={0.03} />

      {/* Accent gradient from bottom */}
      <div style={{
        position: 'absolute',
        bottom: 0,
        left: 0,
        right: 0,
        height: 600,
        background: `linear-gradient(0deg, rgba(${r},${g},${b},0.12) 0%, transparent 100%)`,
      }} />

      {/* Top line */}
      <div style={{
        position: 'absolute', top: 0, left: 0, right: 0, height: 5,
        background: `linear-gradient(90deg, transparent, ${scene.accent_hex}, transparent)`,
        boxShadow: `0 2px 16px rgba(${r},${g},${b},0.6)`,
      }} />

      <ProgressDots currentScene={currentSceneIndex} totalScenes={totalScenes} accentColor={scene.accent_hex} />
      <SceneTypeBadge type={scene.type} accentColor={scene.accent_hex} localFrame={localFrame} fps={fps} />

      {/* Speech bubble */}
      <div style={{
        position: 'absolute',
        top: 210,
        left: 70,
        right: 70,
        display: 'flex',
        justifyContent: 'center',
        transform: `scale(${bubbleScale})`,
        opacity: bubbleOp,
        transformOrigin: 'bottom center',
      }}>
        <div style={{
          backgroundColor: '#ffffff',
          borderRadius: 28,
          padding: '36px 44px',
          maxWidth: 860,
          position: 'relative',
          boxShadow: `0 8px 40px rgba(0,0,0,0.4), 0 0 0 3px ${scene.accent_hex}`,
        }}>
          <div style={{
            fontFamily: 'system-ui, sans-serif',
            fontSize: 64,
            fontWeight: 900,
            lineHeight: 1.15,
            textAlign: 'center',
            color: '#111',
          }}>
            {scene.headline.toUpperCase().split(' ').map((word, i) => (
              <span key={i} style={{color: i % 2 === 1 ? scene.accent_hex : '#111'}}>
                {word}{i < scene.headline.split(' ').length - 1 ? ' ' : ''}
              </span>
            ))}
          </div>
          {/* Bubble tail pointing down toward character */}
          <div style={{
            position: 'absolute',
            bottom: -28,
            left: '50%',
            transform: 'translateX(-50%)',
            width: 0,
            height: 0,
            borderLeft: '20px solid transparent',
            borderRight: '20px solid transparent',
            borderTop: `28px solid ${scene.accent_hex}`,
          }} />
        </div>
      </div>

      {/* Character with lip sync */}
      <CharacterDisplay
        localFrame={localFrame}
        fps={fps}
        accentColor={scene.accent_hex}
        lipSyncCues={scene.lipSync}
        characterId={characterId}
      />

      {/* Subtext */}
      <div style={{
        position: 'absolute',
        top: 1490,
        left: 80,
        right: 80,
        textAlign: 'center',
        fontFamily: 'system-ui, sans-serif',
        fontSize: 38,
        color: 'rgba(210,210,210,0.9)',
        lineHeight: 1.5,
        opacity: subtextOp,
        transform: `translateY(${subtextY}px)`,
      }}>
        {scene.subtext}
      </div>

      <ProgressBar progress={globalProgress} accentColor={scene.accent_hex} />
    </>
  );
};
