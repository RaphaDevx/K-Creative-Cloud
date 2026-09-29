import React from 'react';
import {AbsoluteFill, Audio, staticFile} from 'remotion';
import {SceneData, ReelStyle} from './types';
import {SceneMinimal} from './styles/SceneMinimal';
import {Scene2D} from './styles/Scene2D';
import {SceneKinetic} from './styles/SceneKinetic';
import {Scene3D} from './styles/Scene3D';

interface SceneProps {
  scene: SceneData;
  startFrame: number;
  globalProgress: number;
  currentSceneIndex: number;
  totalScenes: number;
  style?: ReelStyle;
  characterId?: string;
}

export const Scene: React.FC<SceneProps> = ({
  scene,
  startFrame,
  globalProgress,
  currentSceneIndex,
  totalScenes,
  style = 'minimal',
  characterId,
}) => {
  const commonProps = {scene, startFrame, globalProgress, currentSceneIndex, totalScenes};

  const layout = (() => {
    switch (style) {
      case '2D':      return <Scene2D {...commonProps} characterId={characterId} />;
      case 'kinetic': return <SceneKinetic {...commonProps} />;
      case '3D':      return <Scene3D {...commonProps} />;
      default:        return <SceneMinimal {...commonProps} />;
    }
  })();

  return (
    <AbsoluteFill>
      {layout}
      {scene.audioFile ? (
        <Audio src={staticFile('audio/' + scene.audioFile)} />
      ) : null}
    </AbsoluteFill>
  );
};
