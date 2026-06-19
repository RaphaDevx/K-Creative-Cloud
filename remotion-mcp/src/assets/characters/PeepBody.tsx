import React from 'react';

interface PeepBodyProps {
  skinColor?: string;
  hairColor?: string;
  shirtColor?: string;
  width?: number;
  height?: number;
}

// Mouth is at approximately (160, 195) in 320×460 viewBox
export const MOUTH_SLOT = {x: 160, y: 195, width: 120, height: 50};

export const PeepBody: React.FC<PeepBodyProps> = ({
  skinColor = '#F5C5A3',
  hairColor = '#3D2314',
  shirtColor = '#4A4A6A',
  width = 320,
  height = 460,
}) => (
  <svg viewBox="0 0 320 460" width={width} height={height}>
    {/* Neck */}
    <rect x="135" y="290" width="50" height="60" rx="8" fill={skinColor} />

    {/* Shoulders / body */}
    <ellipse cx="160" cy="410" rx="140" ry="80" fill={shirtColor} />
    <rect x="20" y="370" width="280" height="90" fill={shirtColor} />

    {/* Shirt collar */}
    <path d="M120,310 L160,360 L200,310" fill="white" opacity="0.3" />

    {/* Head */}
    <ellipse cx="160" cy="180" rx="100" ry="110" fill={skinColor} />

    {/* Hair */}
    <ellipse cx="160" cy="82" rx="105" ry="55" fill={hairColor} />
    <ellipse cx="62" cy="155" rx="22" ry="45" fill={hairColor} />
    <ellipse cx="258" cy="155" rx="22" ry="45" fill={hairColor} />

    {/* Ears */}
    <ellipse cx="62" cy="190" rx="14" ry="18" fill={skinColor} />
    <ellipse cx="258" cy="190" rx="14" ry="18" fill={skinColor} />

    {/* Eyes */}
    <ellipse cx="122" cy="168" rx="18" ry="20" fill="white" />
    <ellipse cx="198" cy="168" rx="18" ry="20" fill="white" />
    <ellipse cx="126" cy="170" rx="10" ry="12" fill="#1a1a1a" />
    <ellipse cx="202" cy="170" rx="10" ry="12" fill="#1a1a1a" />
    {/* Eye shine */}
    <circle cx="130" cy="165" r="3" fill="white" />
    <circle cx="206" cy="165" r="3" fill="white" />

    {/* Eyebrows */}
    <path d="M106,148 Q122,140 138,145" stroke={hairColor} strokeWidth="5" strokeLinecap="round" fill="none" />
    <path d="M182,145 Q198,140 214,148" stroke={hairColor} strokeWidth="5" strokeLinecap="round" fill="none" />

    {/* Nose */}
    <ellipse cx="160" cy="192" rx="7" ry="5" fill="rgba(0,0,0,0.12)" />

    {/* Mouth placeholder area — MouthShape is overlaid here by CharacterDisplay */}
  </svg>
);
