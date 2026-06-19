import {ReelStyle} from '../types';

export interface StyleConfig {
  name: ReelStyle;
  label: string;
  description: string;
  hasCharacter: boolean;
  usesLipSync: boolean;
}

export const STYLE_REGISTRY: Record<ReelStyle, StyleConfig> = {
  minimal: {
    name: 'minimal',
    label: 'Minimal',
    description: 'Dark background, emoji, spring animations (default)',
    hasCharacter: false,
    usesLipSync: false,
  },
  '2D': {
    name: '2D',
    label: '2D Cartoon',
    description: 'Animated cartoon character with Rhubarb lip sync',
    hasCharacter: true,
    usesLipSync: true,
  },
  kinetic: {
    name: 'kinetic',
    label: 'Kinetic Text',
    description: 'Bold word-by-word typography, no character',
    hasCharacter: false,
    usesLipSync: false,
  },
  '3D': {
    name: '3D',
    label: '3D Cards',
    description: 'CSS perspective depth, floating card layout',
    hasCharacter: false,
    usesLipSync: false,
  },
};
