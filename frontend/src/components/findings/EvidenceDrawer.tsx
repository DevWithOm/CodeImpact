import React, { useState } from 'react';
import {
  Cpu,
  Code2,
  GitBranch,
  AlertTriangle,
  CheckCircle2,
  Info,
  Copy,
  Check,
  Sparkles,
  FlaskConical,
  ShieldAlert,
  SlidersHorizontal,
  ChevronDown,
  Layers
} from 'lucide-react';
import { Finding, ReviewStatus } from '../../types';
import { RiskBadge } from './RiskBadge';

interface EvidenceDrawerProps {
  finding: Finding | null;
  onAskAI?: (finding: Finding) => void;
  onViewInGraph?: (finding: Finding) => void;
  onUpdateReviewStatus?: (findingId: string, status: ReviewStatus) => void;
  onClose?: () => void;
}

export const EvidenceDrawer: React.FC<EvidenceDrawerProps> = ({
  finding,
  onAskAI,
  onViewInGraph,
  onUpdateReviewStatus,
  onClose
}) => {
  const [copiedCode, setCopiedCode] = useState(false);
  const [isStatusDropdownOpen, setIsStatusDropdownOpen] = useState(false);

  if (!finding) {
    return (
      <div className="p-8 text-center rounded-3xl bg-white border border-slate-200 text-slate-400 space-y-3 shadow-sm">
        <div className="w-12 h-12 rounded-2xl bg-slate-100 text-slate-400 flex items-center justify-center mx-auto">
          <Layers className="w-6 h-6" />
        </div>
        <h4 className="text-sm font-bold text-slate-700">No Finding Selected</h4>
        <p className="text-xs text-slate-500 max-w-xs mx-auto">
          Click on any item in the findings list to inspect analyzer evidence, blast radius, and verification steps.
        </p>
      </div>
    );
  }

  const copyCode = (text: string) => {
    navigator.clipboard.writeText(text);
    setCopiedCode(true);
    setTimeout(() => setCopiedCode(false), 2000);
  };

  const statusOptions: ReviewStatus[] = [
    'Pending Review',
    'In Review',
    'Verified for Refactor',
    'False Positive (Keep)',
    'High Risk (Do Not Touch)'
  ];

  return (
    <div className="sticky top-20 rounded-3xl bg-white border border-red-200 shadow-xl shadow-red-500/10 p-6 space-y-6">
      {/* 1. Finding Overview Header */}
      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="text-xs font-mono bg-slate-100 px-2 py-0.5 rounded text-slate-700 font-bold">
              {finding.id}
            </span>
            <RiskBadge type={finding.severity} />
          </div>

          {/* Interactive Review Status Selector */}
          <div className="relative">
            <button
              onClick={() => setIsStatusDropdownOpen(!isStatusDropdownOpen)}
              className="flex items-center gap-1.5 px-2.5 py-1 rounded-xl text-xs font-bold border border-slate-200 hover:border-red-200 bg-slate-50 transition-all text-slate-700"
              title="Change local review status"
            >
              <span className="text-[10px] text-slate-400 uppercase font-mono">Status:</span>
              <RiskBadge type={finding.reviewStatus} />
              <ChevronDown className="w-3 h-3 text-slate-400" />
            </button>

            {isStatusDropdownOpen && (
              <div className="absolute right-0 mt-1 w-56 rounded-2xl bg-white border border-slate-200 shadow-xl p-1.5 z-30 space-y-1">
                <div className="px-2 py-1 text-[10px] font-black uppercase text-slate-400 font-mono">
                  Update Review Status
                </div>
                {statusOptions.map((st) => (
                  <button
                    key={st}
                    onClick={() => {
                      if (onUpdateReviewStatus) onUpdateReviewStatus(finding.id, st);
                      setIsStatusDropdownOpen(false);
                    }}
                    className={`w-full text-left px-2.5 py-1.5 rounded-xl text-xs font-bold transition-all flex items-center justify-between ${
                      finding.reviewStatus === st
                        ? 'bg-red-50 text-[#FF2E55]'
                        : 'hover:bg-slate-100 text-slate-700'
                    }`}
                  >
                    <span>{st}</span>
                    {finding.reviewStatus === st && <Check className="w-3.5 h-3.5 text-[#FF2E55]" />}
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>

        <h3 className="text-lg font-black text-slate-900 leading-snug">{finding.title}</h3>

        <div className="flex flex-wrap items-center gap-2 text-xs font-mono text-slate-500 pt-0.5">
          <span className="text-slate-800 font-bold">{finding.file}</span>
          <span>({finding.lines})</span>
        </div>

        {/* Confidence & Impact Risk Bar */}
        <div className="grid grid-cols-2 gap-2 pt-1 text-center font-mono">
          <div className="p-2.5 rounded-xl bg-slate-50 border border-slate-200">
            <span className="text-[10px] uppercase font-black text-slate-400 block font-sans">
              Confidence Level
            </span>
            <span className="text-base font-black text-slate-900">{finding.confidence}%</span>
            <span className="text-[10px] text-slate-500 block">AST Evidence Match</span>
          </div>
          <div className="p-2.5 rounded-xl bg-slate-50 border border-slate-200">
            <span className="text-[10px] uppercase font-black text-slate-400 block font-sans">
              Impact Risk
            </span>
            <span className={`text-base font-black ${
              finding.impactRiskType === 'high' ? 'text-red-600' : 'text-amber-600'
            }`}>
              {finding.impactRisk}
            </span>
            <span className="text-[10px] text-slate-500 block">Score: {finding.impactScore}/100</span>
          </div>
        </div>
      </div>

      {/* 2. Detection Evidence Box */}
      <div className="p-4 rounded-2xl bg-slate-50 border border-slate-200 space-y-2">
        <div className="flex items-center justify-between text-xs">
          <span className="font-extrabold text-slate-800 flex items-center gap-1.5">
            <Cpu className="w-3.5 h-3.5 text-[#FF2E55]" />
            Analyzer Detection Evidence
          </span>
          <span className="text-[10px] font-bold text-[#FF2E55] bg-red-50 px-2 py-0.5 rounded border border-red-200">
            {finding.analyzer}
          </span>
        </div>
        <p className="text-xs text-slate-600 font-medium leading-relaxed">{finding.description}</p>
      </div>

      {/* Relevant Code Snippet */}
      {finding.codeSnippet && (
        <div className="space-y-1.5">
          <div className="flex items-center justify-between text-xs">
            <span className="font-extrabold text-slate-700 flex items-center gap-1.5">
              <Code2 className="w-3.5 h-3.5 text-slate-500" />
              Source Code Location ({finding.lines})
            </span>
            <button
              onClick={() => copyCode(finding.codeSnippet)}
              className="text-[10px] font-bold text-[#FF2E55] hover:underline flex items-center gap-1"
            >
              {copiedCode ? <Check className="w-3 h-3" /> : <Copy className="w-3 h-3" />}
              <span>{copiedCode ? 'Copied' : 'Copy'}</span>
            </button>
          </div>
          <pre className="p-3.5 rounded-2xl bg-[#0F0F12] text-red-300 font-mono text-[11px] overflow-x-auto leading-relaxed border border-red-900/40">
            <code>{finding.codeSnippet}</code>
          </pre>
        </div>
      )}

      {/* 3. Dependency Impact Scope */}
      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <span className="text-xs font-extrabold text-slate-700 flex items-center gap-1.5">
            <GitBranch className="w-3.5 h-3.5 text-[#FF2E55]" />
            Dependency Impact & Fan-out
          </span>
          <span className="text-[10px] font-mono text-slate-400">Blast Radius</span>
        </div>

        <div className="grid grid-cols-2 gap-2 text-center">
          <div className="p-2.5 rounded-xl bg-red-50 border border-red-100">
            <span className="text-[10px] uppercase font-black text-[#FF2E55] block">Incoming Dependents</span>
            <span className="text-lg font-black text-slate-900">{finding.dependencyContext.incoming}</span>
          </div>
          <div className="p-2.5 rounded-xl bg-rose-50 border border-rose-100">
            <span className="text-[10px] uppercase font-black text-rose-600 block">Outgoing References</span>
            <span className="text-lg font-black text-slate-900">{finding.dependencyContext.outgoing}</span>
          </div>
        </div>

        {finding.dependencyContext.affectedModules.length > 0 && (
          <div className="p-3 rounded-xl bg-slate-50 border border-slate-200 text-[11px] font-mono text-slate-600">
            <span className="text-slate-400 font-sans font-bold block mb-1">Potentially Affected Modules:</span>
            <div className="flex flex-wrap gap-1">
              {finding.dependencyContext.affectedModules.map((mod) => (
                <span key={mod} className="bg-white border border-slate-200 px-1.5 py-0.5 rounded text-slate-800">
                  {mod}
                </span>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* 4. Potential Test Impact */}
      <div className="space-y-2">
        <span className="text-xs font-extrabold text-slate-700 flex items-center gap-1.5">
          <FlaskConical className="w-3.5 h-3.5 text-[#FF2E55]" />
          Potential Test Impact
        </span>

        {finding.testImpactContext ? (
          <div className="p-3.5 rounded-2xl bg-slate-50 border border-slate-200 space-y-2 text-xs">
            <div className="flex items-center justify-between">
              <span className="font-bold text-slate-800">Related Test Suites:</span>
              <span className="text-[10px] font-mono bg-white border border-slate-200 px-2 py-0.5 rounded text-slate-600 font-bold">
                {finding.testImpactContext.testFiles.length} Test File(s)
              </span>
            </div>

            {finding.testImpactContext.testFiles.length > 0 ? (
              <ul className="space-y-1 font-mono text-[11px] text-slate-700">
                {finding.testImpactContext.testFiles.map((tf) => (
                  <li key={tf} className="flex items-center gap-1.5">
                    <span className="w-1.5 h-1.5 rounded-full bg-[#FF2E55]" />
                    <span>{tf}</span>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-[11px] text-slate-500 italic">No direct test files found targeting this symbol.</p>
            )}

            <div className="pt-1 border-t border-slate-200 text-slate-600 leading-relaxed font-sans text-[11px]">
              <strong className="text-slate-800 font-semibold">Why Affected: </strong>
              {finding.testImpactContext.whyAffected}
            </div>
          </div>
        ) : (
          <div className="p-3 rounded-xl bg-slate-50 border border-slate-200 text-xs text-slate-500">
            No direct test suites mapped to this export.
          </div>
        )}
      </div>

      {/* 5. Verification Checklist */}
      <div className="p-4 rounded-2xl bg-amber-50 border border-amber-200 space-y-2">
        <div className="flex items-center gap-1.5 text-amber-900 text-xs font-black uppercase">
          <AlertTriangle className="w-4 h-4 text-amber-600 shrink-0" />
          <span>Responsible Verification Checklist</span>
        </div>
        <ul className="space-y-1.5">
          {finding.verificationSteps.map((step, idx) => (
            <li key={idx} className="text-xs text-amber-950 font-medium flex items-start gap-2">
              <CheckCircle2 className="w-3.5 h-3.5 text-amber-600 shrink-0 mt-0.5" />
              <span>{step}</span>
            </li>
          ))}
        </ul>
      </div>

      {/* 6. Dynamic Blind Spot Caveat (Uncertainty Disclaimer) */}
      <div className="p-3.5 rounded-xl bg-slate-100 text-[11px] text-slate-600 flex items-start gap-2 border border-slate-200">
        <Info className="w-4 h-4 text-slate-400 shrink-0 mt-0.5" />
        <span>
          <strong>Dynamic Blind Spot Caveat:</strong> Static analysis cannot prove dynamic import absence or reflection API usage. Do not delete code without manual confirmation or running regression tests.
        </span>
      </div>

      {/* 7. Action CTAs */}
      <div className="flex gap-2 pt-1">
        {onAskAI && (
          <button
            onClick={() => onAskAI(finding)}
            className="flex-1 py-2 px-3 rounded-xl bg-red-50 hover:bg-red-100 text-[#FF2E55] border border-red-200 text-xs font-extrabold flex items-center justify-center gap-1.5 transition-colors"
          >
            <Sparkles className="w-3.5 h-3.5" />
            <span>Consult AI</span>
          </button>
        )}
        {onViewInGraph && (
          <button
            onClick={() => onViewInGraph(finding)}
            className="flex-1 py-2 px-3 rounded-xl bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-extrabold flex items-center justify-center gap-1.5 transition-colors"
          >
            <GitBranch className="w-3.5 h-3.5" />
            <span>View in Graph</span>
          </button>
        )}
      </div>
    </div>
  );
};
