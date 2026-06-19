import React from 'react';
import {useCurrentFrame, useVideoConfig, spring, interpolate} from 'remotion';
import {SceneData} from '../types';
import {ProgressBar} from '../components/ProgressBar';
import {ProgressDots} from '../components/ProgressDots';

interface Scene3DProps {
  scene: SceneData;
  startFrame: number;
  globalProgress: number;
  currentSceneIndex: number;
  totalScenes: number;
}

export const Scene3D: React.FC<Scene3DProps> = ({
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

  // Card entrance animations
  const cardRotX = spring({frame: localFrame, fps, config: {damping: 14, stiffness: 80}, from: 25, to: 0});
  const cardTY = spring({frame: localFrame, fps, config: {damping: 14, stiffness: 80}, from: -120, to: 0});
  const cardOpacity = interpolate(localFrame, [0, 10], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});

  const subtextDelay = Math.max(0, localFrame - 14);
  const subtextRotX = spring({frame: subtextDelay, fps, config: {damping: 14, stiffness: 80}, from: -20, to: 0});
  const subtextTY = spring({frame: subtextDelay, fps, config: {damping: 14, stiffness: 80}, from: 80, to: 0});
  const subtextOp = interpolate(subtextDelay, [0, 10], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});

  // Floating depth orbs
  const t = localFrame / fps;
  const orb1X = Math.sin(t * 0.4) * 60;
  const orb1Y = Math.cos(t * 0.3) * 80;

  return (
    <>
      {/* Deep dark bg */}
      <div style={{position: 'absolute', inset: 0, background: `radial-gradient(ellipse 100% 80% at 50% 50%, rgba(${r},${g},${b},0.12) 0%, #050508 70%)`}} />

      {/* Grid lines (perspective) */}
      <div style={{
        position: 'absolute', inset: 0,
        backgroundImage: `linear-gradient(rgba(${r},${g},${b},0.06) 1px, transparent 1px), linear-gradient(90deg, rgba(${r},${g},${b},0.06) 1px, transparent 1px)`,
        backgroundSize: '80px 80px',
      }} />

      {/* Floating depth orb */}
      <div style={{
        position: 'absolute',
        left: '20%',
        top: '30%',
        width: 400,
        height: 400,
        borderRadius: '50%',
        background: `radial-gradient(circle, rgba(${r},${g},${b},0.12) 0%, transparent 70%)`,
        filter: 'blur(40px)',
        transform: `translate(${orb1X}px, ${orb1Y}px) translate(-50%,-50%)`,
      }} />

      {/* Scene type strip */}
      <div style={{
        position: 'absolute',
        top: 0,
        left: 0,
        right: 0,
        height: 90,
        background: `linear-gradient(180deg, rgba(${r},${g},${b},0.25) 0%, transparent 100%)`,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
      }}>
        <span style={{
          fontFamily: 'system-ui, sans-serif',
          fontSize: 26,
          fontWeight: 800,
          letterSpacing: 6,
          color: scene.accent_hex,
          textTransform: 'uppercase',
          textShadow: `0 0 20px ${scene.accent_hex}`,
        }}>
          {scene.type.toUpperCase()}
        </span>
      </div>

      {/* 3D Headline card */}
      <div style={{
        position: 'absolute',
        top: 560,
        left: 60,
        right: 60,
        perspective: 1000,
        opacity: cardOpacity,
      }}>
        <div style={{
          background: `linear-gradient(135deg, rgba(${r},${g},${b},0.2) 0%, rgba(${r},${g},${b},0.05) 100%)`,
          border: `1px solid rgba(${r},${g},${b},0.4)`,
          borderRadius: 24,
          padding: '48px 52px',
          transform: `rotateX(${cardRotX}deg) translateY(${cardTY}px)`,
          transformOrigin: 'center bottom',
          boxShadow: `0 30px 80px rgba(0,0,0,0.6), 0 0 40px rgba(${r},${g},${b},0.15), inset 0 1px 0 rgba(255,255,255,0.1)`,
        }}>
          <div style={{
            fontFamily: 'system-ui, sans-serif',
            fontSize: 82,
            fontWeight: 900,
            lineHeight: 1.15,
            textAlign: 'center',
            color: '#fff',
            textShadow: `3px 3px 0 rgba(0,0,0,0.6)`,
          }}>
            {scene.headline.toUpperCase().split(' ').map((word, i) => (
              <span key={i} style={{color: i % 2 === 1 ? scene.accent_hex : '#fff'}}>
                {word}{i < scene.headline.split(' ').length - 1 ? ' ' : ''}
              </span>
            ))}
          </div>
        </div>
      </div>

      {/* Emoji floating above card */}
      <div style={{
        position: 'absolute',
        top: 420,
        left: 0,
        right: 0,
        textAlign: 'center',
        fontSize: 110,
        fontFamily: '"Noto Color Emoji", "Apple Color Emoji", "Segoe UI Emoji", system-ui',
        filter: `drop-shadow(0 0 20px rgba(${r},${g},${b},0.6))`,
        opacity: cardOpacity,
        transform: `translateY(${cardTY * 0.5}px)`,
      }}>
        {scene.emoji}
      </div>

      {/* Subtext 3D card */}
      <div style={{
        position: 'absolute',
        top: 1150,
        left: 60,
        right: 60,
        perspective: 800,
        opacity: subtextOp,
      }}>
        <div style={{
          background: `rgba(${r},${g},${b},0.08)`,
          border: `1px solid rgba(${r},${g},${b},0.2)`,
          borderRadius: 16,
          padding: '24px 36px',
          transform: `rotateX(${subtextRotX}deg) translateY(${subtextTY}px)`,
          transformOrigin: 'center top',
        }}>
          <div style={{
            fontFamily: 'system-ui, sans-serif',
            fontSize: 38,
            color: 'rgba(230,230,230,0.9)',
            lineHeight: 1.5,
            textAlign: 'center',
          }}>
            {scene.subtext}
          </div>
        </div>
      </div>

      <ProgressDots currentScene={currentSceneIndex} totalScenes={totalScenes} accentColor={scene.accent_hex} />
      <ProgressBar progress={globalProgress} accentColor={scene.accent_hex} />
    </>
  );
};
