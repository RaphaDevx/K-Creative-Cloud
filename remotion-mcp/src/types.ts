export type ReelStyle = 'minimal' | '2D' | 'kinetic' | '3D';

export interface LipSyncCue {
  start: number;   // seconds from scene audio start
  phoneme: string; // A | B | C | D | E | F
}

export type VizType = 'normal_dist' | 'skewed_dist' | 'histogram' | 'bar_chart' | 'latex';

export interface VizMarker {
  label: string;  // e.g. "Mittelwert", "Median", "Mode"
  value: number;  // 0–1 relative x position on the plot
  color?: string; // optional hex override
}

export interface VizData {
  type: VizType;
  skew?: 'left' | 'right';  // skewed_dist only
  markers?: VizMarker[];
  data?: number[];           // histogram/bar_chart: bar heights 0–1 normalized
  labels?: string[];         // x-axis labels for histogram/bar_chart
  caption?: string;          // optional note below viz
  latex?: string;            // latex only: KaTeX formula string
}

export interface SceneData {
  id: number;
  type: 'hook' | 'fact' | 'explanation' | 'warning' | 'tip' | 'takeaway';
  headline: string;
  subtext: string;
  emoji: string;
  spoken: string;
  accent_hex: string;
  audioFile: string;
  durationFrames: number;
  lipSync?: LipSyncCue[];
  viz?: VizData;
}

export interface VideoProps {
  scenes: SceneData[];
  title: string;
  totalDurationFrames: number;
  style?: ReelStyle;
  characterId?: string;
}
