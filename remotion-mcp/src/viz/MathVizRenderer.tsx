import React from 'react';
import {VizData} from '../types';
import {DistributionCurve} from './DistributionCurve';
import {HistogramViz} from './HistogramViz';
import {BarChartViz} from './BarChartViz';
import {LatexViz} from './LatexViz';

interface MathVizRendererProps {
  viz: VizData;
  accentHex: string;
  localFrame: number;
  fps: number;
}

export const MathVizRenderer: React.FC<MathVizRendererProps> = (props) => {
  switch (props.viz.type) {
    case 'normal_dist':
    case 'skewed_dist':
      return <DistributionCurve {...props} />;
    case 'histogram':
      return <HistogramViz {...props} />;
    case 'bar_chart':
      return <BarChartViz {...props} />;
    case 'latex':
      return <LatexViz {...props} />;
    default:
      return null;
  }
};
