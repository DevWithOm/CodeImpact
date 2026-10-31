import React, { memo } from 'react';
import { Handle, Position, NodeProps } from '@xyflow/react';
import {
  FileCode,
  AlertTriangle,
  Flame,
  Layers,
  CopyCheck,
  Compass,
  ArrowDownLeft,
  ArrowUpRight
} from 'lucide-react';
import { GraphNode } from '../../types';

export interface ModuleNodeData {
  node: GraphNode;
  isCycle: boolean;
  isHotspot: boolean;
  isUnused: boolean;
  isDuplicate: boolean;
  isEntry: boolean;
  isSelected: boolean;
  isHighlighted: boolean;
  isDimmed: boolean;
  onSelect: (node: GraphNode) => void;
}

export const ModuleNode: React.FC<NodeProps> = memo(({ data }) => {
  const nodeData = data as unknown as ModuleNodeData;
  const {
    node,
    isCycle,
    isHotspot,
    isUnused,
    isDuplicate,
    isEntry,
    isSelected,
    isHighlighted,
    isDimmed,
    onSelect
  } = nodeData;

  // Determine border and background styling based on role
  let containerStyle = 'bg-[#141418] border-slate-700/80 text-slate-200';
  let badgeStyle = 'bg-slate-800 text-slate-300 border-slate-700';
  let badgeLabel = 'Module';
  let Icon = FileCode;

  if (isCycle) {
    containerStyle = 'bg-[#181115] border-[#FF2E55] text-white shadow-lg shadow-red-500/20';
    badgeStyle = 'bg-red-950/90 text-red-200 border-red-500/50';
    badgeLabel = 'Cycle Participant';
    Icon = AlertTriangle;
  } else if (isHotspot) {
    containerStyle = 'bg-[#191114] border-rose-600 text-rose-100 shadow-lg shadow-rose-950/40';
    badgeStyle = 'bg-rose-950 text-rose-200 border-rose-500/40';
    badgeLabel = 'Hotspot (High Fan-In)';
    Icon = Flame;
  } else if (isUnused) {
    containerStyle = 'bg-[#141418] border-amber-600/70 border-dashed text-amber-200/90';
    badgeStyle = 'bg-amber-950/70 text-amber-300 border-amber-600/30';
    badgeLabel = 'Potentially Unused';
    Icon = Layers;
  } else if (isDuplicate) {
    containerStyle = 'bg-[#141419] border-purple-600/70 text-purple-200';
    badgeStyle = 'bg-purple-950/70 text-purple-300 border-purple-600/30';
    badgeLabel = 'Clone / Duplicate';
    Icon = CopyCheck;
  } else if (isEntry) {
    containerStyle = 'bg-[#12161E] border-blue-600/80 text-blue-100';
    badgeStyle = 'bg-blue-950/80 text-blue-200 border-blue-500/40';
    badgeLabel = 'Entrypoint';
    Icon = Compass;
  }

  // Selected state overlay
  if (isSelected) {
    containerStyle += ' ring-2 ring-[#FF2E55] ring-offset-2 ring-offset-[#0F0F12] shadow-2xl shadow-red-500/30 scale-105';
  } else if (isHighlighted) {
    containerStyle += ' ring-1 ring-sky-400 shadow-md shadow-sky-500/20';
  }

  if (isDimmed && !isSelected && !isHighlighted) {
    containerStyle += ' opacity-35 grayscale-[50%]';
  }

  const incoming = node.incomingCount ?? 0;
  const outgoing = node.outgoingCount ?? 0;
  const findingCount = node.findingCount ?? 0;

  return (
    <div
      onClick={(e) => {
        e.stopPropagation();
        onSelect(node);
      }}
      className={`relative w-[210px] rounded-2xl p-3 border transition-all duration-200 cursor-pointer select-none font-sans ${containerStyle}`}
    >
      {/* Handles for edges */}
      <Handle
        type="target"
        position={Position.Top}
        className="!w-2 !h-2 !bg-slate-400 !border-none !-top-1"
      />
      <Handle
        type="source"
        position={Position.Bottom}
        className="!w-2 !h-2 !bg-[#FF2E55] !border-none !-bottom-1"
      />
      <Handle
        type="target"
        position={Position.Left}
        className="!w-2 !h-2 !bg-slate-400 !border-none !-left-1"
      />
      <Handle
        type="source"
        position={Position.Right}
        className="!w-2 !h-2 !bg-[#FF2E55] !border-none !-right-1"
      />

      {/* Top Header: Badge & Risk */}
      <div className="flex items-center justify-between gap-1 mb-2">
        <span className={`text-[9px] font-black uppercase tracking-wider px-2 py-0.5 rounded-md border flex items-center gap-1 ${badgeStyle}`}>
          <Icon className="w-2.5 h-2.5 shrink-0" />
          <span className="truncate max-w-[110px]">{badgeLabel}</span>
        </span>

        <span
          className={`text-[9px] font-mono font-bold px-1.5 py-0.5 rounded uppercase ${
            node.risk === 'high'
              ? 'bg-red-500/20 text-red-400 border border-red-500/30'
              : node.risk === 'medium'
              ? 'bg-amber-500/20 text-amber-400 border border-amber-500/30'
              : 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
          }`}
        >
          {node.risk}
        </span>
      </div>

      {/* Node Title & File Path */}
      <div className="space-y-0.5">
        <div className="flex items-center gap-1.5 font-mono text-xs font-bold text-white truncate">
          <FileCode className={`w-3.5 h-3.5 shrink-0 ${isCycle ? 'text-[#FF2E55]' : 'text-slate-400'}`} />
          <span className="truncate">{node.label}</span>
        </div>
        <p className="text-[10px] font-mono text-slate-400 truncate" title={node.filePath || node.label}>
          {node.filePath || node.label}
        </p>
      </div>

      {/* Footer Metrics */}
      <div className="mt-2.5 pt-2 border-t border-white/10 flex items-center justify-between text-[10px] font-mono text-slate-300">
        <div className="flex items-center gap-2">
          <span className="flex items-center gap-0.5 text-slate-400" title={`Incoming dependencies: ${incoming}`}>
            <ArrowDownLeft className="w-2.5 h-2.5 text-sky-400" />
            <span>{incoming}</span>
          </span>
          <span className="flex items-center gap-0.5 text-slate-400" title={`Outgoing dependencies: ${outgoing}`}>
            <ArrowUpRight className="w-2.5 h-2.5 text-amber-400" />
            <span>{outgoing}</span>
          </span>
        </div>

        {findingCount > 0 ? (
          <span className="px-1.5 py-0.2 rounded-full bg-[#FF2E55] text-white text-[9px] font-sans font-bold flex items-center gap-1">
            <span className="w-1.5 h-1.5 rounded-full bg-white animate-pulse" />
            {findingCount} finding{findingCount > 1 ? 's' : ''}
          </span>
        ) : (
          <span className="text-[9px] text-slate-500">0 findings</span>
        )}
      </div>
    </div>
  );
});

ModuleNode.displayName = 'ModuleNode';
