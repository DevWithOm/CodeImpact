import React from 'react';
import { Flame, ChevronRight, ShieldCheck, ArrowRight } from 'lucide-react';

interface WorkflowStoryCardProps {
  onInspectPriorityQueue: () => void;
}

export const WorkflowStoryCard: React.FC<WorkflowStoryCardProps> = ({
  onInspectPriorityQueue
}) => {
  return (
    <div className="p-6 sm:p-8 rounded-3xl bg-slate-900 text-white shadow-xl relative overflow-hidden border border-red-900/40">
      {/* Background Glow */}
      <div className="absolute -right-20 -bottom-20 w-80 h-80 rounded-full bg-[#FF2E55]/15 blur-3xl pointer-events-none" />

      <div className="relative z-10 flex flex-col md:flex-row items-start md:items-center justify-between gap-6">
        <div className="space-y-2">
          <div className="flex items-center gap-2 text-[#FF2E55] text-xs font-black uppercase tracking-widest">
            <Flame className="w-4 h-4" />
            The CodeImpact Story Pattern
          </div>

          <h3 className="text-xl sm:text-2xl font-black text-white flex flex-wrap items-center gap-x-2 gap-y-1">
            <span>Repository Findings</span>
            <ChevronRight className="w-5 h-5 text-[#FF2E55] shrink-0" />
            <span>Analyzer Evidence</span>
            <ChevronRight className="w-5 h-5 text-[#FF2E55] shrink-0" />
            <span>Impact Context</span>
            <ChevronRight className="w-5 h-5 text-[#FF2E55] shrink-0" />
            <span className="text-[#FF2E55]">Responsible Action</span>
          </h3>

          <p className="text-slate-300 text-xs sm:text-sm font-medium max-w-2xl leading-relaxed">
            Never auto-delete code based purely on static flags. CodeImpact reveals the exact analyzer triggers, incoming dependents, affected test files, and runtime uncertainty limits before any refactoring takes place.
          </p>

          <div className="flex items-center gap-4 pt-1 text-xs text-slate-400 font-mono">
            <span className="flex items-center gap-1 text-emerald-400">
              <ShieldCheck className="w-4 h-4" /> Zero Auto-Destructive Changes
            </span>
            <span>•</span>
            <span>Grounded In Exact AST Evidence</span>
          </div>
        </div>

        <button
          onClick={onInspectPriorityQueue}
          className="px-6 py-3.5 rounded-2xl bg-[#FF2E55] text-white hover:bg-red-600 font-black text-xs uppercase tracking-wider shadow-lg shadow-red-500/30 hover:scale-105 active:scale-95 transition-all flex items-center gap-2 shrink-0 group"
        >
          <span>Inspect Priority Queue</span>
          <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
        </button>
      </div>
    </div>
  );
};
