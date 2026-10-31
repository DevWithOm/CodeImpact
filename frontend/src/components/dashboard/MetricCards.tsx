import React from 'react';
import { Trash2, FileText, AlertTriangle, Zap } from 'lucide-react';
import { AnalysisSummary } from '../../types';

interface MetricCardsProps {
  summary: AnalysisSummary;
  onFilterCategory?: (category: string) => void;
  onSelectTab?: (tab: string) => void;
}

export const MetricCards: React.FC<MetricCardsProps> = ({
  summary,
  onFilterCategory,
  onSelectTab
}) => {
  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
      {/* 1. Potentially Unused */}
      <div
        onClick={() => {
          if (onFilterCategory) onFilterCategory('Unused Export');
          if (onSelectTab) onSelectTab('findings');
        }}
        className="p-5 rounded-2xl bg-white border border-red-100 shadow-xl shadow-red-500/5 hover:border-red-300 transition-all cursor-pointer group"
      >
        <div className="flex items-center justify-between mb-3">
          <span className="text-xs font-black uppercase tracking-wider text-slate-400">Potentially Unused</span>
          <div className="w-9 h-9 rounded-xl bg-red-50 text-[#FF2E55] flex items-center justify-center font-bold border border-red-200 group-hover:scale-110 transition-transform">
            <Trash2 className="w-4 h-4" />
          </div>
        </div>
        <div className="flex items-baseline gap-2">
          <span className="text-3xl font-black text-slate-900">{summary.potentiallyUnusedCount}</span>
          <span className="text-xs font-extrabold text-[#FF2E55] bg-red-50 px-2 py-0.5 rounded-full border border-red-200">
            Knip Scanned
          </span>
        </div>
        <p className="text-xs text-slate-500 mt-2 font-medium">Unreferenced exports & isolated files needing manual verification.</p>
      </div>

      {/* 2. Duplication Clones */}
      <div
        onClick={() => {
          if (onFilterCategory) onFilterCategory('Code Duplication');
          if (onSelectTab) onSelectTab('findings');
        }}
        className="p-5 rounded-2xl bg-white border border-red-100 shadow-xl shadow-red-500/5 hover:border-red-300 transition-all cursor-pointer group"
      >
        <div className="flex items-center justify-between mb-3">
          <span className="text-xs font-black uppercase tracking-wider text-slate-400">Duplication Clones</span>
          <div className="w-9 h-9 rounded-xl bg-rose-50 text-rose-600 flex items-center justify-center font-bold border border-rose-200 group-hover:scale-110 transition-transform">
            <FileText className="w-4 h-4" />
          </div>
        </div>
        <div className="flex items-baseline gap-2">
          <span className="text-3xl font-black text-slate-900">{summary.duplicationClonesCount}</span>
          <span className="text-xs font-extrabold text-rose-600 bg-rose-50 px-2 py-0.5 rounded-full border border-rose-200">
            jscpd Matches
          </span>
        </div>
        <p className="text-xs text-slate-500 mt-2 font-medium">Identical AST clones with over 85% structural similarity.</p>
      </div>

      {/* 3. Circular Cycles */}
      <div
        onClick={() => {
          if (onSelectTab) onSelectTab('graph');
        }}
        className="p-5 rounded-2xl bg-white border border-red-100 shadow-xl shadow-red-500/5 hover:border-red-300 transition-all cursor-pointer group"
      >
        <div className="flex items-center justify-between mb-3">
          <span className="text-xs font-black uppercase tracking-wider text-slate-400">Circular Cycles</span>
          <div className="w-9 h-9 rounded-xl bg-red-100 text-red-700 flex items-center justify-center font-bold border border-red-300 group-hover:scale-110 transition-transform">
            <AlertTriangle className="w-4 h-4" />
          </div>
        </div>
        <div className="flex items-baseline gap-2">
          <span className="text-3xl font-black text-slate-900">{summary.circularCyclesCount}</span>
          <span className="text-xs font-extrabold text-red-700 bg-red-100 px-2 py-0.5 rounded-full border border-red-300">
            Madge Detected
          </span>
        </div>
        <p className="text-xs text-slate-500 mt-2 font-medium">Module circular dependency chains creating initialization risks.</p>
      </div>

      {/* 4. Hotspot Risk Index */}
      <div
        onClick={() => {
          if (onFilterCategory) onFilterCategory('All');
          if (onSelectTab) onSelectTab('findings');
        }}
        className="p-5 rounded-2xl bg-white border border-red-100 shadow-xl shadow-red-500/5 hover:border-red-300 transition-all cursor-pointer group"
      >
        <div className="flex items-center justify-between mb-3">
          <span className="text-xs font-black uppercase tracking-wider text-slate-400">Hotspot Risk Index</span>
          <div className="w-9 h-9 rounded-xl bg-slate-900 text-[#FF2E55] flex items-center justify-center font-bold group-hover:scale-110 transition-transform">
            <Zap className="w-4 h-4" />
          </div>
        </div>
        <div className="flex items-baseline gap-2">
          <span className="text-3xl font-black text-slate-900">{summary.hotspotRiskIndex}</span>
          <span className="text-xs font-extrabold text-white bg-[#FF2E55] px-2 py-0.5 rounded-full">
            High Impact
          </span>
        </div>
        <p className="text-xs text-slate-500 mt-2 font-medium">Modules with deep dependent fan-out requiring test verification.</p>
      </div>
    </div>
  );
};
