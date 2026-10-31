import React, { useState } from 'react';
import {
  FileCode,
  AlertTriangle,
  Flame,
  Layers,
  CopyCheck,
  Compass,
  ArrowDownLeft,
  ArrowUpRight,
  ShieldAlert,
  CheckCircle2,
  Info,
  ExternalLink,
  Target,
  X,
  Copy,
  Check
} from 'lucide-react';
import { GraphNode } from '../../types';

interface ModuleDetailsPanelProps {
  node: GraphNode | null;
  nodes: GraphNode[];
  incomingNodes: GraphNode[];
  outgoingNodes: GraphNode[];
  isFocusMode: boolean;
  onToggleFocusMode: () => void;
  onSelectNode: (node: GraphNode) => void;
  onClose: () => void;
  onInspectLinkedFindings: (node: GraphNode) => void;
}

export const ModuleDetailsPanel: React.FC<ModuleDetailsPanelProps> = ({
  node,
  incomingNodes,
  outgoingNodes,
  isFocusMode,
  onToggleFocusMode,
  onSelectNode,
  onClose,
  onInspectLinkedFindings
}) => {
  const [copied, setCopied] = useState(false);

  if (!node) {
    return (
      <div className="p-6 rounded-3xl bg-white border border-slate-200 shadow-xl text-center space-y-3">
        <div className="w-12 h-12 rounded-2xl bg-slate-100 text-slate-400 mx-auto flex items-center justify-center">
          <Target className="w-6 h-6" />
        </div>
        <h4 className="text-sm font-bold text-slate-800">No Module Selected</h4>
        <p className="text-xs text-slate-500 max-w-xs mx-auto">
          Click any module node or circular dependency cycle in the canvas to inspect its dependency context, incoming callers, and verification checklist.
        </p>
      </div>
    );
  }

  const handleCopyPath = () => {
    if (node.filePath || node.label) {
      navigator.clipboard.writeText(node.filePath || node.label);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const isCycle = node.type === 'cycle';
  const isHotspot = node.type === 'hotspot';
  const isUnused = node.type === 'unused';
  const isDuplicate = node.type === 'duplicate';
  const isEntry = node.type === 'entry';

  return (
    <div className="rounded-3xl bg-white border border-slate-200/80 shadow-xl overflow-hidden flex flex-col space-y-4 p-5 animate-fadeIn">
      {/* 1. Header Bar */}
      <div className="flex items-start justify-between gap-3 border-b border-slate-100 pb-3">
        <div className="space-y-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span
              className={`text-[10px] font-black uppercase px-2 py-0.5 rounded-md border flex items-center gap-1 ${
                isCycle
                  ? 'bg-red-50 text-red-700 border-red-200'
                  : isHotspot
                  ? 'bg-rose-50 text-rose-700 border-rose-200'
                  : isUnused
                  ? 'bg-amber-50 text-amber-800 border-amber-200'
                  : isDuplicate
                  ? 'bg-purple-50 text-purple-700 border-purple-200'
                  : isEntry
                  ? 'bg-blue-50 text-blue-700 border-blue-200'
                  : 'bg-slate-100 text-slate-700 border-slate-200'
              }`}
            >
              {isCycle && <AlertTriangle className="w-3 h-3 text-[#FF2E55]" />}
              {isHotspot && <Flame className="w-3 h-3 text-rose-600" />}
              {isUnused && <Layers className="w-3 h-3 text-amber-600" />}
              {isDuplicate && <CopyCheck className="w-3 h-3 text-purple-600" />}
              {isEntry && <Compass className="w-3 h-3 text-blue-600" />}
              <span>{node.type.toUpperCase()} MODULE</span>
            </span>

            <span
              className={`text-[10px] font-mono font-bold px-2 py-0.5 rounded ${
                node.risk === 'high' || node.risk === 'critical'
                  ? 'bg-red-100 text-red-700'
                  : node.risk === 'medium'
                  ? 'bg-amber-100 text-amber-800'
                  : 'bg-emerald-100 text-emerald-800'
              }`}
            >
              Risk: {node.risk.toUpperCase()}
            </span>
          </div>

          <h3 className="text-base font-black text-slate-900 font-mono truncate" title={node.label}>
            {node.label}
          </h3>

          <div className="flex items-center gap-1.5 text-xs text-slate-500 font-mono">
            <span className="truncate max-w-[200px]" title={node.filePath || node.label}>
              {node.filePath || node.label}
            </span>
            <button
              onClick={handleCopyPath}
              className="p-1 hover:text-slate-800 rounded transition-colors"
              title="Copy file path"
            >
              {copied ? <Check className="w-3 h-3 text-emerald-600" /> : <Copy className="w-3 h-3" />}
            </button>
          </div>
        </div>

        <button
          onClick={onClose}
          className="p-1.5 rounded-xl hover:bg-slate-100 text-slate-400 hover:text-slate-700 transition-colors shrink-0"
          title="Close details"
        >
          <X className="w-4 h-4" />
        </button>
      </div>

      {/* 2. Fan-In / Fan-Out Metrics Bar */}
      <div className="grid grid-cols-2 gap-2 text-center font-mono">
        <div className="p-2.5 rounded-2xl bg-sky-50/60 border border-sky-100">
          <span className="text-[10px] uppercase font-bold text-sky-700 font-sans block flex items-center justify-center gap-1">
            <ArrowDownLeft className="w-3 h-3 text-sky-600" />
            Incoming Callers
          </span>
          <span className="text-lg font-black text-slate-900">{node.incomingCount ?? incomingNodes.length}</span>
          <span className="text-[9px] text-slate-500 block">Depended on by</span>
        </div>

        <div className="p-2.5 rounded-2xl bg-amber-50/60 border border-amber-100">
          <span className="text-[10px] uppercase font-bold text-amber-800 font-sans block flex items-center justify-center gap-1">
            <ArrowUpRight className="w-3 h-3 text-amber-600" />
            Outgoing Imports
          </span>
          <span className="text-lg font-black text-slate-900">{node.outgoingCount ?? outgoingNodes.length}</span>
          <span className="text-[9px] text-slate-500 block">Depends upon</span>
        </div>
      </div>

      {/* 3. Circular Dependency Warning Alert if cycle participant */}
      {isCycle && (
        <div className="p-3.5 rounded-2xl bg-red-50/90 border border-red-200 space-y-1.5">
          <div className="flex items-center gap-1.5 text-xs font-black text-red-700 uppercase">
            <AlertTriangle className="w-3.5 h-3.5 text-[#FF2E55]" />
            <span>Active Circular Dependency Cycle</span>
          </div>
          <p className="text-xs text-red-950 font-medium leading-relaxed">
            This module has a reciprocal import loop. Mutual evaluation risks runtime reference errors (`Cannot access antes initialization`).
          </p>
        </div>
      )}

      {/* 4. Dependency Connections: Incoming & Outgoing */}
      <div className="space-y-3 pt-1">
        {/* Depended on by (Incoming) */}
        <div>
          <span className="text-[10px] uppercase font-black text-slate-400 block mb-1">
            Depended on by ({incomingNodes.length})
          </span>
          {incomingNodes.length > 0 ? (
            <div className="flex flex-wrap gap-1.5">
              {incomingNodes.map((inNode) => (
                <button
                  key={inNode.id}
                  onClick={() => onSelectNode(inNode)}
                  className="px-2.5 py-1 rounded-lg bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-mono font-medium flex items-center gap-1.5 transition-colors border border-slate-200"
                >
                  <FileCode className="w-3 h-3 text-sky-600" />
                  <span className="truncate max-w-[130px]">{inNode.label}</span>
                </button>
              ))}
            </div>
          ) : (
            <p className="text-xs text-slate-400 italic">No incoming imports (entrypoint or isolated dead code).</p>
          )}
        </div>

        {/* Depends on (Outgoing) */}
        <div>
          <span className="text-[10px] uppercase font-black text-slate-400 block mb-1">
            Depends on ({outgoingNodes.length})
          </span>
          {outgoingNodes.length > 0 ? (
            <div className="flex flex-wrap gap-1.5">
              {outgoingNodes.map((outNode) => (
                <button
                  key={outNode.id}
                  onClick={() => onSelectNode(outNode)}
                  className="px-2.5 py-1 rounded-lg bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-mono font-medium flex items-center gap-1.5 transition-colors border border-slate-200"
                >
                  <FileCode className="w-3 h-3 text-amber-600" />
                  <span className="truncate max-w-[130px]">{outNode.label}</span>
                </button>
              ))}
            </div>
          ) : (
            <p className="text-xs text-slate-400 italic">Leaf node with zero outgoing dependencies.</p>
          )}
        </div>
      </div>

      {/* 5. Impact & Evidence */}
      {node.riskEvidence && (
        <div className="p-3.5 rounded-2xl bg-slate-50 border border-slate-200 space-y-1.5">
          <span className="text-[10px] uppercase font-black text-slate-500 block flex items-center gap-1">
            <ShieldAlert className="w-3 h-3 text-[#FF2E55]" />
            Analyzer Blast Radius Evidence
          </span>
          <p className="text-xs text-slate-700 leading-relaxed font-medium">
            {node.riskEvidence}
          </p>

          {node.affectedTests && node.affectedTests.length > 0 && (
            <div className="pt-2 border-t border-slate-200 text-[11px] text-slate-600 space-y-1">
              <strong className="text-slate-800 font-semibold block">Mapped Test Suites:</strong>
              <ul className="space-y-0.5 font-mono text-[10px]">
                {node.affectedTests.map((testPath, idx) => (
                  <li key={idx} className="flex items-center gap-1 text-slate-600">
                    <span className="text-emerald-600">✓</span>
                    <span>{testPath}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}

      {/* 6. Verification Checklist */}
      <div className="p-3.5 rounded-2xl bg-amber-50/70 border border-amber-200/90 space-y-1.5">
        <span className="text-[10px] uppercase font-black text-amber-900 block flex items-center gap-1">
          <CheckCircle2 className="w-3.5 h-3.5 text-amber-600" />
          Recommended Verification Steps
        </span>
        <ul className="space-y-1 text-xs text-amber-950">
          {(node.verificationSteps || [
            'Search for dynamic imports using regex `import\\(.*\\)`.',
            'Run full test suite targeting caller components.',
            'Confirm no external consumption in package index.'
          ]).map((step, idx) => (
            <li key={idx} className="flex items-start gap-1.5 leading-snug">
              <span className="text-amber-600 font-bold mt-0.5">•</span>
              <span>{step}</span>
            </li>
          ))}
        </ul>
      </div>

      {/* 7. Runtime Caveat */}
      <div className="p-3 rounded-xl bg-slate-100 text-[10px] text-slate-600 flex items-start gap-2 border border-slate-200 leading-relaxed">
        <Info className="w-3.5 h-3.5 text-slate-400 shrink-0 mt-0.5" />
        <span>
          <strong>Runtime Uncertainty Caveat:</strong> Static module graphs do not reflect runtime reflection, dynamic bundler code-splits, or Web Worker instantiation. Always verify with automated tests.
        </span>
      </div>

      {/* 8. Action CTAs */}
      <div className="pt-1 flex flex-col sm:flex-row gap-2">
        <button
          onClick={() => onInspectLinkedFindings(node)}
          className="flex-1 py-2.5 px-3 rounded-xl bg-[#FF2E55] hover:bg-red-600 text-white text-xs font-black shadow-md shadow-red-500/20 flex items-center justify-center gap-1.5 transition-colors"
        >
          <ExternalLink className="w-3.5 h-3.5" />
          <span>Inspect Linked Findings ({node.findingCount ?? 0})</span>
        </button>

        <button
          onClick={onToggleFocusMode}
          className={`py-2.5 px-3 rounded-xl border text-xs font-extrabold flex items-center justify-center gap-1.5 transition-colors ${
            isFocusMode
              ? 'bg-slate-900 text-white border-slate-900'
              : 'bg-slate-100 hover:bg-slate-200 text-slate-700 border-slate-200'
          }`}
        >
          <Target className="w-3.5 h-3.5" />
          <span>{isFocusMode ? 'Show Full Graph' : 'Focus Neighborhood'}</span>
        </button>
      </div>
    </div>
  );
};
