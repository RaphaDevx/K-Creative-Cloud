import React from 'react';
import {Composition} from 'remotion';
import {VideoShort} from './VideoShort';
import {VideoProps} from './types';

export const RemotionRoot: React.FC = () => {
  return (
    <Composition
      id="VideoShort"
      component={VideoShort}
      durationInFrames={3000}
      fps={30}
      width={1080}
      height={1920}
      defaultProps={{
        scenes: [],
        title: '',
        totalDurationFrames: 3000,
      } as VideoProps}
    />
  );
};
