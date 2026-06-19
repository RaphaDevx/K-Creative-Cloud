import React from 'react';
import {spring} from 'remotion';
import {LipSyncCue} from '../../types';
import {PeepBody, MOUTH_SLOT} from './PeepBody';
import {getMouthShape} from './MouthShapes';

interface CharacterDisplayProps {
  localFrame: number;
  fps: number;
  accentColor: string;
  lipSyncCues?: LipSyncCue[];
  characterId?: string;
}

function useCurrentPhoneme(localFrame: number, fps: number, cues: LipSyncCue[]): string {
  if (!cues || cues.length === 0) return 'A';
  const t = localFrame / fps;
  let phoneme = 'A';
  for (const cue of cues) {
    if (cue.start <= t) phoneme = cue.phoneme;
    else break;
  }
  return phoneme;
}

const CHARACTER_VARIANTS: Record<string, {skinColor: string; hairColor: string; shirtColor: string}> = {
  default:  {skinColor: '#F5C5A3', hairColor: '#3D2314', shirtColor: '#4A4A6A'},
  dark:     {skinColor: '#8D5524', hairColor: '#1a1a1a', shirtColor: '#2D5A3D'},
  light:    {skinColor: '#FDDBB4', hairColor: '#C4962A', shirtColor: '#6A4A8A'},
  cool:     {skinColor: '#F0C8A0', hairColor: '#1C4E80', shirtColor: '#1C4E80'},
};

export const CharacterDisplay: React.FC<CharacterDisplayProps> = ({
  localFrame,
  fps,
  accentColor,
  lipSyncCues = [],
  characterId = 'default',
}) => {
  const bodyW = 320;
  const bodyH = 460;

  const enterScale = spring({frame: localFrame, fps, config: {damping: 10, stiffness: 120}, from: 0.6, to: 1});
  const enterY = spring({frame: localFrame, fps, config: {damping: 10, stiffness: 120}, from: 80, to: 0});
  const opacity = Math.min(1, localFrame / 8);

  const phoneme = useCurrentPhoneme(localFrame, fps, lipSyncCues);
  const MouthShape = getMouthShape(phoneme);
  const variant = CHARACTER_VARIANTS[characterId] ?? CHARACTER_VARIANTS.default;

  // Mouth position in rendered coordinates
  const mouthX = (MOUTH_SLOT.x / 320) * bodyW - MOUTH_SLOT.width / 2;
  const mouthY = (MOUTH_SLOT.y / 460) * bodyH - MOUTH_SLOT.height / 2;

  return (
    <div style={{
      position: 'absolute',
      top: 860,
      left: 0,
      right: 0,
      display: 'flex',
      justifyContent: 'center',
      opacity,
      transform: `scale(${enterScale}) translateY(${enterY}px)`,
      transformOrigin: 'center top',
    }}>
      <div style={{position: 'relative', width: bodyW, height: bodyH}}>
        <PeepBody
          skinColor={variant.skinColor}
          hairColor={variant.hairColor}
          shirtColor={variant.shirtColor}
          width={bodyW}
          height={bodyH}
        />
        {/* Lip sync mouth overlay */}
        <div style={{
          position: 'absolute',
          left: mouthX,
          top: mouthY,
          width: MOUTH_SLOT.width,
          height: MOUTH_SLOT.height,
          pointerEvents: 'none',
        }}>
          <MouthShape skinColor={variant.skinColor} width={MOUTH_SLOT.width} height={MOUTH_SLOT.height} />
        </div>
      </div>
    </div>
  );
};
