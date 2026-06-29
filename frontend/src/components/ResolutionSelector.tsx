import React from 'react';
import type { FormatInfo } from '../hooks/useApi';

interface ResolutionSelectorProps {
  formats: FormatInfo[];
  heights: number[];
  onSelect: (height: number) => void;
  isLoading: boolean;
  onBack: () => void;
}

const ResolutionSelector: React.FC<ResolutionSelectorProps> = ({
  formats,
  heights,
  onSelect,
  isLoading,
  onBack,
}) => {
  const getLabel = (height: number) => {
    if (height >= 2160) return '4K';
    if (height >= 1440) return '1440p';
    if (height >= 1080) return '1080p';
    if (height >= 720) return '720p';
    if (height >= 480) return '480p';
    if (height >= 360) return '360p';
    if (height >= 240) return '240p';
    return `${height}p`;
  };

  const getQualityBadge = (height: number) => {
    if (height >= 1080) return 'HD';
    if (height >= 720) return 'HD';
    return 'SD';
  };

  return (
    <div className="animate-slide-up w-full">
      <div className="mb-6 text-center">
        <div className="flex justify-center mb-3">
          <img
            src="/logo-sm.png"
            alt="Siphon"
            className="h-10 w-10 object-contain opacity-80"
            draggable={false}
          />
        </div>
        <h2 className="text-xl font-semibold text-white mb-1">Choose Resolution</h2>
        <p className="text-sm text-slate-400">
          {formats.length} format{formats.length !== 1 ? 's' : ''} found
        </p>
      </div>

      <div className="grid grid-cols-2 gap-3 mb-4">
        {heights.map((height) => (
          <button
            key={height}
            onClick={() => onSelect(height)}
            disabled={isLoading}
            className="relative rounded-2xl bg-dark-surface border border-dark-border p-4 text-left hover:border-siphon-500 active:bg-siphon-950 transition-all disabled:opacity-50"
          >
            <div className="flex items-center justify-between">
              <span className="text-lg font-bold text-white">{getLabel(height)}</span>
              <span className="text-[10px] font-medium uppercase tracking-wider rounded-full bg-siphon-900 text-siphon-300 px-2 py-0.5">
                {getQualityBadge(height)}
              </span>
            </div>
            <div className="mt-1 text-xs text-slate-500">{height} pixels</div>
          </button>
        ))}
      </div>

      <button
        onClick={onBack}
        disabled={isLoading}
        className="w-full rounded-2xl border border-dark-border bg-transparent hover:bg-dark-surface text-slate-300 font-medium py-3.5 text-sm transition-colors"
      >
        Back
      </button>
    </div>
  );
};

export default ResolutionSelector;
