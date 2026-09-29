import React from 'react';

interface MouthShapeProps {
  skinColor?: string;
  accentColor?: string;
  width?: number;
  height?: number;
}

// A: rest / silence — thin closed line
export const MouthA: React.FC<MouthShapeProps> = ({skinColor = '#F5C5A3', accentColor = '#c0392b', width = 120, height = 50}) => (
  <svg viewBox="0 0 120 50" width={width} height={height}>
    <ellipse cx="60" cy="26" rx="32" ry="5" fill="#222" />
    <ellipse cx="60" cy="24" rx="30" ry="3" fill={skinColor} />
    <ellipse cx="60" cy="26" rx="28" ry="2" fill="#333" />
  </svg>
);

// B: /p/ /b/ /m/ — pressed closed, slight puff
export const MouthB: React.FC<MouthShapeProps> = ({skinColor = '#F5C5A3', accentColor = '#c0392b', width = 120, height = 50}) => (
  <svg viewBox="0 0 120 50" width={width} height={height}>
    <ellipse cx="60" cy="25" rx="34" ry="7" fill="#c0392b" />
    <ellipse cx="60" cy="22" rx="32" ry="6" fill={skinColor} />
    <path d="M26,25 Q60,20 94,25" stroke="#a33" strokeWidth="2" fill="none" />
    <path d="M26,25 Q60,30 94,25" stroke="#a33" strokeWidth="2" fill="none" />
  </svg>
);

// C: /k/ /t/ /d/ — slightly open, small gap
export const MouthC: React.FC<MouthShapeProps> = ({skinColor = '#F5C5A3', accentColor = '#c0392b', width = 120, height = 50}) => (
  <svg viewBox="0 0 120 50" width={width} height={height}>
    <ellipse cx="60" cy="25" rx="30" ry="12" fill="#1a0a0a" />
    <ellipse cx="60" cy="18" rx="28" ry="8" fill={skinColor} />
    <rect x="32" y="20" width="56" height="5" rx="2" fill="white" opacity="0.9" />
    <rect x="32" y="30" width="56" height="4" rx="2" fill="white" opacity="0.7" />
  </svg>
);

// D: /th/ — slightly open with tongue tip visible
export const MouthD: React.FC<MouthShapeProps> = ({skinColor = '#F5C5A3', accentColor = '#c0392b', width = 120, height = 50}) => (
  <svg viewBox="0 0 120 50" width={width} height={height}>
    <ellipse cx="60" cy="25" rx="30" ry="14" fill="#1a0a0a" />
    <ellipse cx="60" cy="17" rx="28" ry="8" fill={skinColor} />
    <rect x="34" y="19" width="52" height="5" rx="2" fill="white" opacity="0.9" />
    {/* tongue tip */}
    <ellipse cx="60" cy="30" rx="14" ry="6" fill="#e07070" />
  </svg>
);

// E: /f/ /v/ — lower lip under upper teeth
export const MouthE: React.FC<MouthShapeProps> = ({skinColor = '#F5C5A3', accentColor = '#c0392b', width = 120, height = 50}) => (
  <svg viewBox="0 0 120 50" width={width} height={height}>
    <ellipse cx="60" cy="24" rx="32" ry="14" fill="#1a0a0a" />
    <ellipse cx="60" cy="16" rx="30" ry="8" fill={skinColor} />
    <rect x="32" y="17" width="56" height="6" rx="3" fill="white" opacity="0.95" />
    {/* lower lip raised */}
    <ellipse cx="60" cy="30" rx="28" ry="7" fill={skinColor} />
    <path d="M36,29 Q60,35 84,29" fill={skinColor} />
  </svg>
);

// F: /L/ /n/ — open smile, teeth and tongue visible
export const MouthF: React.FC<MouthShapeProps> = ({skinColor = '#F5C5A3', accentColor = '#c0392b', width = 120, height = 50}) => (
  <svg viewBox="0 0 120 50" width={width} height={height}>
    <path d="M28,20 Q60,50 92,20 Q92,14 60,14 Q28,14 28,20" fill="#1a0a0a" />
    <rect x="34" y="17" width="52" height="6" rx="3" fill="white" opacity="0.95" />
    <ellipse cx="60" cy="35" rx="22" ry="8" fill="#e07070" />
    <rect x="34" y="32" width="52" height="5" rx="3" fill="white" opacity="0.8" />
  </svg>
);

export const MOUTH_SHAPES: Record<string, React.FC<MouthShapeProps>> = {
  A: MouthA,
  B: MouthB,
  C: MouthC,
  D: MouthD,
  E: MouthE,
  F: MouthF,
  X: MouthF, // fallback wide-open
  G: MouthC, // fallback
  H: MouthC, // fallback
};

export function getMouthShape(phoneme: string): React.FC<MouthShapeProps> {
  return MOUTH_SHAPES[phoneme?.toUpperCase()] ?? MouthA;
}
