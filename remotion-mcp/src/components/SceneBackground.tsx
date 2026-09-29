import React from 'react';
import {hexToRgb, darkenHex} from '../utils/colors';
import {FloatingOrbs} from '../assets/FloatingOrbs';
import {DotGrid} from '../assets/DotGrid';

interface SceneBackgroundProps {
  accentHex: string;
}

export const SceneBackground: React.FC<SceneBackgroundProps> = ({accentHex}) => {
  const {r, g, b} = hexToRgb(accentHex);
  const baseTint = darkenHex(accentHex, 0.92);

  return (
    <div
      style={{
        position: 'absolute',
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        backgroundColor: baseTint,
      }}
    >
      <DotGrid />
      <FloatingOrbs accentColor={accentHex} />

      <div
        style={{
          position: 'absolute',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          background: `radial-gradient(ellipse 85% 65% at 50% 42%, rgba(${r},${g},${b},0.2) 0%, transparent 65%)`,
        }}
      />

      <div
        style={{
          position: 'absolute',
          top: 0,
          left: 0,
          right: 0,
          height: 6,
          background: `linear-gradient(90deg, transparent 0%, ${accentHex} 25%, ${accentHex} 75%, transparent 100%)`,
          boxShadow: `0 2px 20px 2px rgba(${r},${g},${b},0.7)`,
        }}
      />

      <div
        style={{
          position: 'absolute',
          bottom: 0,
          left: 0,
          right: 0,
          height: 6,
          background: `linear-gradient(90deg, transparent 0%, ${accentHex} 25%, ${accentHex} 75%, transparent 100%)`,
          boxShadow: `0 -2px 20px 2px rgba(${r},${g},${b},0.7)`,
        }}
      />
    </div>
  );
};
