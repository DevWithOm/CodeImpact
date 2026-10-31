import React from 'react';
import {
  Search,
  X,
  Filter,
  AlertTriangle,
  Flame,
  Layers,
  ZoomIn,
  ZoomOut,
  Maximize2,
  RotateCcw,
  Sparkles
} from 'lucide-react';

interface GraphToolbarProps {
  searchQuery: string;
  onSearchChange: (q: string) => void;
  selectedFilter: string;
  onFilterChange: (filter: string) => void;
  highlightCyclesOnly: boolean;
  onToggleHighlightCycles: () => void;
  onZoomIn: () => void;
  onZoomOut: () => void;
  onFitView: () => void;
  onResetSelection: () => void;
  matchingCount: number;
  totalCount: number;
  cycleCount: number;
}

export const GraphToolbar: React.FC<GraphToolbarProps> = ({
  searchQuery,
  onSearchChange,
  selectedFilter,
  onFilterChange,
  highlightCyclesOnly,
  onToggleHighlightCycles,
  onZoomIn,
  onZoomOut,
  onFitView,
  onResetSelection,
  matchingCount,
  totalCount,
  cycleCount
}) => {
  const filterOptions = [
    { id: 'all', label: 'All Modules' },
    { id: 'cycle', label: 'Circular Cycles', icon: AlertTriangle, count: cycleCount, badgeColor: 'bg-red-500' },
    { id: 'hotspot', label: 'Hotspots', icon: Flame },
    { id: 'unused', label: 'Potentially Unused', icon: Layers },
    { id: 'entry', label: 'Entrypoints' }
  ];

  return (
    <div className="p-4 rounded-2xl bg-white border border-slate-200/90 shadow-sm space-y-3">
      {/* Top Row: Search and Viewport Controls */}
      <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3">
        {/* Search Bar */}
        <div className="relative flex-1 max-w-md">
          <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => onSearchChange(e.target.value)}
            placeholder="Search module by file name or path (e.g. sessionProvider)..."
            className="w-full pl-9 pr-8 py-2 rounded-xl bg-slate-50 border border-slate-200 text-xs font-mono font-medium text-slate-800 placeholder-slate-400 focus:outline-none focus:border-[#FF2E55] focus:ring-1 focus:ring-[#FF2E55] transition-all"
          />
          {searchQuery && (
            <button
              onClick={() => onSearchChange('')}
              className="absolute right-2.5 top-1/2 -translate-y-1/2 p-0.5 text-slate-400 hover:text-slate-600 rounded"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          )}
        </div>

        {/* View Controls: Zoom, Fit, Reset */}
        <div className="flex items-center gap-1.5 shrink-0 self-end sm:self-center">
          <button
            onClick={onToggleHighlightCycles}
            className={`px-3 py-1.5 rounded-xl text-xs font-extrabold flex items-center gap-1.5 transition-all border ${
              highlightCyclesOnly
                ? 'bg-red-50 text-[#FF2E55] border-red-300 ring-2 ring-red-400/20'
                : 'bg-slate-50 text-slate-600 border-slate-200 hover:bg-slate-100'
            }`}
            title="Highlight only circular dependency nodes and edges"
          >
            <AlertTriangle className={`w-3.5 h-3.5 ${highlightCyclesOnly ? 'text-[#FF2E55]' : 'text-slate-500'}`} />
            <span className="hidden md:inline">Cycles Mode</span>
          </button>

          <div className="h-5 w-px bg-slate-200 mx-1" />

          <button
            onClick={onZoomIn}
            className="p-2 rounded-xl bg-slate-50 hover:bg-slate-100 text-slate-600 border border-slate-200 transition-colors"
            title="Zoom in"
          >
            <ZoomIn className="w-4 h-4" />
          </button>

          <button
            onClick={onZoomOut}
            className="p-2 rounded-xl bg-slate-50 hover:bg-slate-100 text-slate-600 border border-slate-200 transition-colors"
            title="Zoom out"
          >
            <ZoomOut className="w-4 h-4" />
          </button>

          <button
            onClick={onFitView}
            className="p-2 rounded-xl bg-slate-50 hover:bg-slate-100 text-slate-600 border border-slate-200 transition-colors"
            title="Fit graph to view"
          >
            <Maximize2 className="w-4 h-4" />
          </button>

          <button
            onClick={onResetSelection}
            className="p-2 rounded-xl bg-slate-50 hover:bg-slate-100 text-slate-600 border border-slate-200 transition-colors"
            title="Reset selection"
          >
            <RotateCcw className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Bottom Row: Filter Chips and Search Count */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pt-2 border-t border-slate-100 text-xs">
        <div className="flex items-center gap-1.5 flex-wrap">
          <Filter className="w-3.5 h-3.5 text-slate-400 mr-1 shrink-0" />
          {filterOptions.map((opt) => {
            const isSelected = selectedFilter === opt.id;
            const Icon = opt.icon;
            return (
              <button
                key={opt.id}
                onClick={() => onFilterChange(opt.id)}
                className={`px-2.5 py-1 rounded-xl text-xs font-bold transition-all flex items-center gap-1.5 ${
                  isSelected
                    ? 'bg-slate-900 text-white shadow-xs'
                    : 'bg-slate-100/80 text-slate-600 hover:bg-slate-200/80'
                }`}
              >
                {Icon && <Icon className="w-3 h-3 text-[#FF2E55]" />}
                <span>{opt.label}</span>
                {opt.count !== undefined && opt.count > 0 && (
                  <span className={`px-1.5 py-0.2 rounded-full text-[10px] text-white font-mono ${opt.badgeColor || 'bg-slate-700'}`}>
                    {opt.count}
                  </span>
                )}
              </button>
            );
          })}
        </div>

        <div className="text-[11px] font-mono text-slate-400 text-right">
          {searchQuery ? (
            <span>Found <strong>{matchingCount}</strong> of {totalCount} modules</span>
          ) : (
            <span>Total <strong>{totalCount}</strong> modules</span>
          )}
        </div>
      </div>
    </div>
  );
};
