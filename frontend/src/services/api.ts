import { Finding, GraphNode, GraphEdge, DependencyCycleInfo, AnalysisSummary, ChatMessage, ReportCustomization, FindingCategory, FindingSeverity, ImpactRiskType } from '../types';
import { INITIAL_FINDINGS, GRAPH_NODES, GRAPH_EDGES, GRAPH_CYCLES, DEFAULT_SUMMARY } from './mockData';

const BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const inFlightExplains = new Map<string, Promise<{ text: string; source: 'backend-gemini' | 'grounded-engine' }>>();

function mapBackendCategory(cat: string): FindingCategory {
  const c = (cat || '').toLowerCase();
  if (c.includes('duplicate')) return 'Duplicate code';
  if (c.includes('cycle') || c.includes('circular')) return 'Circular dependencies';
  if (c.includes('unused_file')) return 'Potentially unused files';
  if (c.includes('hotspot')) return 'High-risk hotspots';
  return 'Potentially unused code';
}

function mapSeverity(sev: string): FindingSeverity {
  const s = (sev || 'medium').toLowerCase();
  if (s === 'critical') return 'Critical';
  if (s === 'high') return 'High';
  if (s === 'low') return 'Low';
  return 'Medium';
}

function mapImpactRiskType(r: string): ImpactRiskType {
  const val = (r || 'medium').toLowerCase();
  if (val.includes('critical')) return 'critical';
  if (val.includes('high')) return 'high';
  if (val.includes('low')) return 'low';
  return 'medium';
}

/**
 * Service layer for CodeImpact API interactions.
 * Connects to the backend REST API; gracefully falls back to mock intelligence
 * if the backend is unreachable.
 */
export const api = {
  /**
   * Triggers a new repository analysis.
   */
  async startAnalysis(repoUrl: string, branch = 'main'): Promise<{ analysisId: string; status: string }> {
    try {
      const res = await fetch(`${BASE_URL}/api/repositories/analyse`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ repository_url: repoUrl, branch })
      });
      if (res.ok) {
        const data = await res.json();
        return {
          analysisId: data.analysis_id || data.analysisId || `an_${Date.now()}`,
          status: data.status || 'queued'
        };
      }
    } catch (err) {
      console.warn('[CodeImpact API] Failed to trigger backend analysis, falling back to local simulation:', err);
    }

    return {
      analysisId: `an_${Date.now()}`,
      status: 'queued'
    };
  },

  /**
   * Retrieves status and summary metrics.
   */
  async getAnalysisStatus(analysisId: string): Promise<AnalysisSummary & { status?: string; currentStage?: string; stageProgress?: number; error?: string | null }> {
    try {
      const res = await fetch(`${BASE_URL}/api/analyses/${analysisId}`);
      if (res.ok) {
        const data = await res.json();
        const m = data.metrics || {};
        const total = m.total_findings ?? 0;
        const health = total === 0 ? 'A+' : total < 5 ? 'A-' : total < 10 ? 'B+' : total < 20 ? 'B' : 'C';

        return {
          repoUrl: data.repository_url || '',
          branch: data.branch || 'main',
          analyzedFiles: m.files_analyzed || m.total_files || 10,
          totalFindings: total,
          potentiallyUnusedCount: m.potentially_unused ?? 0,
          duplicationClonesCount: m.duplicate_code ?? 0,
          circularCyclesCount: m.circular_dependencies ?? 0,
          hotspotRiskIndex: m.high_risk_findings ? Math.min(100, m.high_risk_findings * 25) : 0,
          healthScore: health,
          status: data.status,
          currentStage: data.current_stage,
          stageProgress: data.stage_progress,
          error: data.error
        };
      }
    } catch (err) {
      console.warn(`[CodeImpact API] Status check failed for ${analysisId}:`, err);
    }

    return DEFAULT_SUMMARY;
  },

  /**
   * Retrieves normalized findings.
   */
  async getFindings(analysisId: string): Promise<Finding[]> {
    try {
      const res = await fetch(`${BASE_URL}/api/analyses/${analysisId}/findings`);
      if (res.ok) {
        const data = await res.json();
        const rawItems = Array.isArray(data) ? data : data.items || [];
        if (rawItems.length > 0) {
          return rawItems.map((item: any, idx: number): Finding => {
            const id = item.finding_id || item.id || `f_${idx + 1}`;
            const file = item.file_path || item.file || 'unknown';
            const cat = mapBackendCategory(item.category);
            const sev = mapSeverity(item.severity);
            const risk = item.review_risk || 'Medium';
            const riskType = mapImpactRiskType(risk);
            const conf = typeof item.confidence === 'number'
              ? (item.confidence <= 1.0 ? Math.round(item.confidence * 100) : Math.round(item.confidence))
              : 85;
            const lines = item.line_number
              ? (item.line_end && item.line_end !== item.line_number ? `L${item.line_number}-L${item.line_end}` : `L${item.line_number}`)
              : 'Entire file';

            const evList = item.evidence || [];
            const primaryEv = evList[0] || {};
            const desc = primaryEv.details || primaryEv.message || primaryEv.description || `${cat} candidate identified by ${item.analyzer || 'static analyzer'}.`;

            const imp = item.impact || {};
            const incoming = imp.direct_dependents_count ?? 0;
            const outgoing = 0;
            const affectedMods = imp.direct_dependents || [];
            const affectedTests = imp.test_suites || [];

            return {
              id,
              category: cat,
              title: item.symbol_name ? `${item.symbol_name} in ${file.split('/').pop()}` : `${cat}: ${file}`,
              file,
              lines,
              severity: sev,
              confidence: conf,
              impactScore: imp.impact_score ?? (riskType === 'high' ? 85 : riskType === 'medium' ? 50 : 20),
              impactRisk: `${risk.charAt(0).toUpperCase() + risk.slice(1)} Risk`,
              impactRiskType: riskType,
              analyzer: (item.analyzer || 'Static Analysis').toUpperCase(),
              description: desc,
              codeSnippet: primaryEv.snippet || `// Location: ${file} ${lines}\n// Symbol: ${item.symbol_name || 'N/A'}`,
              dependencyContext: {
                incoming,
                outgoing,
                affectedModules: affectedMods,
                affectedTests: affectedTests
              },
              testImpactContext: {
                testFiles: affectedTests,
                whyAffected: imp.why_affected || (affectedTests.length > 0 ? 'Direct imports in test suites.' : 'No direct unit tests mapped.')
              },
              verificationSteps: [
                `Verify if ${item.symbol_name || file} is invoked dynamically or via string reflection.`,
                'Run automated unit test suites targeting importing caller modules.',
                'Check Git blame/history to understand original architectural intent before refactoring.'
              ],
              reviewStatus: 'Pending Review',
              runtimeCaveat: 'Static analysis cannot prove dynamic runtime reachability.'
            };
          });
        }
      }
    } catch (err) {
      console.warn(`[CodeImpact API] Findings fetch failed for ${analysisId}:`, err);
    }

    return INITIAL_FINDINGS;
  },

  /**
   * Retrieves dependency graph nodes, edges, and cycle chains.
   */
  async getDependencyGraph(analysisId: string): Promise<{ nodes: GraphNode[]; edges: GraphEdge[]; cycles?: DependencyCycleInfo[] }> {
    try {
      const res = await fetch(`${BASE_URL}/api/analyses/${analysisId}/graph`);
      if (res.ok) {
        const data = await res.json();
        const rawNodes = data.nodes || [];
        const rawEdges = data.edges || [];
        const rawCycles = data.cycles || [];

        if (rawNodes.length > 0) {
          const nodes: GraphNode[] = rawNodes.map((n: any, idx: number) => {
            const id = n.id || n.path;
            const hasCycles = Boolean(n.has_cycles);
            const isEntry = Boolean(n.is_entry_point);
            const inDeg = n.in_degree ?? n.dependents_count ?? 0;
            const outDeg = n.out_degree ?? n.dependencies_count ?? 0;

            return {
              id,
              label: n.label || id.split('/').pop() || id,
              filePath: n.path || id,
              type: hasCycles ? 'cycle' : isEntry ? 'entry' : 'standard',
              risk: (n.risk_level || 'low').toLowerCase() as any,
              x: 120 + (idx % 4) * 240,
              y: 80 + Math.floor(idx / 4) * 160,
              val: inDeg + 1,
              incomingCount: inDeg,
              outgoingCount: outDeg,
              affectedModules: [],
              affectedTests: []
            };
          });

          const edges: GraphEdge[] = rawEdges.map((e: any, idx: number) => ({
            id: `e_${e.source}_${e.target}_${idx}`,
            from: e.source,
            to: e.target,
            source: e.source,
            target: e.target,
            isCycle: Boolean(e.is_cycle)
          }));

          const cycles: DependencyCycleInfo[] = rawCycles.map((c: any, idx: number) => {
            const arr = Array.isArray(c) ? c : c.nodes || [];
            return {
              id: `cycle-${idx + 1}`,
              name: arr.map((f: string) => f.split('/').pop()).join(' ⇄ ') || `Cycle ${idx + 1}`,
              nodeIds: arr,
              description: 'Circular import dependency chain identified by Madge AST analysis.',
              severity: 'High'
            };
          });

          return { nodes, edges, cycles };
        }
      }
    } catch (err) {
      console.warn(`[CodeImpact API] Graph fetch failed for ${analysisId}:`, err);
    }

    return {
      nodes: GRAPH_NODES,
      edges: GRAPH_EDGES,
      cycles: GRAPH_CYCLES
    };
  },

  /**
   * Downloads server-generated Markdown audit report (Phase 5 endpoint).
   */
  async downloadServerReport(analysisId: string): Promise<boolean> {
    try {
      const res = await fetch(`${BASE_URL}/api/analyses/${analysisId}/report`);
      if (res.ok) {
        const blob = await res.blob();
        let filename = `CodeImpact_Report_${analysisId}.md`;
        const disp = res.headers.get('content-disposition');
        if (disp && disp.includes('filename=')) {
          const match = disp.match(/filename="?([^"]+)"?/);
          if (match && match[1]) filename = match[1];
        }

        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        a.remove();
        window.URL.revokeObjectURL(url);
        return true;
      }
    } catch (err) {
      console.warn('[CodeImpact API] Download server report failed:', err);
    }
    return false;
  },

  /**
   * Generates grounded AI explanation adhering to CodeImpact reliability guidelines.
   * Checks the backend Gemini endpoint if available; otherwise computes evidence-grounded
   * response based on active finding AST data, dependency fans, test mapping, and verification steps.
   */
  async explainFinding(
    finding: Finding,
    customPrompt?: string,
    analysisId = 'demo-analysis'
  ): Promise<{ text: string; source: 'backend-gemini' | 'grounded-engine' }> {
    const dedupKey = `${analysisId || ''}:${finding?.id || ''}:${customPrompt || ''}`;
    if (inFlightExplains.has(dedupKey)) {
      return inFlightExplains.get(dedupKey)!;
    }

    const runExplain = async (): Promise<{ text: string; source: 'backend-gemini' | 'grounded-engine' }> => {
      const q = (customPrompt || '').toLowerCase().trim();

      // 1. Attempt Backend API if available with valid analysis and finding IDs
      const hasRealAnalysis = analysisId && analysisId !== 'demo-analysis' && analysisId.trim().length > 0;
      if (hasRealAnalysis && finding?.id) {
        try {
          const payload: { finding_id: string; prompt?: string } = {
            finding_id: finding.id
          };
          if (customPrompt && customPrompt.trim()) {
            payload.prompt = customPrompt.trim();
          }

          const res = await fetch(`${BASE_URL}/api/analyses/${encodeURIComponent(analysisId)}/explain`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
          });

          if (res.ok) {
            const data = await res.json();
            const summaryText = data.summary || data.explanation;
            if (summaryText) {
              const whyItMatters = data.why_it_matters ? `\n\n**Why It Matters:**\n${data.why_it_matters}` : '';
              const rawRisks = data.false_positive_scenarios || data.potential_risks || [];
              const risksText = rawRisks.length > 0 ? `\n\n**Potential False Positive Scenarios / Risks:**\n${rawRisks.map((r: string) => `- ${r}`).join('\n')}` : '';
              const rawSteps = data.verification_steps || [];
              const stepsText = rawSteps.length > 0 ? `\n\n**Verification Steps:**\n${rawSteps.map((v: string, i: number) => `${i + 1}. ${v}`).join('\n')}` : '';
              const actionText = data.suggested_action ? `\n\n**Suggested Action:**\n${data.suggested_action}` : '';
              const rawLimits = (data.limitations || data.uncertainty_notes || []).join(' ');
              const limitsText = rawLimits ? `\n\n> [!CAUTION]\n> **Limitations**: ${rawLimits}` : '';

              const formatted = `### AI Assessment: ${finding.title}\n\n${summaryText}${whyItMatters}${risksText}${stepsText}${actionText}${limitsText}`;
              return { text: formatted, source: 'backend-gemini' as const };
            }
          } else if (res.status === 422) {
            const errData = await res.json().catch(() => ({}));
            console.warn('[CodeImpact API] Explanation validation error (422):', errData);
          }
        } catch (fetchErr) {
          console.warn('[CodeImpact API] Explain endpoint network error, using grounded engine:', fetchErr);
        }
      }

      // 2. Grounded Client-Side Engine Fallback (Deterministic, Evidence-First)
      const fileName = finding.file.split('/').pop() || finding.file;
      const incomingCount = finding.dependencyContext.incoming;
      const outgoingCount = finding.dependencyContext.outgoing;
      const affectedModules = finding.dependencyContext.affectedModules;
      const tests = finding.testImpactContext?.testFiles || finding.dependencyContext.affectedTests;

      // A. "Is it safe to delete?"
      if (q.includes('safe to delete') || q.includes('can i delete') || q.includes('remove safely')) {
        const isLowFanIn = incomingCount === 0;
        return {
          source: 'grounded-engine' as const,
          text: `### ⚠️ Safety Assessment for \`${fileName}\`\n\n**Verdict**: **No static analysis tool can unconditionally guarantee that code is safe to delete.**\n\n#### 1. Available Evidence\n- **Analyzer**: ${finding.analyzer} (Confidence: **${finding.confidence}%**)\n- **Category**: ${finding.category}\n- **Incoming Dependencies**: ${incomingCount} static references detected.\n- **Outgoing Imports**: ${outgoingCount} modules imported.\n- **Associated Tests**: ${tests.length > 0 ? tests.join(', ') : 'None mapped directly.'}\n\n#### 2. Risk Indicators\n${
            isLowFanIn
              ? '- **Low Static Fan-In**: No other tracked files directly import this file in the static AST scan.\n- **Blind Spot Warning**: Framework routing (Next.js/React Router), dynamic `import()`, or Webpack chunk configurations might invoke this component dynamically at runtime.'
              : `- **Active Dependants Detected**: Flagged code has **${incomingCount} incoming callers** (${affectedModules.slice(0, 3).join(', ')}${affectedModules.length > 3 ? '...' : ''}). Deleting it will cause compiler/runtime crashes.`
          }\n\n#### 3. Recommended Verification Steps\n1. Search for dynamic references or string keys (e.g. \`React.lazy(() => import(...))\`).\n2. Run automated test suites: ${tests.length > 0 ? `\`${tests.join(', ')}\`` : 'No direct unit tests detected; run full regression test suite.'}\n3. If this is a library package, check whether this export is part of the public interface before refactoring.`
        };
      }

      // B. "What could break if I remove this code?"
      if (q.includes('what could break') || q.includes('break') || q.includes('impact') || q.includes('consequences')) {
        return {
          source: 'grounded-engine' as const,
          text: `### 💥 Blast Radius & Impact Analysis: \`${fileName}\`\n\n- **Finding ID**: \`${finding.id}\`\n- **Direct Callers**: **${incomingCount}** modules depend on this file.\n- **Downstream Consumers**: ${
            affectedModules.length > 0
              ? affectedModules.map((m) => `\`${m}\``).join(', ')
              : 'None detected via static import analysis.'
          }\n- **Impact Risk Rating**: **${finding.impactRisk}** (${finding.impactScore}/100)\n\n#### Potential Runtime Failures\n- **Import Resolution Errors**: If any consumer attempts to import this module, bundling or execution will fail with \`Cannot find module\` or \`Module not found\`.\n- **Export Reference Breakage**: If exported functions are expected by third-party packages, external consumers will encounter runtime crashes.\n\n#### Mandatory Pre-Removal Checklist\n1. Deprecate the symbol first (mark with \`@deprecated\`) before outright deletion.\n2. Run regression tests in all downstream caller modules: ${affectedModules.slice(0, 4).join(', ') || 'N/A'}.`
        };
      }

      // C. "Why was this code flagged?"
      if (q.includes('why was this') || q.includes('flagged') || q.includes('reason') || q.includes('why is this')) {
        return {
          source: 'grounded-engine' as const,
          text: `### 🔬 Static Analysis Audit Trail: \`${fileName}\`\n\n- **Reporting Tool**: **${finding.analyzer}**\n- **Finding Category**: **${finding.category}**\n- **Confidence**: **${finding.confidence}%**\n- **Location**: \`${finding.file}\` (${finding.lines})\n\n#### Detection Evidence\n${finding.description}\n\n\`\`\`typescript\n${finding.codeSnippet}\n\`\`\`\n\n#### Analysis Invariants\n- CodeImpact detected **0 direct static imports** referencing this symbol during the AST scan.\n- This finding represents an *absence of static evidence*, not a guarantee of non-usage.`
        };
      }

      // D. "Which tests should I run?"
      if (q.includes('test') || q.includes('tests') || q.includes('spec') || q.includes('suite')) {
        return {
          source: 'grounded-engine' as const,
          text: `### 🧪 Test Impact Mapping: \`${fileName}\`\n\n- **Directly Associated Tests**: ${tests.length > 0 ? tests.map((t) => `\`${t}\``).join(', ') : '**No direct unit tests mapped.**'}\n- **Test Impact Context**: ${finding.testImpactContext?.whyAffected || 'Derived from topological dependency analysis.'}\n\n#### Recommended Test Plan\n${
            tests.length > 0
              ? tests.map((t, i) => `${i + 1}. Run \`npm test -- ${t}\``).join('\n')
              : '1. No tests import this file directly. Write a regression smoke test before altering this module.'
          }\n2. Run end-to-end integration tests to verify runtime paths.`
        };
      }

      // E. "Which modules depend on this file?"
      if (q.includes('depend') || q.includes('callers') || q.includes('consumers') || q.includes('modules')) {
        return {
          source: 'grounded-engine' as const,
          text: `### 🔗 Dependency Fan-In & Fan-Out: \`${fileName}\`\n\n- **Incoming Callers (${incomingCount})**: ${
            affectedModules.length > 0
              ? affectedModules.map((m) => `\`${m}\``).join(', ')
              : 'None detected.'
          }\n- **Outgoing Imports (${outgoingCount})**: This file imports **${outgoingCount}** other modules in the codebase.\n- **Circular Cycle Risk**: ${
            finding.category === 'Circular dependencies'
              ? '⚠️ **Active member of a circular dependency cycle.**'
              : 'No circular cycles detected for this module.'
          }`
        };
      }

      // F. "Is this finding reliable or a false positive?"
      if (q.includes('false positive') || q.includes('reliable') || q.includes('accuracy') || q.includes('confidence')) {
        return {
          source: 'grounded-engine' as const,
          text: `### 🎯 Reliability & False-Positive Analysis: \`${fileName}\`\n\n- **Confidence Score**: **${finding.confidence}%**\n- **Primary Evidence**: ${finding.description}\n\n#### Common False-Positive Scenarios for this Finding\n1. **Dynamic Reflection**: Code invoked via \`require(variable)\` or \`window[symbol]\` cannot be traced statically.\n2. **Plugin Registration**: Files automatically registered by Vite/Webpack glob loaders (e.g. \`import.meta.glob\`).\n3. **External Consumer API**: If this repository is an npm package or SDK, exports are consumed externally.\n\n#### Action\n- If this symbol belongs to a public SDK or plugin boundary, mark status as **"False Positive (Keep)"** in the Findings Explorer.`
        };
      }

      // G. "Explain this finding in simple terms"
      if (q.includes('simple terms') || q.includes('eli5') || q.includes('plain english') || q.includes('explain')) {
        return {
          source: 'grounded-engine' as const,
          text: `### 💡 Plain English Summary: \`${fileName}\`\n\n- **The Problem**: CodeImpact's **${finding.analyzer}** noticed that \`${fileName}\` ${
            finding.category === 'Potentially unused code'
              ? 'contains code that nothing else in the project seems to be importing or calling.'
              : finding.category === 'Circular dependencies'
              ? 'and another file import each other in a loop, which can cause subtle crashes when the app starts.'
              : finding.category === 'Duplicate code'
              ? 'contains a chunk of code that is almost identical to code in another file.'
              : finding.category === 'High-risk hotspots'
              ? 'is a heavily modified, central file that many other files depend on. Changing it carries high risk.'
              : 'has been flagged for engineering review.'
          }\n\n- **Why You Should Care**:\n  - Leaving dead code around bloats your bundle and confuses new developers.\n  - But deleting it recklessly can break things if it is secretly loaded in background scripts.\n\n- **What You Should Do Next**:\n  1. Don't delete it immediately.\n  2. Check if any tests use it (\`${tests[0] || 'npm test'}\`).\n  3. Verify whether it is part of a public API before removing.`
        };
      }

      // H. Default comprehensive context reply
      return {
        source: 'grounded-engine' as const,
        text: `### 📋 Contextual Assessment for \`${fileName}\` (${finding.lines})\n\n- **Analyzer**: Flagged by **${finding.analyzer}** with **${finding.confidence}%** confidence.\n- **Finding Type**: ${finding.category}\n- **Description**: ${finding.description}\n- **Impact Risk**: **${finding.impactRisk}** (${finding.impactScore}/100)\n- **Dependency Topology**: ${incomingCount} incoming callers, ${outgoingCount} outgoing imports.\n- **Mapped Tests**: ${tests.length > 0 ? tests.join(', ') : 'None mapped (requires regression verification)'}.\n\n#### Verification Steps:\n${finding.verificationSteps.map((step, idx) => `${idx + 1}. ${step}`).join('\n')}\n\n> [!NOTE]\n> **Runtime Caveat**: ${finding.runtimeCaveat || 'Static analysis does not guarantee runtime reachability.'}`
      };
    };

    const promise = runExplain().finally(() => {
      inFlightExplains.delete(dedupKey);
    });
    inFlightExplains.set(dedupKey, promise);
    return promise;
  },
  downloadFile(content: string, filename: string, mimeType: string): void {
    const blob = new Blob([content], { type: mimeType });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', filename);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  },

  /**
   * Generates structured JSON report object.
   */
  generateStructuredJsonReport(
    summary: AnalysisSummary,
    findings: Finding[],
    graphNodes: GraphNode[] = GRAPH_NODES,
    graphEdges: GraphEdge[] = GRAPH_EDGES,
    customization?: ReportCustomization
  ): string {
    let filteredFindings = findings;
    if (customization) {
      if (customization.filterCategory !== 'all') {
        filteredFindings = filteredFindings.filter((f) => f.category === customization.filterCategory);
      }
      if (customization.filterSeverity !== 'all') {
        filteredFindings = filteredFindings.filter((f) => f.severity === customization.filterSeverity);
      }
    }

    const reportObj = {
      meta: {
        platform: 'CodeImpact Intelligence Platform',
        version: '1.0.0',
        report_id: `REP-${Date.now()}`,
        generated_at: new Date().toISOString(),
        repository: {
          url: summary.repoUrl,
          branch: summary.branch,
          analyzed_files_count: summary.analyzedFiles
        }
      },
      executive_summary: customization?.includeExecutiveSummary !== false ? {
        health_score: summary.healthScore,
        total_findings: filteredFindings.length,
        hotspot_risk_index: summary.hotspotRiskIndex,
        potentially_unused_items: summary.potentiallyUnusedCount,
        duplication_clones: summary.duplicationClonesCount,
        circular_cycles: summary.circularCyclesCount,
        disclaimer: 'Static analysis cannot prove dynamic runtime reachability or reflection absence.'
      } : undefined,
      findings_breakdown: customization?.includeFindingsOverview !== false ? filteredFindings.map((f) => ({
        id: f.id,
        category: f.category,
        title: f.title,
        file: f.file,
        lines: f.lines,
        severity: f.severity,
        confidence_percent: f.confidence,
        impact_risk: f.impactRisk,
        impact_score: f.impactScore,
        analyzer: f.analyzer,
        review_status: f.reviewStatus,
        evidence: f.description,
        code_snippet: f.codeSnippet,
        dependencies: {
          incoming_callers_count: f.dependencyContext.incoming,
          outgoing_imports_count: f.dependencyContext.outgoing,
          affected_modules: f.dependencyContext.affectedModules
        },
        tests: {
          mapped_test_suites: f.testImpactContext?.testFiles || f.dependencyContext.affectedTests,
          why_affected: f.testImpactContext?.whyAffected || 'Assertions touch symbols from this module.'
        },
        verification_steps: f.verificationSteps,
        runtime_caveat: f.runtimeCaveat
      })) : undefined,
      dependency_topology: customization?.includeDependencyImpact !== false ? {
        node_count: graphNodes.length,
        edge_count: graphEdges.length,
        circular_cycles: GRAPH_CYCLES.map((c) => ({
          cycle_id: c.id,
          name: c.name,
          participating_nodes: c.nodeIds,
          description: c.description
        })),
        hotspot_nodes: graphNodes.filter((n) => n.type === 'hotspot').map((n) => ({
          label: n.label,
          file: n.filePath,
          incoming: n.incomingCount
        }))
      } : undefined,
      verification_checklist: customization?.includeVerificationChecklist !== false ? [
        'Inspect all call sites and dynamic imports before removal.',
        'Run mapped unit and integration test suites.',
        'Deprecate symbol with notice before deleting from master branch.',
        'Never rely solely on static analysis tools to verify deletion safety.'
      ] : undefined
    };

    return JSON.stringify(reportObj, null, 2);
  },

  /**
   * Generates RFC 4180 compliant CSV export of all findings.
   */
  generateCsvFindings(findings: Finding[]): string {
    const escapeCsv = (str: string | number) => {
      const s = String(str ?? '');
      if (s.includes(',') || s.includes('"') || s.includes('\n')) {
        return `"${s.replace(/"/g, '""')}"`;
      }
      return s;
    };

    const headers = [
      'Finding ID',
      'Category',
      'Title',
      'File Path',
      'Lines',
      'Severity',
      'Confidence %',
      'Impact Risk',
      'Impact Score',
      'Analyzer Engine',
      'Review Status',
      'Incoming Callers',
      'Outgoing Imports',
      'Mapped Tests Count',
      'Description / Evidence',
      'Runtime Caveat'
    ];

    const rows = findings.map((f) => [
      escapeCsv(f.id),
      escapeCsv(f.category),
      escapeCsv(f.title),
      escapeCsv(f.file),
      escapeCsv(f.lines),
      escapeCsv(f.severity),
      escapeCsv(f.confidence),
      escapeCsv(f.impactRisk),
      escapeCsv(f.impactScore),
      escapeCsv(f.analyzer),
      escapeCsv(f.reviewStatus),
      escapeCsv(f.dependencyContext.incoming),
      escapeCsv(f.dependencyContext.outgoing),
      escapeCsv((f.testImpactContext?.testFiles || f.dependencyContext.affectedTests).length),
      escapeCsv(f.description),
      escapeCsv(f.runtimeCaveat || '')
    ]);

    return [headers.join(','), ...rows.map((r) => r.join(','))].join('\r\n');
  },

  /**
   * Opens high-fidelity, printable PDF audit report in a dedicated printable view.
   */
  exportReportPdf(
    summary: AnalysisSummary,
    findings: Finding[],
    graphNodes: GraphNode[] = GRAPH_NODES,
    graphEdges: GraphEdge[] = GRAPH_EDGES,
    customization?: ReportCustomization
  ): void {
    let filteredFindings = findings;
    if (customization) {
      if (customization.filterCategory !== 'all') {
        filteredFindings = filteredFindings.filter((f) => f.category === customization.filterCategory);
      }
      if (customization.filterSeverity !== 'all') {
        filteredFindings = filteredFindings.filter((f) => f.severity === customization.filterSeverity);
      }
    }

    const printWindow = window.open('', '_blank');
    if (!printWindow) {
      alert('Pop-up blocked. Please allow pop-ups for CodeImpact to generate your printable PDF report.');
      return;
    }

    const html = `
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8" />
  <title>CodeImpact Audit Report - ${summary.repoUrl.replace('https://github.com/', '')}</title>
  <style>
    @page { size: A4; margin: 20mm; }
    body {
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
      color: #0f172a;
      line-height: 1.5;
      font-size: 11pt;
      margin: 0;
      padding: 20px;
    }
    .header {
      border-bottom: 3px solid #FF2E55;
      padding-bottom: 12px;
      margin-bottom: 24px;
      display: flex;
      justify-content: space-between;
      align-items: flex-end;
    }
    .logo {
      font-size: 20pt;
      font-weight: 900;
      color: #FF2E55;
      letter-spacing: -0.5px;
    }
    .meta {
      text-align: right;
      font-size: 9pt;
      color: #64748b;
      font-family: monospace;
    }
    .summary-grid {
      display: grid;
      grid-template-columns: repeat(4, 1fr);
      gap: 12px;
      margin-bottom: 24px;
    }
    .summary-card {
      background: #f8fafc;
      border: 1px solid #e2e8f0;
      border-radius: 8px;
      padding: 10px;
      text-align: center;
    }
    .summary-card .num {
      font-size: 16pt;
      font-weight: 900;
      color: #0f172a;
    }
    .summary-card .lbl {
      font-size: 8pt;
      text-transform: uppercase;
      font-weight: bold;
      color: #64748b;
    }
    h2 {
      font-size: 13pt;
      font-weight: 800;
      color: #0f172a;
      border-bottom: 1px solid #e2e8f0;
      padding-bottom: 6px;
      margin-top: 24px;
      margin-bottom: 12px;
    }
    .finding {
      border: 1px solid #e2e8f0;
      border-radius: 8px;
      padding: 12px;
      margin-bottom: 14px;
      page-break-inside: avoid;
    }
    .finding-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 6px;
    }
    .badge {
      font-size: 7.5pt;
      font-weight: 800;
      padding: 2px 6px;
      border-radius: 4px;
      text-transform: uppercase;
    }
    .badge-critical { background: #fee2e2; color: #991b1b; }
    .badge-high { background: #ffedd5; color: #9a3412; }
    .badge-med { background: #fef3c7; color: #92400e; }
    .badge-low { background: #f1f5f9; color: #475569; }
    .caution-box {
      background: #fff1f2;
      border: 1px solid #fecdd3;
      border-radius: 6px;
      padding: 10px;
      font-size: 9pt;
      color: #881337;
      margin-top: 20px;
      page-break-inside: avoid;
    }
    .checklist {
      margin-top: 8px;
      padding-left: 20px;
      font-size: 9pt;
    }
    @media print {
      body { padding: 0; }
      .no-print { display: none; }
    }
  </style>
</head>
<body>
  <div class="no-print" style="margin-bottom: 15px; padding: 10px; background: #0f172a; color: white; border-radius: 6px; display: flex; justify-content: space-between; align-items: center;">
    <span>PDF Print Preview Ready. Click <strong>Print / Save as PDF</strong>:</span>
    <button onclick="window.print()" style="background: #FF2E55; color: white; border: none; padding: 6px 14px; font-weight: bold; border-radius: 4px; cursor: pointer;">Print / Save as PDF</button>
  </div>

  <div class="header">
    <div>
      <div class="logo">CodeImpact</div>
      <div style="font-size: 10pt; color: #475569; font-weight: 600;">Codebase Analysis & Cleanup Intelligence Audit</div>
    </div>
    <div class="meta">
      <div><strong>Repository:</strong> ${summary.repoUrl.replace('https://github.com/', '')}</div>
      <div><strong>Branch:</strong> ${summary.branch} | <strong>Date:</strong> ${new Date().toLocaleDateString()}</div>
      <div><strong>Report ID:</strong> CIP-${Date.now()}</div>
    </div>
  </div>

  <div class="summary-grid">
    <div class="summary-card">
      <div class="num">${filteredFindings.length}</div>
      <div class="lbl">Total Findings</div>
    </div>
    <div class="summary-card">
      <div class="num" style="color: #FF2E55;">${summary.circularCyclesCount}</div>
      <div class="lbl">Circular Cycles</div>
    </div>
    <div class="summary-card">
      <div class="num">${summary.hotspotRiskIndex}/100</div>
      <div class="lbl">Hotspot Risk Index</div>
    </div>
    <div class="summary-card">
      <div class="num" style="color: #10b981;">${summary.healthScore}</div>
      <div class="lbl">Code Health Score</div>
    </div>
  </div>

  <h2>1. Priority Findings Overview (${filteredFindings.length})</h2>
  ${filteredFindings.map((f, i) => `
    <div class="finding">
      <div class="finding-header">
        <strong style="font-size: 10pt;">${i + 1}. [${f.id}] ${f.title}</strong>
        <span class="badge ${f.severity === 'Critical' ? 'badge-critical' : f.severity === 'High' ? 'badge-high' : f.severity === 'Medium' ? 'badge-med' : 'badge-low'}">${f.severity} Risk</span>
      </div>
      <div style="font-family: monospace; font-size: 8.5pt; color: #475569; margin-bottom: 6px;">
        ${f.file} (${f.lines}) &bull; Analyzer: <strong>${f.analyzer}</strong> &bull; Conf: <strong>${f.confidence}%</strong>
      </div>
      <div style="font-size: 9.5pt; color: #334155; margin-bottom: 6px;">
        ${f.description}
      </div>
      <div style="font-size: 8.5pt; color: #64748b; font-family: monospace;">
        Inbound Callers: ${f.dependencyContext.incoming} | Outbound Imports: ${f.dependencyContext.outgoing} | Mapped Tests: ${(f.testImpactContext?.testFiles || f.dependencyContext.affectedTests).length}
      </div>
    </div>
  `).join('')}

  <h2>2. Dependency & Cycle Impact</h2>
  <p style="font-size: 9.5pt; color: #334155;">
    Analyzed ${graphNodes.length} module nodes across ${graphEdges.length} static import edges.
    <strong>${summary.circularCyclesCount} circular dependency cycle(s)</strong> detected by Madge AST analysis (auth ⇄ user).
  </p>

  <h2>3. Responsible Verification Checklist</h2>
  <ol class="checklist">
    <li>Verify whether flagged files are accessed via dynamic import statements or runtime reflection.</li>
    <li>Run automated test suites targeting caller components before removing symbols.</li>
    <li>If modifying circular dependencies, extract shared interface contracts into isolated type files.</li>
    <li>Never auto-delete code without manual engineering review.</li>
  </ol>

  <div class="caution-box">
    <strong>Static Analysis Limitation Notice:</strong> Findings in this report represent candidates for engineering review. Static analysis cannot mathematically prove that code is completely unused due to runtime dynamics, reflection, or external consumers.
  </div>
</body>
</html>
    `;

    printWindow.document.open();
    printWindow.document.write(html);
    printWindow.document.close();
  },

  /**
   * Exports markdown report adhering to the CodeImpact specification.
   */
  generateMarkdownReport(
    summary: AnalysisSummary,
    findings: Finding[],
    customization?: ReportCustomization
  ): string {
    let filteredFindings = findings;
    if (customization) {
      if (customization.filterCategory !== 'all') {
        filteredFindings = filteredFindings.filter((f) => f.category === customization.filterCategory);
      }
      if (customization.filterSeverity !== 'all') {
        filteredFindings = filteredFindings.filter((f) => f.severity === customization.filterSeverity);
      }
    }

    return `# CodeImpact Intelligence Report
Repository: ${summary.repoUrl} (${summary.branch})
Generated: ${new Date().toISOString()}

---

## Executive Summary
- Analyzed Files: ${summary.analyzedFiles}
- Total Findings: ${filteredFindings.length}
- Potentially Unused Items: ${summary.potentiallyUnusedCount}
- Duplication Clones: ${summary.duplicationClonesCount}
- Circular Dependency Cycles: ${summary.circularCyclesCount}
- Hotspot Risk Index: ${summary.hotspotRiskIndex} / 100
- Repository Health Score: ${summary.healthScore}

> [!IMPORTANT]
> **Static Analysis Limitation**: Findings represent candidates for engineering review. Static analysis cannot prove that code is completely unused due to runtime dynamics, reflection, or downstream consumers.

---

## Priority Findings (${filteredFindings.length})
${filteredFindings
  .map(
    (f, idx) => `
### ${idx + 1}. [${f.id}] ${f.title}
- **Category**: ${f.category}
- **Severity**: ${f.severity}
- **Confidence**: ${f.confidence}%
- **Impact Risk**: ${f.impactRisk} (Score: ${f.impactScore}/100)
- **Analyzer**: ${f.analyzer}
- **File**: \`${f.file}\` (${f.lines})
- **Incoming Dependents**: ${f.dependencyContext.incoming}
- **Outgoing References**: ${f.dependencyContext.outgoing}

#### Evidence:
${f.description}

#### Verification Checklist:
${f.verificationSteps.map((s) => `- [ ] ${s}`).join('\n')}

#### Runtime Caveat:
${f.runtimeCaveat || 'None noted'}
`
  )
  .join('\n')}
`;
  }
};
