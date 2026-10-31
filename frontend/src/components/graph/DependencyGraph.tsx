import React, { useState, useMemo, useEffect, useRef } from 'react';
import {
  ReactFlow,
  ReactFlowProvider,
  Background,
  Controls,
  MiniMap,
  useNodesState,
  useEdgesState,
  MarkerType,
  BackgroundVariant,
  useReactFlow,
  Node,
  Edge
} from '@xyflow/react';
import {
  GitBranch,
  AlertTriangle,
  Maximize2
} from 'lucide-react';

import { GraphNode, GraphEdge, DependencyCycleInfo } from '../../types';
import { ModuleNode } from './ModuleNode';
import { ModuleDetailsPanel } from './ModuleDetailsPanel';
import { GraphToolbar } from './GraphToolbar';
import { GRAPH_CYCLES } from '../../services/mockData';

const nodeTypes = {
  module: ModuleNode
};

interface DependencyGraphProps {
  nodes: GraphNode[];
  edges: GraphEdge[];
  selectedNode: GraphNode | null;
  setSelectedNode: (node: GraphNode | null) => void;
  onInspectLinkedFindings: (node: GraphNode) => void;
  cycles?: DependencyCycleInfo[];
}

/**
 * Inner canvas component wrapped in ReactFlowProvider so useReactFlow hooks work smoothly.
 */
const FlowCanvas: React.FC<{
  nodes: GraphNode[];
  edges: GraphEdge[];
  selectedNode: GraphNode | null;
  setSelectedNode: (node: GraphNode | null) => void;
  onInspectLinkedFindings: (node: GraphNode) => void;
  cycles: DependencyCycleInfo[];
}> = ({
  nodes: initialNodes,
  edges: initialEdges,
  selectedNode,
  setSelectedNode,
  onInspectLinkedFindings,
  cycles
}) => {
  const { fitView, zoomIn, zoomOut, setCenter } = useReactFlow();

  const [searchQuery, setSearchQuery] = useState('');
  const [selectedFilter, setSelectedFilter] = useState('all');
  const [highlightCyclesOnly, setHighlightCyclesOnly] = useState(false);
  const [isFocusMode, setIsFocusMode] = useState(false);

  // Derive active cycle node IDs
  const cycleNodeIds = useMemo(() => {
    const ids = new Set<string>();
    cycles.forEach((c) => c.nodeIds.forEach((id) => ids.add(id)));
    initialNodes.filter((n) => n.type === 'cycle').forEach((n) => ids.add(n.id));
    initialEdges.filter((e) => e.isCycle).forEach((e) => {
      ids.add(e.from);
      ids.add(e.to);
    });
    return ids;
  }, [cycles, initialNodes, initialEdges]);

  // Find incoming and outgoing neighbors for the selected node
  const { incomingNeighbors, outgoingNeighbors, neighborIds } = useMemo(() => {
    if (!selectedNode) {
      return { incomingNeighbors: [], outgoingNeighbors: [], neighborIds: new Set<string>() };
    }

    const inList: GraphNode[] = [];
    const outList: GraphNode[] = [];
    const nIds = new Set<string>([selectedNode.id]);

    initialEdges.forEach((e) => {
      if (e.to === selectedNode.id) {
        const sourceNode = initialNodes.find((n) => n.id === e.from);
        if (sourceNode) {
          inList.push(sourceNode);
          nIds.add(sourceNode.id);
        }
      }
      if (e.from === selectedNode.id) {
        const targetNode = initialNodes.find((n) => n.id === e.to);
        if (targetNode) {
          outList.push(targetNode);
          nIds.add(targetNode.id);
        }
      }
    });

    return { incomingNeighbors: inList, outgoingNeighbors: outList, neighborIds: nIds };
  }, [selectedNode, initialNodes, initialEdges]);

  // Filter nodes based on search, filter chips, cycle mode, and focus mode
  const visibleNodes = useMemo(() => {
    return initialNodes.filter((node) => {
      // Focus mode: only selected node + its 1-hop neighbors
      if (isFocusMode && selectedNode) {
        if (!neighborIds.has(node.id)) return false;
      }

      // Cycles only toggle
      if (highlightCyclesOnly && !cycleNodeIds.has(node.id)) {
        return false;
      }

      // Category filter chip
      if (selectedFilter !== 'all') {
        if (selectedFilter === 'cycle' && !cycleNodeIds.has(node.id)) return false;
        if (selectedFilter === 'hotspot' && node.type !== 'hotspot') return false;
        if (selectedFilter === 'unused' && node.type !== 'unused') return false;
        if (selectedFilter === 'entry' && node.type !== 'entry') return false;
      }

      // Search query
      if (searchQuery.trim()) {
        const query = searchQuery.toLowerCase().trim();
        const matchLabel = node.label.toLowerCase().includes(query);
        const matchPath = (node.filePath || '').toLowerCase().includes(query);
        if (!matchLabel && !matchPath) return false;
      }

      return true;
    });
  }, [initialNodes, isFocusMode, selectedNode, neighborIds, highlightCyclesOnly, cycleNodeIds, selectedFilter, searchQuery]);

  // Convert to React Flow Nodes
  const flowNodes: Node[] = useMemo(() => {
    return visibleNodes.map((node) => {
      const isCycle = cycleNodeIds.has(node.id);
      const isSelected = selectedNode?.id === node.id;
      const isHighlighted = neighborIds.has(node.id) && !isSelected;
      const isDimmed = selectedNode !== null && !neighborIds.has(node.id);

      return {
        id: node.id,
        type: 'module',
        position: { x: node.x, y: node.y },
        data: {
          node,
          isCycle,
          isHotspot: node.type === 'hotspot',
          isUnused: node.type === 'unused',
          isDuplicate: node.type === 'duplicate',
          isEntry: node.type === 'entry',
          isSelected,
          isHighlighted,
          isDimmed,
          onSelect: (n: GraphNode) => setSelectedNode(n)
        }
      };
    });
  }, [visibleNodes, selectedNode, neighborIds, cycleNodeIds, setSelectedNode]);

  // Convert to React Flow Edges
  const flowEdges: Edge[] = useMemo(() => {
    const visibleIds = new Set(visibleNodes.map((n) => n.id));

    return initialEdges
      .filter((e) => visibleIds.has(e.from) && visibleIds.has(e.to))
      .map((e, idx) => {
        const edgeId = e.id || `e-${e.from}-${e.to}-${idx}`;
        const isCycleEdge = Boolean(e.isCycle);
        const isConnectedToSelected =
          selectedNode && (e.from === selectedNode.id || e.to === selectedNode.id);

        let strokeColor = isCycleEdge ? '#FF2E55' : '#475569';
        let strokeWidth = isCycleEdge ? 2.5 : 1.5;
        let animated = isCycleEdge;

        if (isConnectedToSelected) {
          strokeColor = e.to === selectedNode.id ? '#38BDF8' : '#F59E0B';
          strokeWidth = 2.5;
          animated = true;
        }

        return {
          id: edgeId,
          source: e.from,
          target: e.to,
          animated,
          style: {
            stroke: strokeColor,
            strokeWidth,
            strokeDasharray: isCycleEdge ? '5 3' : undefined,
            opacity: selectedNode && !isConnectedToSelected && !isCycleEdge ? 0.25 : 0.85
          },
          markerEnd: {
            type: MarkerType.ArrowClosed,
            color: strokeColor,
            width: 14,
            height: 14
          },
          label: isCycleEdge ? 'CYCLE' : undefined,
          labelStyle: {
            fill: '#FF2E55',
            fontWeight: 800,
            fontSize: 9,
            fontFamily: 'monospace'
          },
          labelBgStyle: {
            fill: '#181115',
            fillOpacity: 0.9,
            rx: 4,
            ry: 4
          }
        };
      });
  }, [initialEdges, visibleNodes, selectedNode]);

  const [nodes, setNodes, onNodesChange] = useNodesState(flowNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(flowEdges);

  // Sync state when dependencies update
  useEffect(() => {
    setNodes(flowNodes);
  }, [flowNodes, setNodes]);

  useEffect(() => {
    setEdges(flowEdges);
  }, [flowEdges, setEdges]);

  // Initial fit view on mount
  const hasMounted = useRef(false);
  useEffect(() => {
    if (!hasMounted.current && initialNodes.length > 0) {
      setTimeout(() => fitView({ padding: 0.2, duration: 400 }), 150);
      hasMounted.current = true;
    }
  }, [fitView, initialNodes]);

  // Auto-pan to selected node if selected outside
  useEffect(() => {
    if (selectedNode) {
      setCenter(selectedNode.x + 105, selectedNode.y + 45, { zoom: 1.15, duration: 500 });
    }
  }, [selectedNode, setCenter]);

  // Focus specific cycle
  const handleFocusCycle = (cycle: DependencyCycleInfo) => {
    const cycleNodes = initialNodes.filter((n) => cycle.nodeIds.includes(n.id));
    if (cycleNodes.length > 0) {
      setSelectedNode(cycleNodes[0]);
      setHighlightCyclesOnly(true);
      setTimeout(() => fitView({ padding: 0.3, duration: 500 }), 100);
    }
  };

  return (
    <div className="space-y-4 animate-fadeIn">
      {/* 1. Header Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 p-6 rounded-3xl bg-white border border-red-100 shadow-xl">
        <div className="space-y-1">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-[10px] font-black uppercase tracking-widest px-2.5 py-0.5 rounded-full bg-red-50 text-[#FF2E55] border border-red-200">
              Interactive Module Dependency Architecture
            </span>
            <span className="text-[10px] font-mono text-slate-500 bg-slate-100 px-2 py-0.5 rounded">
              Engine: Madge AST + React Flow
            </span>
          </div>

          <h2 className="text-xl font-black text-slate-900 flex items-center gap-2">
            <GitBranch className="w-5 h-5 text-[#FF2E55]" />
            Codebase Dependency Graph & Cycle Inspector
          </h2>

          <p className="text-xs text-slate-600 font-medium">
            Explore compiled import relationships, trace circular dependency loops, and inspect caller fan-in blast radius before refactoring.
          </p>
        </div>

        {/* Status Pill */}
        <div className="flex items-center gap-2 shrink-0">
          <div className="px-3.5 py-1.5 rounded-2xl bg-[#0F0F12] text-white text-xs font-mono font-bold flex items-center gap-2 border border-red-900/40 shadow-xs">
            <span className="w-2 h-2 rounded-full bg-[#FF2E55] animate-ping" />
            <span>{cycles.length} Cycle{cycles.length !== 1 ? 's' : ''} Detected</span>
          </div>
        </div>
      </div>

      {/* 2. Circular Dependency Alert Banner */}
      {cycles.length > 0 && (
        <div className="p-4 rounded-2xl bg-gradient-to-r from-red-50 via-rose-50 to-amber-50 border border-red-200 shadow-xs flex flex-col md:flex-row items-start md:items-center justify-between gap-3">
          <div className="flex items-start gap-3">
            <div className="w-9 h-9 rounded-xl bg-[#FF2E55] text-white flex items-center justify-center shrink-0 shadow-md shadow-red-500/30">
              <AlertTriangle className="w-5 h-5" />
            </div>
            <div>
              <h4 className="text-xs font-black uppercase text-red-950 flex items-center gap-1.5">
                <span>Circular Dependency Alert: {cycles[0].name}</span>
              </h4>
              <p className="text-xs text-red-900/90 font-medium mt-0.5">
                {cycles[0].description} Mutual evaluation causes undefined bindings and runtime memory leaks.
              </p>
            </div>
          </div>

          <button
            onClick={() => handleFocusCycle(cycles[0])}
            className="px-3.5 py-1.5 rounded-xl bg-[#FF2E55] hover:bg-red-600 text-white text-xs font-extrabold shadow-md shadow-red-500/20 flex items-center gap-1.5 shrink-0 transition-colors"
          >
            <Maximize2 className="w-3.5 h-3.5" />
            <span>Focus Active Cycle</span>
          </button>
        </div>
      )}

      {/* 3. Controls & Filter Toolbar */}
      <GraphToolbar
        searchQuery={searchQuery}
        onSearchChange={setSearchQuery}
        selectedFilter={selectedFilter}
        onFilterChange={setSelectedFilter}
        highlightCyclesOnly={highlightCyclesOnly}
        onToggleHighlightCycles={() => setHighlightCyclesOnly((prev) => !prev)}
        onZoomIn={() => zoomIn({ duration: 300 })}
        onZoomOut={() => zoomOut({ duration: 300 })}
        onFitView={() => fitView({ padding: 0.2, duration: 400 })}
        onResetSelection={() => {
          setSelectedNode(null);
          setIsFocusMode(false);
          setHighlightCyclesOnly(false);
          setSelectedFilter('all');
          setSearchQuery('');
          fitView({ padding: 0.2, duration: 400 });
        }}
        matchingCount={visibleNodes.length}
        totalCount={initialNodes.length}
        cycleCount={cycleNodeIds.size}
      />

      {/* 4. Canvas + Details Grid Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-5 items-start">
        {/* React Flow Canvas (Left / Main) */}
        <div className="lg:col-span-8 relative h-[560px] rounded-3xl bg-[#0F0F12] border border-red-900/40 shadow-2xl overflow-hidden">
          {/* Subtle Red Dot Grid */}
          <Background
            color="#FF2E55"
            variant={BackgroundVariant.Dots}
            gap={24}
            size={1}
            style={{ opacity: 0.18 }}
          />

          <ReactFlow
            nodes={nodes}
            edges={edges}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            nodeTypes={nodeTypes}
            onPaneClick={() => setSelectedNode(null)}
            fitView
            minZoom={0.2}
            maxZoom={2}
            nodesDraggable={true}
            nodesConnectable={false}
            elementsSelectable={true}
            panOnDrag={true}
            zoomOnScroll={true}
          >
            {/* Standard React Flow Controls */}
            <Controls
              showInteractive={false}
              className="!bg-[#18181D] !border-slate-800 !rounded-xl !shadow-xl !overflow-hidden [&>button]:!bg-[#18181D] [&>button]:!border-slate-800 [&>button]:!text-slate-300 hover:[&>button]:!bg-[#22222A]"
            />

            {/* Canvas MiniMap */}
            <MiniMap
              nodeStrokeColor="#FF2E55"
              nodeColor="#1F1F28"
              nodeBorderRadius={6}
              maskColor="rgba(15, 15, 18, 0.75)"
              className="!bg-[#121216] !border !border-slate-800 !rounded-xl !overflow-hidden"
            />
          </ReactFlow>

          {/* Canvas Bottom Legend */}
          <div className="absolute bottom-3 left-3 bg-[#18181D]/90 backdrop-blur-md px-3 py-1.5 rounded-xl border border-slate-800 text-[10px] text-slate-300 font-mono flex items-center gap-3 shadow-lg pointer-events-none">
            <span className="flex items-center gap-1.5">
              <span className="w-2.5 h-2.5 rounded-full bg-[#FF2E55] ring-2 ring-red-500/40 animate-pulse" />
              <span>Circular Cycle</span>
            </span>
            <span className="flex items-center gap-1.5">
              <span className="w-2.5 h-2.5 rounded-full bg-rose-700 border border-rose-500" />
              <span>Hotspot</span>
            </span>
            <span className="flex items-center gap-1.5">
              <span className="w-2.5 h-2.5 rounded-full bg-amber-500 border border-dashed border-amber-300" />
              <span>Unused</span>
            </span>
            <span className="flex items-center gap-1.5">
              <span className="w-2.5 h-2.5 rounded-full bg-slate-700" />
              <span>Standard</span>
            </span>
          </div>

          {/* Empty search fallback */}
          {visibleNodes.length === 0 && (
            <div className="absolute inset-0 flex flex-col items-center justify-center p-6 text-center bg-[#0F0F12]/90 backdrop-blur-xs z-30">
              <div className="w-12 h-12 rounded-2xl bg-slate-800/80 text-slate-400 flex items-center justify-center mb-3">
                <GitBranch className="w-6 h-6" />
              </div>
              <h4 className="text-sm font-bold text-white mb-1">No Modules Match Your Filter</h4>
              <p className="text-xs text-slate-400 max-w-xs mb-4">
                No dependency nodes match "{searchQuery || selectedFilter}". Clear your filter to view full repository architecture.
              </p>
              <button
                onClick={() => {
                  setSearchQuery('');
                  setSelectedFilter('all');
                  setHighlightCyclesOnly(false);
                  setIsFocusMode(false);
                }}
                className="px-3.5 py-1.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-white text-xs font-bold border border-slate-700 transition-colors"
              >
                Reset Filters
              </button>
            </div>
          )}
        </div>

        {/* Selected Module Details Panel (Right Column) */}
        <div className="lg:col-span-4">
          <ModuleDetailsPanel
            node={selectedNode}
            nodes={initialNodes}
            incomingNodes={incomingNeighbors}
            outgoingNodes={outgoingNeighbors}
            isFocusMode={isFocusMode}
            onToggleFocusMode={() => setIsFocusMode((prev) => !prev)}
            onSelectNode={(n) => setSelectedNode(n)}
            onClose={() => {
              setSelectedNode(null);
              setIsFocusMode(false);
            }}
            onInspectLinkedFindings={onInspectLinkedFindings}
          />
        </div>
      </div>
    </div>
  );
};

/**
 * Main DependencyGraph exported component with ReactFlowProvider.
 */
export const DependencyGraph: React.FC<DependencyGraphProps> = ({
  nodes,
  edges,
  selectedNode,
  setSelectedNode,
  onInspectLinkedFindings,
  cycles = GRAPH_CYCLES
}) => {
  return (
    <ReactFlowProvider>
      <FlowCanvas
        nodes={nodes}
        edges={edges}
        selectedNode={selectedNode}
        setSelectedNode={setSelectedNode}
        onInspectLinkedFindings={onInspectLinkedFindings}
        cycles={cycles}
      />
    </ReactFlowProvider>
  );
};