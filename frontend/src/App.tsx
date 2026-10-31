import React, { useState } from 'react';
import { AppLayout } from './components/layout/AppLayout';
import { Overview } from './components/dashboard/Overview';
import { FindingsPage } from './pages/Findings';
import { DependencyGraph } from './components/graph/DependencyGraph';
import { ContextualAI } from './components/ai/ContextualAI';
import { ReportsPage } from './pages/Reports';
import { CompetitorMatrix } from './components/matrix/CompetitorMatrix';

import {
  DEMO_REPOS,
  INITIAL_FINDINGS,
  GRAPH_NODES,
  GRAPH_EDGES,
  GRAPH_CYCLES,
  COMPETITOR_MATRIX,
  INITIAL_LOGS,
  DEFAULT_SUMMARY
} from './services/mockData';
import { Finding, GraphNode, TerminalLog, ChatMessage, AnalysisSummary, ReviewStatus } from './types';
import { api } from './services/api';

export default function App() {
  const [repoUrl, setRepoUrl] = useState('https://github.com/facebook/react');
  const [branch, setBranch] = useState('main');
  const [isScanning, setIsScanning] = useState(false);
  const [scanProgress, setScanProgress] = useState(0);
  const [scanStatus, setScanStatus] = useState('System Idle - Ready for Scan');

  const [activeTab, setActiveTab] = useState('overview'); // overview, findings, graph, ai, matrix
  const [findings, setFindings] = useState<Finding[]>(INITIAL_FINDINGS);
  const [activeFinding, setActiveFinding] = useState<Finding | null>(INITIAL_FINDINGS[0]);

  const [graphNodes] = useState<GraphNode[]>(GRAPH_NODES);
  const [graphEdges] = useState(GRAPH_EDGES);
  const [selectedGraphNode, setSelectedGraphNode] = useState<GraphNode | null>(GRAPH_NODES[1]);

  const [terminalLogs, setTerminalLogs] = useState<TerminalLog[]>(INITIAL_LOGS);
  const [summary, setSummary] = useState<AnalysisSummary>(DEFAULT_SUMMARY);

  // AI Chat State
  const [isAiTyping, setIsAiTyping] = useState(false);
  const [aiChat, setAiChat] = useState<ChatMessage[]>([
    {
      id: 'welcome',
      role: 'assistant',
      text: '🔥 Yo! I am your CodeImpact Contextual AI. Ask me about detected circular cycles, dynamic import blind spots, or safe verification steps before altering code.'
    }
  ]);

  // Trigger Live Scan
  const triggerLiveScan = async (customUrl?: string) => {
    const url = customUrl || repoUrl;
    setIsScanning(true);
    setScanProgress(5);
    setScanStatus('Initializing Git Repository Tree Retrieval...');

    const logMsg = (text: string, type: 'info' | 'warn' | 'error' | 'success' = 'info') => {
      setTerminalLogs((prev) => [
        ...prev,
        { id: Date.now() + Math.random(), type, text }
      ]);
    };

    logMsg(`[FETCH] Cloning repository head from ${url}...`, 'info');

    // Notify backend if available
    await api.startAnalysis(url, branch);

    const steps = [
      {
        p: 25,
        status: 'Parsing AST and running Knip export detection...',
        log: '[KNIP] Checked 412 export points. 14 unreferenced exports flagged.',
        type: 'warn' as const
      },
      {
        p: 50,
        status: 'Running jscpd AST clone detection engine...',
        log: '[JSCPD] Detected 6 structural clone blocks (>85% match).',
        type: 'warn' as const
      },
      {
        p: 75,
        status: 'Building Madge dependency cycle matrix...',
        log: '[MADGE] Found 1 CRITICAL circular dependency cycle in Auth/User modules!',
        type: 'error' as const
      },
      {
        p: 90,
        status: 'Synthesizing AI context & risk confidence weights...',
        log: '[AI] Generated verification checklist & dynamic blind spot warnings.',
        type: 'success' as const
      },
      {
        p: 100,
        status: 'Scan complete! Intelligence workspace updated.',
        log: '[COMPLETE] CodeImpact report ready.',
        type: 'success' as const
      }
    ];

    steps.forEach((st, idx) => {
      setTimeout(() => {
        setScanProgress(st.p);
        setScanStatus(st.status);
        logMsg(st.log, st.type);
        if (st.p === 100) {
          setTimeout(() => {
            setIsScanning(false);
            setSummary((prev) => ({ ...prev, repoUrl: url, branch }));
          }, 500);
        }
      }, (idx + 1) * 700);
    });
  };

  // AI Chat Handler
  const handleAiAsk = async (promptText: string) => {
    if (!promptText.trim()) return;

    const timeStr = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

    setAiChat((prev) => [
      ...prev,
      { id: String(Date.now()), role: 'user', text: promptText, timestamp: timeStr }
    ]);
    setIsAiTyping(true);

    try {
      const currentFinding = activeFinding || findings[0];
      const { text, source } = await api.explainFinding(currentFinding, promptText);

      setAiChat((prev) => [
        ...prev,
        {
          id: String(Date.now() + 1),
          role: 'assistant',
          text,
          groundingFindingId: currentFinding.id,
          groundingFile: currentFinding.file,
          source,
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
        }
      ]);
    } catch {
      setAiChat((prev) => [
        ...prev,
        {
          id: String(Date.now() + 1),
          role: 'assistant',
          text: 'Error processing evidence query. Please check active finding context.',
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
        }
      ]);
    } finally {
      setIsAiTyping(false);
    }
  };

  // Update Review Status Locally
  const handleUpdateReviewStatus = (findingId: string, status: ReviewStatus) => {
    setFindings((prev) =>
      prev.map((f) => (f.id === findingId ? { ...f, reviewStatus: status } : f))
    );
    if (activeFinding && activeFinding.id === findingId) {
      setActiveFinding((prev) => (prev ? { ...prev, reviewStatus: status } : null));
    }
  };

  // Handle consultation from finding card
  const handleConsultAIFromFinding = (f: Finding) => {
    setActiveFinding(f);
    setActiveTab('ai');
    handleAiAsk(`Please explain the risk and verification steps for ${f.id} (${f.title}) in ${f.file}`);
  };

  // Handle viewing finding in dependency graph
  const handleViewFindingInGraph = (f: Finding) => {
    const fileName = f.file.split('/').pop() || f.file;
    const matchingNode = graphNodes.find(
      (n) =>
        n.filePath === f.file ||
        f.file.includes(n.label) ||
        (n.label && n.label.toLowerCase() === fileName.toLowerCase())
    );
    if (matchingNode) {
      setSelectedGraphNode(matchingNode);
    }
    setActiveTab('graph');
  };

  // Handle selecting node in graph and inspecting finding
  const handleInspectLinkedFindingsFromNode = (node: GraphNode) => {
    const fileName = node.label.toLowerCase();
    const matchedFinding = findings.find(
      (f) =>
        f.file === node.filePath ||
        f.file.includes(node.label) ||
        f.file.toLowerCase().includes(fileName)
    );
    if (matchedFinding) {
      setActiveFinding(matchedFinding);
    }
    setActiveTab('findings');
  };

  return (
    <AppLayout
      activeTab={activeTab}
      setActiveTab={setActiveTab}
      onTriggerScan={() => triggerLiveScan()}
      isScanning={isScanning}
      activeRepo={repoUrl}
      branch={branch}
      summary={summary}
      findings={findings}
    >
      {/* 1. Overview Dashboard */}
      {activeTab === 'overview' && (
        <Overview
          repoUrl={repoUrl}
          setRepoUrl={setRepoUrl}
          isScanning={isScanning}
          scanProgress={scanProgress}
          scanStatus={scanStatus}
          onTriggerScan={(url) => triggerLiveScan(url)}
          demoRepos={DEMO_REPOS}
          summary={summary}
          terminalLogs={terminalLogs}
          onClearLogs={() => setTerminalLogs([])}
          onSelectTab={setActiveTab}
        />
      )}

      {/* 2. Findings Explorer Dedicated Page */}
      {activeTab === 'findings' && (
        <FindingsPage
          findings={findings}
          activeFinding={activeFinding}
          setActiveFinding={setActiveFinding}
          onUpdateReviewStatus={handleUpdateReviewStatus}
          onAskAI={handleConsultAIFromFinding}
          onViewInGraph={handleViewFindingInGraph}
          summary={summary}
        />
      )}

      {/* 3. Interactive Dependency Graph */}
      {activeTab === 'graph' && (
        <DependencyGraph
          nodes={graphNodes}
          edges={graphEdges}
          selectedNode={selectedGraphNode}
          setSelectedNode={setSelectedGraphNode}
          onInspectLinkedFindings={handleInspectLinkedFindingsFromNode}
          cycles={GRAPH_CYCLES}
        />
      )}

      {/* 4. Contextual AI Code Reviewer */}
      {activeTab === 'ai' && (
        <ContextualAI
          chatMessages={aiChat}
          isAiTyping={isAiTyping}
          onSendMessage={handleAiAsk}
          activeFinding={activeFinding}
          findings={findings}
          onSelectFinding={setActiveFinding}
          onClearChat={() => setAiChat([])}
          onNavigateToFindings={() => setActiveTab('findings')}
          onNavigateToGraph={(f) => handleViewFindingInGraph(f)}
          repoUrl={repoUrl}
          branch={branch}
        />
      )}

      {/* 5. Reports & Export Dashboard */}
      {activeTab === 'reports' && (
        <ReportsPage
          summary={summary}
          findings={findings}
          graphNodes={graphNodes}
          graphEdges={graphEdges}
          onNavigateToFindings={() => setActiveTab('findings')}
          onNavigateToGraph={() => setActiveTab('graph')}
        />
      )}

      {/* 6. Competitor Matrix */}
      {activeTab === 'matrix' && (
        <CompetitorMatrix competitors={COMPETITOR_MATRIX} />
      )}
    </AppLayout>
  );
}
