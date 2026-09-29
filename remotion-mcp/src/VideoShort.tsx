import React from 'react';
import {AbsoluteFill, Sequence, useCurrentFrame} from 'remotion';
import {VideoProps} from './types';
import {Scene} from './Scene';

export const VideoShort: React.FC<VideoProps> = ({
  scenes,
  totalDurationFrames,
  style = 'minimal',
  characterId,
}) => {
  const frame = useCurrentFrame();

  if (!scenes || scenes.length === 0) {
    return <AbsoluteFill style={{backgroundColor: '#0a0a0a'}} />;
  }

  const startFrames: number[] = [];
  let cumulative = 0;
  for (const scene of scenes) {
    startFrames.push(cumulative);
    cumulative += scene.durationFrames;
  }

  const globalProgress = totalDurationFrames > 0 ? frame / totalDurationFrames : 0;

  return (
    <AbsoluteFill style={{backgroundColor: '#0a0a0a'}}>
      {scenes.map((scene, i) => (
        <Sequence
          key={scene.id}
          from={startFrames[i]}
          durationInFrames={scene.durationFrames}
        >
          <Scene
            scene={scene}
            startFrame={0}
            globalProgress={globalProgress}
            currentSceneIndex={i}
            totalScenes={scenes.length}
            style={style}
            characterId={characterId}
          />
        </Sequence>
      ))}
    </AbsoluteFill>
  );
};
