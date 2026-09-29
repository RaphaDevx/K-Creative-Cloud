import React, {useMemo} from 'react';
import katex from 'katex';
import {VizData} from '../types';
import {hexToRgb} from '../utils/colors';

interface LatexVizProps {
  viz: VizData;
  accentHex: string;
  localFrame: number;
  fps: number;
}

export const LatexViz: React.FC<LatexVizProps> = ({viz, accentHex}) => {
  const {r, g, b} = hexToRgb(accentHex);

  const renderedHtml = useMemo(() => {
    try {
      return katex.renderToString(viz.latex ?? '', {
        throwOnError: false,
        displayMode: true,
        output: 'html',
      });
    } catch {
      return `<span style="color:#ff4444;">LaTeX Error</span>`;
    }
  }, [viz.latex]);

  return (
    <div
      style={{
        width: 900,
        minHeight: 200,
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        gap: 28,
      }}
    >
      <div
        style={{
          width: '100%',
          backgroundColor: `rgba(${r},${g},${b},0.12)`,
          border: `2px solid rgba(${r},${g},${b},0.45)`,
          borderRadius: 24,
          paddingTop: 40,
          paddingBottom: 40,
          paddingLeft: 48,
          paddingRight: 48,
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'center',
        }}
      >
        <div
          dangerouslySetInnerHTML={{__html: renderedHtml}}
          style={{
            color: '#ffffff',
            fontSize: 52,
            lineHeight: 1.6,
            textAlign: 'center',
          }}
        />
      </div>

      {viz.caption ? (
        <div
          style={{
            fontFamily: 'system-ui, -apple-system, sans-serif',
            fontSize: 30,
            fontWeight: 400,
            color: `rgba(${r},${g},${b},0.95)`,
            textAlign: 'center',
            letterSpacing: 0.5,
          }}
        >
          {viz.caption}
        </div>
      ) : null}
    </div>
  );
};
