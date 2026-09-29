import React from 'react';
import {useCurrentFrame, useVideoConfig, spring, interpolate} from 'remotion';
import {SceneData} from '../types';
import {SceneBackground} from '../components/SceneBackground';
import {ProgressDots} from '../components/ProgressDots';
import {ProgressBar} from '../components/ProgressBar';
import {EmojiDisplay} from '../components/EmojiDisplay';
import {HeadlineText} from '../components/HeadlineText';
import {SubtextDisplay} from '../components/SubtextDisplay';
import {SceneTypeBadge} from '../assets/SceneTypeBadge';
import {MathVizRenderer} from '../viz/MathVizRenderer';
import {hexToRgb} from '../utils/colors';

interface SceneMinimalProps {
  scene: SceneData;
  startFrame: number;
  globalProgress: number;
  currentSceneIndex: number;
  totalScenes: number;
}

export const SceneMinimal: React.FC<SceneMinimalProps> = ({
  scene,
  startFrame,
  globalProgress,
  currentSceneIndex,
  totalScenes,
}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const localFrame = frame - startFrame;

  if (scene.viz) {
    return (
      <SceneMinimalMath
        scene={scene}
        localFrame={localFrame}
        globalProgress={globalProgress}
        currentSceneIndex={currentSceneIndex}
        totalScenes={totalScenes}
        fps={fps}
      />
    );
  }

  return (
    <>
      <SceneBackground accentHex={scene.accent_hex} />
      <ProgressDots currentScene={currentSceneIndex} totalScenes={totalScenes} accentColor={scene.accent_hex} />
      <SceneTypeBadge type={scene.type} accentColor={scene.accent_hex} localFrame={localFrame} fps={fps} />
      <EmojiDisplay emoji={scene.emoji} accentColor={scene.accent_hex} localFrame={Math.max(0, localFrame - 3)} fps={fps} />
      <HeadlineText text={scene.headline} accentColor={scene.accent_hex} localFrame={Math.max(0, localFrame - 6)} fps={fps} />
      <SubtextDisplay text={scene.subtext} accentColor={scene.accent_hex} localFrame={Math.max(0, localFrame - 12)} fps={fps} />
      <ProgressBar progress={globalProgress} accentColor={scene.accent_hex} />
    </>
  );
};

// Math layout: compact headline → viz → subtext (no emoji)
interface MathProps {
  scene: SceneData;
  localFrame: number;
  globalProgress: number;
  currentSceneIndex: number;
  totalScenes: number;
  fps: number;
}

const SceneMinimalMath: React.FC<MathProps> = ({
  scene,
  localFrame,
  globalProgress,
  currentSceneIndex,
  totalScenes,
  fps,
}) => {
  const {r, g, b} = hexToRgb(scene.accent_hex);

  // Compact headline animation
  const headlineY = spring({
    frame: Math.max(0, localFrame - 6),
    fps,
    config: {damping: 12, stiffness: 120},
    from: 50,
    to: 0,
  });
  const headlineOpacity = interpolate(Math.max(0, localFrame - 6), [0, 8], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });

  // Viz container fade-in
  const vizOpacity = interpolate(localFrame, [0, 6], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });

  // Subtext animation
  const subtextY = spring({
    frame: Math.max(0, localFrame - 14),
    fps,
    config: {damping: 14, stiffness: 100},
    from: 30,
    to: 0,
  });
  const subtextOpacity = interpolate(Math.max(0, localFrame - 14), [0, 10], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });

  const words = scene.headline.toUpperCase().split(' ');

  return (
    <>
      <SceneBackground accentHex={scene.accent_hex} />
      <ProgressDots currentScene={currentSceneIndex} totalScenes={totalScenes} accentColor={scene.accent_hex} />
      <SceneTypeBadge type={scene.type} accentColor={scene.accent_hex} localFrame={localFrame} fps={fps} />

      {/* Compact headline — higher up, smaller font */}
      <div
        style={{
          position: 'absolute',
          top: 370,
          left: 90,
          right: 90,
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'center',
          transform: `translateY(${headlineY}px)`,
          opacity: headlineOpacity,
        }}
      >
        <div
          style={{
            maxWidth: 900,
            textAlign: 'center',
            fontFamily: 'system-ui, -apple-system, sans-serif',
            fontSize: 70,
            fontWeight: '900',
            lineHeight: 1.15,
            letterSpacing: 1,
            wordWrap: 'break-word',
          }}
        >
          {words.map((word, i) => (
            <span
              key={i}
              style={{
                color: i % 2 === 1 ? scene.accent_hex : '#ffffff',
                textShadow:
                  i % 2 === 1
                    ? `0 0 30px rgba(${r},${g},${b},0.7), 3px 3px 0px rgba(0,0,0,0.65)`
                    : '3px 3px 0px rgba(0,0,0,0.65)',
              }}
            >
              {word}
              {i < words.length - 1 ? ' ' : ''}
            </span>
          ))}
        </div>
      </div>

      {/* Math Viz — centered in screen */}
      <div
        style={{
          position: 'absolute',
          top: 630,
          left: 90,
          right: 90,
          display: 'flex',
          justifyContent: 'center',
          opacity: vizOpacity,
        }}
      >
        <MathVizRenderer
          viz={scene.viz!}
          accentHex={scene.accent_hex}
          localFrame={localFrame}
          fps={fps}
        />
      </div>

      {/* Subtext — below viz */}
      <div
        style={{
          position: 'absolute',
          top: 1190,
          left: 90,
          right: 90,
          display: 'flex',
          justifyContent: 'center',
          transform: `translateY(${subtextY}px)`,
          opacity: subtextOpacity,
        }}
      >
        <div
          style={{
            maxWidth: 860,
            textAlign: 'center',
            fontFamily: 'system-ui, -apple-system, sans-serif',
            fontSize: 36,
            fontWeight: 400,
            color: 'rgba(240,240,240,0.95)',
            lineHeight: 1.5,
            wordWrap: 'break-word',
            backgroundColor: `rgba(${r},${g},${b},0.13)`,
            border: `1px solid rgba(${r},${g},${b},0.28)`,
            borderRadius: 20,
            paddingTop: 22,
            paddingBottom: 22,
            paddingLeft: 36,
            paddingRight: 36,
          }}
        >
          {scene.subtext}
        </div>
      </div>

      <ProgressBar progress={globalProgress} accentColor={scene.accent_hex} />
    </>
  );
};
