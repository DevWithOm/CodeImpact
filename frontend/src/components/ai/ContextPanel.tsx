import React, { useState } from 'react';
import {
  FileCode,
  GitBranch,
  ShieldAlert,
  Layers,
  ArrowDownLeft,
  ArrowUpRight,
  ExternalLink,
  ChevronDown,
  CheckCircle2,
  AlertTriangle,
  FolderGit2,
  Check,
  Target
} from 'lucide-react';
import { Finding } from '../../types';

interface ContextPanelProps {
  activeFinding: Finding | null;
  findings: Finding[];
  onSelectFinding: (finding: Finding) => void;
  onNavigateToFindings: () => void;
  onNavigateToGraph: (finding: Finding) => void;
  repoUrl: string;
  branch: string;
}

export const ContextPanel: React.FC<ContextPanelProps> = ({
  activeFinding,
  findings,
  onSelectFinding,
  onNavigateToFindings,
  onNavigateToGraph,
  repoUrl,
  branch
}) => {
  const [isDropdownOpen, setIsDropdownOpen] = useState(false);

  // If no finding selected, show selector card
  if (!activeFinding) {
    return (
      <div className="p-6 rounded-3xl bg-white border border-slate-200/80 shadow-xl space-y-4 text-center">
        <div className="w-12 h-12 rounded-2xl bg-red-50 text-[#FF2E55] mx-auto flex items-center justify-center border border-red-200">
          <Target className="w-6 h-6" />
        </div>
        <h3 className="text-sm font-black text-slate-900">Select a Finding to Ground AI</h3>
        <p className="text-xs text-slate-500 leading-relaxed max-w-xs mx-auto">
          Choose a static code finding below to give the assistant AST context, blast radius details, and test suites.
        </p>

        <div className="space-y-2 text-left pt-2 max-h-[300px] overflow-y-auto">
          {findings.map((f) => (
            <button
              key={f.id}
              onClick={() => onSelectFinding(f)}
              className="w-full p-2.5 rounded-xl border border-slate-200 bg-slate-50 hover:bg-red-50/60 hover:border-red-300 transition-all text-left flex items-start gap-2.5"
            >
              <FileCode className="w-4 h-4 text-[#FF2E55] shrink-0 mt-0.5" />
              <div className="min-w-0 flex-1">
                <div className="flex items-center justify-between gap-1">
                  <span className="text-xs font-bold text-slate-800 truncate">{f.title}</span>
                  <span className="text-[10px] font-mono font-bold text-slate-500 shrink-0">{f.id}</span>
                </div>
                <p className="text-[10px] text-slate-500 font-mono truncate">{f.file}</p>
              </div>
            </button>
          ))}
        </div>
      </div>
    );
  }

  const incomingCount = activeFinding.dependencyContext.incoming;
  const outgoingCount = activeFinding.dependencyContext.outgoing;
  const tests = activeFinding.testImpactContext?.testFiles || activeFinding.dependencyContext.affectedTests;

  return (
    <div className="rounded-3xl bg-white border border-slate-200/80 shadow-xl p-5 space-y-4 animate-fadeIn">
      {/* 1. Repository Context Banner */}
      <div className="p-3 rounded-2xl bg-[#0F0F12] text-white flex items-center justify-between gap-2 text-xs font-mono">
        <div className="flex items-center gap-2 truncate">
          <FolderGit2 className="w-4 h-4 text-[#FF2E55] shrink-0" />
          <span className="font-bold truncate">{repoUrl.replace('https://github.com/', '')}</span>
        </div>
        <span className="text-[10px] text-slate-400 bg-white/10 px-2 py-0.5 rounded shrink-0">
          {branch}
        </span>
      </div>

      {/* 2. Active Finding Selector Header */}
      <div className="relative">
        <div className="flex items-center justify-between text-xs font-black text-slate-400 uppercase tracking-wider mb-1.5">
          <span>Active Finding Context</span>
          <button
            onClick={() => setIsDropdownOpen((prev) => !prev)}
            className="text-[#FF2E55] hover:text-red-700 flex items-center gap-1 text-[11px] font-bold normal-case"
          >
            <span>Change</span>
            <ChevronDown className="w-3.5 h-3.5" />
          </button>
        </div>

        {/* Change Finding Dropdown Menu */}
        {isDropdownOpen && (
          <div className="absolute top-8 left-0 right-0 z-30 bg-white rounded-2xl border border-slate-200 shadow-2xl p-2 max-h-[300px] overflow-y-auto space-y-1">
            <span className="px-2 py-1 text-[10px] uppercase font-black text-slate-400 block font-mono">
              Switch Context to Finding:
            </span>
            {findings.map((f) => (
              <button
                key={f.id}
                onClick={() => {
                  onSelectFinding(f);
                  setIsDropdownOpen(false);
                }}
                className={`w-full text-left p-2 rounded-xl text-xs flex items-center justify-between transition-colors ${
                  activeFinding.id === f.id
                    ? 'bg-red-50 text-[#FF2E55] font-bold'
                    : 'hover:bg-slate-100 text-slate-700'
                }`}
              >
                <div className="truncate pr-2">
                  <div className="truncate font-semibold">{f.title}</div>
                  <div className="text-[10px] text-slate-400 font-mono truncate">{f.file}</div>
                </div>
                {activeFinding.id === f.id && <Check className="w-4 h-4 text-[#FF2E55] shrink-0" />}
              </button>
            ))}
          </div>
        )}

        {/* Selected Finding Card */}
        <div className="p-3.5 rounded-2xl bg-slate-50 border border-slate-200 space-y-2">
          <div className="flex items-center justify-between gap-1">
            <span className="text-[10px] font-mono font-bold text-slate-500 bg-white px-2 py-0.5 rounded border border-slate-200">
              {activeFinding.id}
            </span>
            <span className="text-[10px] font-bold text-[#FF2E55] bg-red-50 px-2 py-0.5 rounded border border-red-200 truncate">
              {activeFinding.category}
            </span>
          </div>

          <h4 className="text-xs font-black text-slate-900 leading-snug line-clamp-2">
            {activeFinding.title}
          </h4>

          <div className="flex items-center gap-1.5 text-xs text-slate-600 font-mono">
            <FileCode className="w-3.5 h-3.5 text-slate-400 shrink-0" />
            <span className="truncate">{activeFinding.file}</span>
            <span className="text-slate-400 shrink-0">({activeFinding.lines})</span>
          </div>
        </div>
      </div>

      {/* 3. Reliability & Impact Grid */}
      <div className="grid grid-cols-2 gap-2 text-center font-mono">
        <div className="p-2.5 rounded-2xl bg-slate-50 border border-slate-200">
          <span className="text-[10px] uppercase font-bold text-slate-400 block font-sans">Confidence</span>
          <span className="text-base font-black text-slate-900">{activeFinding.confidence}%</span>
          <span className="text-[9px] text-slate-500 block truncate">{activeFinding.analyzer}</span>
        </div>

        <div className="p-2.5 rounded-2xl bg-slate-50 border border-slate-200">
          <span className="text-[10px] uppercase font-bold text-slate-400 block font-sans">Impact Risk</span>
          <span
            className={`text-base font-black ${
              activeFinding.impactRiskType === 'high' ? 'text-red-600' : 'text-amber-600'
            }`}
          >
            {activeFinding.impactRisk}
          </span>
          <span className="text-[9px] text-slate-500 block">Score: {activeFinding.impactScore}/100</span>
        </div>
      </div>

      {/* 4. Dependency Topology */}
      <div className="p-3.5 rounded-2xl bg-slate-50 border border-slate-200 space-y-2">
        <span className="text-[10px] uppercase font-black text-slate-500 block flex items-center justify-between">
          <span>Dependency Context</span>
          <span className="font-mono text-slate-400">In: {incomingCount} | Out: {outgoingCount}</span>
        </span>

        <div className="grid grid-cols-2 gap-2">
          <div className="p-2 rounded-xl bg-white border border-slate-200 text-center">
            <span className="text-[10px] text-sky-700 font-bold flex items-center justify-center gap-0.5">
              <ArrowDownLeft className="w-3 h-3" /> Callers
            </span>
            <span className="text-sm font-black text-slate-800">{incomingCount}</span>
          </div>

          <div className="p-2 rounded-xl bg-white border border-slate-200 text-center">
            <span className="text-[10px] text-amber-700 font-bold flex items-center justify-center gap-0.5">
              <ArrowUpRight className="w-3 h-3" /> Imports
            </span>
            <span className="text-sm font-black text-slate-800">{outgoingCount}</span>
          </div>
        </div>

        {activeFinding.dependencyContext.affectedModules.length > 0 && (
          <div className="text-[11px] text-slate-600 space-y-1 pt-1 border-t border-slate-200">
            <span className="font-bold text-slate-800 block text-[10px] uppercase">Downstream modules:</span>
            <ul className="space-y-0.5 font-mono text-[10px] text-slate-500">
              {activeFinding.dependencyContext.affectedModules.slice(0, 3).map((m, idx) => (
                <li key={idx} className="truncate">• {m}</li>
              ))}
            </ul>
          </div>
        )}
      </div>

      {/* 5. Mapped Test Suites */}
      {tests.length > 0 && (
        <div className="p-3.5 rounded-2xl bg-emerald-50/70 border border-emerald-200 space-y-1.5">
          <span className="text-[10px] uppercase font-black text-emerald-900 block flex items-center gap-1">
            <CheckCircle2 className="w-3 h-3 text-emerald-600" />
            Mapped Test Suites ({tests.length})
          </span>
          <ul className="space-y-1 font-mono text-[10px] text-emerald-950">
            {tests.map((t, idx) => (
              <li key={idx} className="truncate">✓ {t}</li>
            ))}
          </ul>
        </div>
      )}

      {/* 6. Navigation Actions */}
      <div className="pt-1 flex flex-col gap-2">
        <button
          onClick={onNavigateToFindings}
          className="w-full py-2 px-3 rounded-xl bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-extrabold flex items-center justify-center gap-1.5 transition-colors border border-slate-200"
        >
          <ExternalLink className="w-3.5 h-3.5" />
          <span>View in Findings Explorer</span>
        </button>

        <button
          onClick={() => onNavigateToGraph(activeFinding)}
          className="w-full py-2 px-3 rounded-xl bg-red-50 hover:bg-red-100 text-[#FF2E55] text-xs font-extrabold flex items-center justify-center gap-1.5 transition-colors border border-red-200"
        >
          <GitBranch className="w-3.5 h-3.5" />
          <span>View in Dependency Graph</span>
        </button>
      </div>
    </div>
  );
};
