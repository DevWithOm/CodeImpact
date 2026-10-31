import React from 'react';
import { GitBranch, FileCode, AlertTriangle, Layers, Info, CheckCircle2 } from 'lucide-react';
import { GraphNode, GraphEdge } from '../../types';

interface DependencyGraphProps {
  nodes: GraphNode[];
  edges: GraphEdge[];
  selectedNode: GraphNode | null;
  setSelectedNode: (node: GraphNode) => void;
  onInspectLinkedFindings: (node: GraphNode) => void;
}

export const DependencyGraph: React.FC<DependencyGraphProps> = ({
  nodes,
  edges,
  selectedNode,
  setSelectedNode,
  onInspectLinkedFindings
}) => {
  return (
    <div className="space-y-6 animate-fadeIn">
      <div className="p-6 rounded-3xl bg-white border border-red-100 shadow-xl space-y-4">
        {/* Graph Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <h3 className="text-lg font-black text-slate-900 flex items-center gap-2">
              <GitBranch className="w-5 h-5 text-[#FF2E55]" />
              Interactive Module Dependency Neighborhood
            </h3>
            <p className="text-xs text-slate-500 font-medium">
              Visualizing file nodes, outgoing connections, and highlighted circular dependency cycles.
            </p>
          </div>

          <div className="flex items-center gap-2">
            <span className="px-3 py-1 rounded-full text-xs font-black text-white bg-[#FF2E55] shadow-xs flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-white animate-ping" />
              Circular Cycle Highlighted
            </span>
          </div>
        </div>

        {/* Node Canvas Area */}
        <div className="relative w-full h-[450px] rounded-2xl bg-[#0F0F12] p-6 overflow-hidden border border-red-900/40 shadow-inner flex items-center justify-center select-none">
          {/* Subtle Grid Background */}
          <div
            className="absolute inset-0 opacity-20 pointer-events-none"
            style={{
              backgroundImage: `radial-gradient(#FF2E55 1px, transparent 1px)`,
              backgroundSize: '24px 24px'
            }}
          />

          {/* SVG Connection Lines */}
          <svg className="absolute inset-0 w-full h-full pointer-events-none">
            <defs>
              <marker
                id="arrowhead-red"
                markerWidth="8"
                markerHeight="8"
                refX="7"
                refY="3.5"
                orient="auto"
              >
                <polygon points="0 0, 8 3.5, 0 7" fill="#FF2E55" />
              </marker>
              <marker
                id="arrowhead-gray"
                markerWidth="8"
                markerHeight="8"
                refX="7"
                refY="3.5"
                orient="auto"
              >
                <polygon points="0 0, 8 3.5, 0 7" fill="#64748b" />
              </marker>
            </defs>

            {edges.map((e, idx) => {
              const fromN = nodes.find((n) => n.id === e.from);
              const toN = nodes.find((n) => n.id === e.to);
              if (!fromN || !toN) return null;

              // Compute node center offsets
              const x1 = fromN.x + 65;
              const y1 = fromN.y + 20;
              const x2 = toN.x + 65;
              const y2 = toN.y + 20;

              return (
                <g key={idx}>
                  <line
                    x1={x1}
                    y1={y1}
                    x2={x2}
                    y2={y2}
                    stroke={e.isCycle ? '#FF2E55' : '#475569'}
                    strokeWidth={e.isCycle ? '2.5' : '1.5'}
                    strokeDasharray={e.isCycle ? '4 2' : 'none'}
                    className={e.isCycle ? 'animate-pulse' : 'opacity-60'}
                    markerEnd={e.isCycle ? 'url(#arrowhead-red)' : 'url(#arrowhead-gray)'}
                  />
                  {e.isCycle && (
                    <text
                      x={(x1 + x2) / 2}
                      y={(y1 + y2) / 2 - 8}
                      fill="#FF2E55"
                      fontSize="9"
                      fontWeight="bold"
                      textAnchor="middle"
                      className="font-mono"
                    >
                      CYCLE
                    </text>
                  )}
                </g>
              );
            })}
          </svg>

          {/* Interactive Nodes */}
          <div className="absolute inset-0 pointer-events-auto">
            {nodes.map((node) => {
              const isSelected = selectedNode?.id === node.id;
              const isCycle = node.type === 'cycle';
              const isHotspot = node.type === 'hotspot';

              return (
                <button
                  key={node.id}
                  onClick={() => setSelectedNode(node)}
                  style={{ left: `${node.x}px`, top: `${node.y}px` }}
                  className={`absolute px-3 py-2 rounded-xl text-xs font-mono font-bold transition-all transform hover:scale-110 shadow-lg flex items-center gap-2 border ${
                    isCycle
                      ? 'bg-[#FF2E55] text-white border-red-300 ring-4 ring-red-500/30'
                      : isHotspot
                      ? 'bg-rose-950 text-rose-200 border-rose-700'
                      : 'bg-slate-800 text-slate-200 border-slate-700 hover:border-slate-500'
                  } ${isSelected ? 'scale-110 ring-4 ring-white shadow-2xl z-20' : ''}`}
                >
                  <FileCode className="w-3.5 h-3.5 shrink-0" />
                  <span>{node.label}</span>
                  {node.findingCount ? (
                    <span className="w-4 h-4 rounded-full bg-white/20 text-[10px] flex items-center justify-center font-sans">
                      {node.findingCount}
                    </span>
                  ) : null}
                </button>
              );
            })}
          </div>

          {/* Canvas Legend */}
          <div className="absolute bottom-3 left-3 bg-[#18181D]/90 backdrop-blur-md px-3 py-1.5 rounded-xl border border-slate-800 text-[10px] text-slate-400 font-mono flex items-center gap-3">
            <span className="flex items-center gap-1">
              <span className="w-2.5 h-2.5 rounded-full bg-[#FF2E55]" /> Circular Cycle
            </span>
            <span className="flex items-center gap-1">
              <span className="w-2.5 h-2.5 rounded-full bg-rose-900 border border-rose-500" /> Hotspot
            </span>
            <span className="flex items-center gap-1">
              <span className="w-2.5 h-2.5 rounded-full bg-slate-700" /> Standard File
            </span>
          </div>
        </div>

        {/* Selected Node Details Bar */}
        {selectedNode && (
          <div className="p-4 rounded-2xl bg-slate-50 border border-slate-200 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
            <div>
              <span className="text-[10px] uppercase font-black text-slate-400 block">
                Selected File Node
              </span>
              <h4 className="text-sm font-bold text-slate-900 font-mono">
                {selectedNode.filePath || selectedNode.label}
              </h4>
            </div>

            <div className="flex items-center gap-3">
              <span
                className={`px-2.5 py-1 rounded-full text-xs font-black ${
                  selectedNode.risk === 'high'
                    ? 'bg-red-100 text-red-700'
                    : selectedNode.risk === 'medium'
                    ? 'bg-amber-100 text-amber-800'
                    : 'bg-slate-200 text-slate-700'
                }`}
              >
                Risk: {selectedNode.risk.toUpperCase()}
              </span>

              <button
                onClick={() => onInspectLinkedFindings(selectedNode)}
                className="px-3.5 py-1.5 rounded-xl bg-[#FF2E55] text-white text-xs font-bold hover:bg-red-600 shadow-md transition-colors"
              >
                Inspect Linked Findings
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
