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
  const [repoUrl, setRepoUrl] = useState('https://github.com/DevWithOm/DeadCode-Detective');
  const [branch, setBranch] = useState('main');
  const [isScanning, setIsScanning] = useState(false);
  const [scanProgress, setScanProgress] = useState(0);
  const [scanStatus, setScanStatus] = useState('System Idle - Ready for Scan');

  const pollingIntervalRef = React.useRef<ReturnType<typeof setInterval> | null>(null);

  React.useEffect(() => {
    return () => {
      if (pollingIntervalRef.current) {
        clearInterval(pollingIntervalRef.current);
      }
    };
  }, []);

  const [activeTab, setActiveTab] = useState('overview'); // overview, findings, graph, ai, matrix
  const [findings, setFindings] = useState<Finding[]>(INITIAL_FINDINGS);
  const [activeFinding, setActiveFinding] = useState<Finding | null>(INITIAL_FINDINGS[0]);

  const [analysisId, setAnalysisId] = useState<string>('');
  const [graphNodes, setGraphNodes] = useState<GraphNode[]>(GRAPH_NODES);
  const [graphEdges, setGraphEdges] = useState(GRAPH_EDGES);
  const [graphCycles, setGraphCycles] = useState(GRAPH_CYCLES);
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
    if (pollingIntervalRef.current) {
      clearInterval(pollingIntervalRef.current);
      pollingIntervalRef.current = null;
    }

    const url = customUrl || repoUrl;
    setIsScanning(true);
    setScanProgress(5);
    setScanStatus('Submitting analysis request to backend...');

    const logMsg = (text: string, type: 'info' | 'warn' | 'error' | 'success' = 'info') => {
      setTerminalLogs((prev) => [
        ...prev,
        { id: Date.now() + Math.random(), type, text }
      ]);
    };

    logMsg(`[INIT] Dispatching repository analysis request for ${url} (branch: ${branch})...`, 'info');

    try {
      const { analysisId: newId, status: initStatus } = await api.startAnalysis(url, branch);
      setAnalysisId(newId);
      logMsg(`[QUEUE] Analysis created: ${newId} (status: ${initStatus})`, 'success');

      let attempts = 0;
      let consecutiveNetworkErrors = 0;
      const maxAttempts = 90;

      const interval = setInterval(async () => {
        attempts++;
        try {
          const statusData = await api.getAnalysisStatus(newId);
          consecutiveNetworkErrors = 0; // reset on successful communication

          const currentStatus = statusData.status || 'running';
          const stage = (statusData.currentStage || 'analyzing').replace('_', ' ');
          const pct = Math.min(95, statusData.stageProgress || 10 + attempts * 8);

          setScanProgress(pct);
          setScanStatus(`Stage: ${stage.toUpperCase()} (${pct}%)`);

          if (currentStatus === 'completed' || currentStatus === 'partial') {
            if (pollingIntervalRef.current) {
              clearInterval(pollingIntervalRef.current);
              pollingIntervalRef.current = null;
            }
            logMsg(`[SUCCESS] Backend analysis completed (status: ${currentStatus.toUpperCase()})`, 'success');

            const [realFindings, realGraph, latestSummary] = await Promise.all([
              api.getFindings(newId),
              api.getDependencyGraph(newId),
              api.getAnalysisStatus(newId)
            ]);

            setFindings(realFindings);
            if (realFindings.length > 0) {
              setActiveFinding(realFindings[0]);
              logMsg(`[FINDINGS] Loaded ${realFindings.length} evidence-backed finding(s).`, 'info');
            } else {
              logMsg('[FINDINGS] No dead code or duplication clones flagged by analyzers.', 'info');
            }

            if (realGraph.nodes.length > 0) {
              setGraphNodes(realGraph.nodes);
              setGraphEdges(realGraph.edges);
              setGraphCycles(realGraph.cycles || []);
              logMsg(`[GRAPH] Rendered dependency topology (${realGraph.nodes.length} nodes, ${realGraph.edges.length} edges).`, 'info');
            }

            setSummary({
              ...latestSummary,
              repoUrl: url,
              branch
            });

            setScanProgress(100);
            setScanStatus('Analysis complete! Intelligence workspace updated.');
            setTimeout(() => setIsScanning(false), 500);
          } else if (currentStatus === 'failed') {
            if (pollingIntervalRef.current) {
              clearInterval(pollingIntervalRef.current);
              pollingIntervalRef.current = null;
            }
            const failureDetail = statusData.error || 'Pipeline execution failed.';
            logMsg(`[ERROR] Analysis failed: ${failureDetail}`, 'error');
            setScanStatus(`Analysis failed: ${failureDetail}`);
            setIsScanning(false);
          } else if (attempts >= maxAttempts) {
            if (pollingIntervalRef.current) {
              clearInterval(pollingIntervalRef.current);
              pollingIntervalRef.current = null;
            }
            logMsg('[TIMEOUT] Analysis polling timed out after 3 minutes.', 'warn');
            setScanStatus('Analysis timed out.');
            setIsScanning(false);
          }
        } catch (err: any) {
          consecutiveNetworkErrors++;
          console.warn(`[Polling Error ${consecutiveNetworkErrors}/5]`, err);
          if (consecutiveNetworkErrors >= 5) {
            if (pollingIntervalRef.current) {
              clearInterval(pollingIntervalRef.current);
              pollingIntervalRef.current = null;
            }
            logMsg('[ERROR] Lost connection to backend server at http://localhost:8000. Scan aborted.', 'error');
            setScanStatus('Backend server unreachable.');
            setIsScanning(false);
          }
        }
      }, 1500);

      pollingIntervalRef.current = interval;
    } catch (err: any) {
      logMsg(`[ERROR] Failed to start analysis: ${err?.message || err}`, 'error');
      setScanStatus(`Failed to start: ${err?.message || err}`);
      setIsScanning(false);
    }
  };

  // AI Chat Handler
  const handleAiAsk = async (promptText: string) => {
    if (!promptText.trim() || isAiTyping) return;

    const timeStr = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

    setAiChat((prev) => [
      ...prev,
      { id: String(Date.now()), role: 'user', text: promptText, timestamp: timeStr }
    ]);
    setIsAiTyping(true);

    try {
      const currentFinding = activeFinding || findings[0];
      const { text, source } = await api.explainFinding(currentFinding, promptText, analysisId);

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
          cycles={graphCycles}
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
          analysisId={analysisId}
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
