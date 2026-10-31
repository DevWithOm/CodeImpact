import React from 'react';
import { Layers, Flame, ShieldAlert, Sparkles, Filter, FileText, CheckCircle2 } from 'lucide-react';
import { FindingsExplorer } from '../components/findings/FindingsExplorer';
import { Finding, ReviewStatus, AnalysisSummary } from '../types';

interface FindingsPageProps {
  findings: Finding[];
  activeFinding: Finding | null;
  setActiveFinding: (finding: Finding) => void;
  onUpdateReviewStatus: (findingId: string, status: ReviewStatus) => void;
  onAskAI?: (finding: Finding) => void;
  onViewInGraph?: (finding: Finding) => void;
  summary: AnalysisSummary;
  onOpenReport?: () => void;
}

export const FindingsPage: React.FC<FindingsPageProps> = ({
  findings,
  activeFinding,
  setActiveFinding,
  onUpdateReviewStatus,
  onAskAI,
  onViewInGraph,
  summary,
  onOpenReport
}) => {
  return (
    <div className="space-y-6 animate-fadeIn">
      {/* Page Header */}
      <div className="p-6 sm:p-8 rounded-3xl bg-white border border-red-100 shadow-xl shadow-red-500/5 flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="space-y-1">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-red-50 border border-red-200 text-[#FF2E55] text-xs font-black uppercase tracking-wider mb-1">
            <Layers className="w-3.5 h-3.5" />
            <span>Codebase Findings Explorer</span>
          </div>
          <h2 className="text-2xl sm:text-3xl font-black text-slate-900 tracking-tight">
            Codebase Cleanup & Risk Queue
          </h2>
          <p className="text-xs sm:text-sm text-slate-500 font-medium max-w-2xl">
            Correlated static analysis evidence from Knip, Madge, and jscpd. Review candidates thoroughly before refactoring.
          </p>
        </div>

        {/* Quick Summary Pill Counters */}
        <div className="flex flex-wrap items-center gap-2">
          <div className="px-3.5 py-2 rounded-2xl bg-slate-50 border border-slate-200 text-center font-mono">
            <span className="text-[10px] text-slate-400 uppercase font-sans font-black block">Total</span>
            <span className="text-base font-black text-slate-900">{findings.length}</span>
          </div>
          <div className="px-3.5 py-2 rounded-2xl bg-red-50 border border-red-200 text-center font-mono">
            <span className="text-[10px] text-[#FF2E55] uppercase font-sans font-black block">Cycles</span>
            <span className="text-base font-black text-[#FF2E55]">
              {findings.filter(f => f.category === 'Circular dependencies').length}
            </span>
          </div>
          <div className="px-3.5 py-2 rounded-2xl bg-rose-50 border border-rose-200 text-center font-mono">
            <span className="text-[10px] text-rose-700 uppercase font-sans font-black block">Clones</span>
            <span className="text-base font-black text-rose-700">
              {findings.filter(f => f.category === 'Duplicate code').length}
            </span>
          </div>
        </div>
      </div>

      {/* Main Interactive Findings Explorer */}
      <FindingsExplorer
        findings={findings}
        activeFinding={activeFinding}
        setActiveFinding={setActiveFinding}
        onUpdateReviewStatus={onUpdateReviewStatus}
        onAskAI={onAskAI}
        onViewInGraph={onViewInGraph}
      />
    </div>
  );
};
