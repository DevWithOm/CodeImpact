import { DemoRepo, Finding, GraphNode, GraphEdge, CompetitorRow, TerminalLog, AnalysisSummary } from '../types';

export const DEMO_REPOS: DemoRepo[] = [
  { name: 'facebook/react', label: 'React Core', branch: 'main', stars: '220k', health: '89%', description: 'UI library for web and native interfaces' },
  { name: 'tailwindlabs/tailwindcss', label: 'Tailwind CSS', branch: 'main', stars: '81k', health: '94%', description: 'Utility-first CSS framework' },
  { name: 'vercel/next.js', label: 'Next.js Framework', branch: 'canary', stars: '121k', health: '86%', description: 'The React Framework for the Web' },
  { name: 'expressjs/express', label: 'Express Node', branch: 'master', stars: '64k', health: '78%', description: 'Fast, unopinionated minimalist web framework' }
];

export const INITIAL_FINDINGS: Finding[] = [
  {
    id: 'FIND-101',
    category: 'Potentially unused code',
    title: 'Unreferenced export `calculateLegacyMetrics`',
    file: 'src/analytics/legacyCalculator.ts',
    lines: 'L42 - L89',
    severity: 'High',
    confidence: 94,
    impactScore: 28,
    impactRisk: 'Low Risk',
    impactRiskType: 'low',
    analyzer: 'Knip AST Engine',
    reviewStatus: 'Pending Review',
    description: 'Exported function is never statically imported across 412 modules in this repository.',
    codeSnippet: `// src/analytics/legacyCalculator.ts
export function calculateLegacyMetrics(data: RawPayload): LegacyMetrics {
  const normalized = data.values.map(v => v * 1.05);
  return {
    score: normalized.reduce((a, b) => a + b, 0),
    timestamp: Date.now()
  };
}`,
    dependencyContext: {
      incoming: 0,
      outgoing: 2,
      affectedModules: ['src/analytics/types.ts', 'src/utils/math.ts'],
      affectedTests: ['tests/analytics/legacy.test.ts']
    },
    testImpactContext: {
      testFiles: ['tests/analytics/legacy.test.ts'],
      whyAffected: 'Test file directly imports and asserts return values of `calculateLegacyMetrics`. Removing the export will cause compilation failure in this test suite.'
    },
    verificationSteps: [
      'Search for dynamic `import()` or string key lookups in reflection modules.',
      'Check if function is consumed by external API consumers or public SDK entrypoints.',
      'Run `npm test tests/analytics/legacy.test.ts` before executing removal.'
    ],
    runtimeCaveat: 'Static analysis cannot prove absence of dynamic imports, eval(), or reflection lookups.'
  },
  {
    id: 'FIND-102',
    category: 'Circular dependencies',
    title: 'Circular dependency cycle between Auth & User Context',
    file: 'src/auth/sessionProvider.tsx',
    lines: 'L12 & src/user/userProfile.tsx:L5',
    severity: 'Critical',
    confidence: 99,
    impactScore: 92,
    impactRisk: 'High Risk',
    impactRiskType: 'high',
    analyzer: 'Madge Cycle Matrix',
    reviewStatus: 'In Review',
    description: 'Direct circular dependency chain: SessionProvider -> UserProfile -> SessionProvider.',
    codeSnippet: `// src/auth/sessionProvider.tsx
import { UserProfile } from '../user/userProfile'; // <-- Cycle Link A

// src/user/userProfile.tsx
import { useSession } from '../auth/sessionProvider'; // <-- Cycle Link B`,
    dependencyContext: {
      incoming: 12,
      outgoing: 8,
      affectedModules: ['src/auth/index.ts', 'src/user/index.ts', 'src/components/Header.tsx'],
      affectedTests: ['tests/auth/flow.test.ts', 'tests/user/profile.test.ts']
    },
    testImpactContext: {
      testFiles: ['tests/auth/flow.test.ts', 'tests/user/profile.test.ts'],
      whyAffected: 'Both suites mock the mutual import boundary. Refactoring the cycle will require updating session mock providers across auth and user test harnesses.'
    },
    verificationSteps: [
      'Extract shared interface or state type into isolated `src/types/auth.ts`.',
      'Use dependency injection or React Context splitting to decouple runtime initializations.',
      'Verify bundle size and tree-shaking execution order post refactor.'
    ],
    runtimeCaveat: 'Circular dependencies cause uninitialized undefined exports during bundler evaluation.'
  },
  {
    id: 'FIND-103',
    category: 'Duplicate code',
    title: '92% identical duplication fragment in Data Formatters',
    file: 'src/utils/formatters.ts',
    lines: 'L110 - L165',
    severity: 'Medium',
    confidence: 91,
    impactScore: 64,
    impactRisk: 'Medium Risk',
    impactRiskType: 'medium',
    analyzer: 'jscpd Structural Clone Detector',
    reviewStatus: 'Pending Review',
    description: 'Identical AST clone found in src/services/oldDataPipeline.ts (L45-L100).',
    codeSnippet: `// Duplicate fragment in formatters.ts & oldDataPipeline.ts
export const formatCurrency = (val: number, currency = 'USD') => {
  if (isNaN(val)) return '$0.00';
  const formatted = new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: currency,
    minimumFractionDigits: 2
  }).format(val);
  return formatted.replace(/\\$/g, '$ ');
};`,
    dependencyContext: {
      incoming: 14,
      outgoing: 1,
      affectedModules: ['src/services/oldDataPipeline.ts', 'src/views/Billing.tsx'],
      affectedTests: ['tests/utils/formatters.test.ts']
    },
    testImpactContext: {
      testFiles: ['tests/utils/formatters.test.ts'],
      whyAffected: 'Unit test validates string formatting replacement edge cases. Consolidating into a single helper must pass all existing currency rounding assertions.'
    },
    verificationSteps: [
      'Extract common currency helper into `src/utils/currencyFormatter.ts`.',
      'Ensure custom replace edge cases are covered by shared unit test suite.'
    ],
    runtimeCaveat: 'Cloned logic can diverge over time, introducing subtle billing calculation differences.'
  },
  {
    id: 'FIND-104',
    category: 'Potentially unused files',
    title: 'Unreferenced file `src/legacy/v1Adapter.ts`',
    file: 'src/legacy/v1Adapter.ts',
    lines: 'L1 - L140',
    severity: 'Medium',
    confidence: 88,
    impactScore: 45,
    impactRisk: 'Medium Risk',
    impactRiskType: 'medium',
    analyzer: 'Knip File Scanner',
    reviewStatus: 'Pending Review',
    description: 'File has zero incoming static references from entry point tree graph.',
    codeSnippet: `// src/legacy/v1Adapter.ts
/**
 * @deprecated V1 API compatibility layer
 */
export class V1Adapter {
  static convertPayload(raw: any) {
    return { version: 1, data: raw };
  }
}`,
    dependencyContext: {
      incoming: 0,
      outgoing: 3,
      affectedModules: ['src/types/v1.ts'],
      affectedTests: []
    },
    testImpactContext: {
      testFiles: [],
      whyAffected: 'No direct unit tests reference this file. Verify build-time entry points and packaging configuration before deleting.'
    },
    verificationSteps: [
      'Verify whether file is loaded dynamically via plugin registration.',
      'Check build configuration entry points (e.g. multi-page webpack/vite entries).'
    ],
    runtimeCaveat: 'Check dynamic module loaders or glob imports (`import.meta.glob`) before deleting.'
  },
  {
    id: 'FIND-105',
    category: 'High-risk hotspots',
    title: 'Deeply nested event emitter fan-out bottleneck',
    file: 'src/core/eventEmitter.ts',
    lines: 'L1 - L210',
    severity: 'High',
    confidence: 96,
    impactScore: 88,
    impactRisk: 'High Risk',
    impactRiskType: 'high',
    analyzer: 'CodeScene Hotspot Engine',
    reviewStatus: 'High Risk (Do Not Touch)',
    description: 'High modification velocity combined with deep outgoing dependent fan-out.',
    codeSnippet: `// src/core/eventEmitter.ts
export class AppEventEmitter {
  private listeners: Map<string, Function[]> = new Map();
  emit(event: string, payload: any) {
    const list = this.listeners.get(event) || [];
    list.forEach(fn => fn(payload));
  }
}`,
    dependencyContext: {
      incoming: 34,
      outgoing: 5,
      affectedModules: ['src/app.tsx', 'src/store/index.ts', 'src/services/socket.ts'],
      affectedTests: ['tests/core/emitter.test.ts', 'tests/integration/app.test.ts']
    },
    testImpactContext: {
      testFiles: ['tests/core/emitter.test.ts', 'tests/integration/app.test.ts'],
      whyAffected: 'Over 34 modules and 2 integration suites rely on asynchronous event broadcasting. Changing the dispatch order breaks test expectations.'
    },
    verificationSteps: [
      'Avoid breaking interface changes; run full end-to-end integration test suite.',
      'Deprecate legacy event listeners gradually before altering dispatcher signature.'
    ],
    runtimeCaveat: 'Widely imported core primitives have massive ripple effects if altered.'
  },
  {
    id: 'FIND-106',
    category: 'Potentially unused code',
    title: 'Dead fallback error handler `handleHttpFallback503`',
    file: 'src/network/client.ts',
    lines: 'L180 - L205',
    severity: 'Low',
    confidence: 91,
    impactScore: 18,
    impactRisk: 'Low Risk',
    impactRiskType: 'low',
    analyzer: 'Knip AST Engine',
    reviewStatus: 'Verified for Refactor',
    description: 'Private helper function was superseded by Axios interceptor retry middleware.',
    codeSnippet: `// src/network/client.ts
function handleHttpFallback503(error: AxiosError): RetryPolicy {
  // Legacy fallback superseded by middleware/retry.ts
  return { attempts: 0, shouldBail: true };
}`,
    dependencyContext: {
      incoming: 0,
      outgoing: 1,
      affectedModules: ['src/network/types.ts'],
      affectedTests: ['tests/network/client.test.ts']
    },
    testImpactContext: {
      testFiles: ['tests/network/client.test.ts'],
      whyAffected: 'A commented-out test case still targets this function. The test can be safely removed alongside the dead handler.'
    },
    verificationSteps: [
      'Verify Axios interceptors handle 503 retry policies independently.',
      'Run network test suite `npm test tests/network/client.test.ts`.'
    ],
    runtimeCaveat: 'Check for private symbol extraction in unit test mocks.'
  },
  {
    id: 'FIND-107',
    category: 'Duplicate code',
    title: 'Duplicate date parser across UI components',
    file: 'src/components/DateBadge.tsx',
    lines: 'L25 - L48',
    severity: 'Low',
    confidence: 84,
    impactScore: 22,
    impactRisk: 'Low Risk',
    impactRiskType: 'low',
    analyzer: 'jscpd Structural Clone Detector',
    reviewStatus: 'False Positive (Keep)',
    description: 'Local date parsing clone matches src/views/ActivityLog.tsx but handles timezone offset differently.',
    codeSnippet: `// src/components/DateBadge.tsx
export function parseBadgeDate(isoString: string): string {
  const d = new Date(isoString);
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
}`,
    dependencyContext: {
      incoming: 6,
      outgoing: 0,
      affectedModules: ['src/components/Header.tsx', 'src/views/Feed.tsx'],
      affectedTests: ['tests/components/DateBadge.test.tsx']
    },
    testImpactContext: {
      testFiles: ['tests/components/DateBadge.test.tsx'],
      whyAffected: 'UI snapshot tests verify formatted date strings for localized badges.'
    },
    verificationSteps: [
      'Confirm whether timezone behavior is intentionally different for compact badge display.',
      'Mark as false positive if intentional UI micro-optimization.'
    ],
    runtimeCaveat: 'Consolidating date formatters can cause unexpected time zone shifts in UI badges.'
  }
];

export const GRAPH_NODES: GraphNode[] = [
  { id: 'app', label: 'App.tsx', type: 'entry', risk: 'low', x: 220, y: 70, val: 30, filePath: 'src/App.tsx', findingCount: 0 },
  { id: 'auth', label: 'sessionProvider.tsx', type: 'cycle', risk: 'high', x: 90, y: 190, val: 45, filePath: 'src/auth/sessionProvider.tsx', findingCount: 1 },
  { id: 'user', label: 'userProfile.tsx', type: 'cycle', risk: 'high', x: 330, y: 190, val: 45, filePath: 'src/user/userProfile.tsx', findingCount: 1 },
  { id: 'format', label: 'formatters.ts', type: 'duplicate', risk: 'medium', x: 480, y: 120, val: 25, filePath: 'src/utils/formatters.ts', findingCount: 1 },
  { id: 'legacy', label: 'legacyCalculator.ts', type: 'unused', risk: 'low', x: 50, y: 320, val: 20, filePath: 'src/analytics/legacyCalculator.ts', findingCount: 1 },
  { id: 'v1', label: 'v1Adapter.ts', type: 'unused', risk: 'medium', x: 490, y: 310, val: 22, filePath: 'src/legacy/v1Adapter.ts', findingCount: 1 },
  { id: 'emitter', label: 'eventEmitter.ts', type: 'hotspot', risk: 'high', x: 250, y: 340, val: 50, filePath: 'src/core/eventEmitter.ts', findingCount: 1 }
];

export const GRAPH_EDGES: GraphEdge[] = [
  { from: 'app', to: 'auth' },
  { from: 'app', to: 'format' },
  { from: 'auth', to: 'user', isCycle: true, label: 'Cycle Link A' },
  { from: 'user', to: 'auth', isCycle: true, label: 'Cycle Link B' },
  { from: 'auth', to: 'emitter' },
  { from: 'user', to: 'emitter' },
  { from: 'app', to: 'emitter' },
  { from: 'format', to: 'v1' }
];

export const COMPETITOR_MATRIX: CompetitorRow[] = [
  { tool: 'Knip', focus: 'Unused Code / Exports', evidence: 'High', impact: 'None', cycle: 'Basic', ai: 'No' },
  { tool: 'jscpd', focus: 'Code Duplication Clones', evidence: 'High', impact: 'None', cycle: 'No', ai: 'No' },
  { tool: 'Madge', focus: 'Module Dependency Graph', evidence: 'High', impact: 'Low', cycle: 'Strong', ai: 'No' },
  { tool: 'SonarQube', focus: 'Code Quality & Vulnerabilities', evidence: 'Medium', impact: 'Medium', cycle: 'Medium', ai: 'Limited' },
  { tool: 'CodeScene', focus: 'Hotspots & Tech Debt', evidence: 'High', impact: 'High', cycle: 'Medium', ai: 'No' },
  { tool: 'Greptile', focus: 'AI Code Review', evidence: 'Low', impact: 'Medium', cycle: 'No', ai: 'Strong' },
  { tool: 'CodeImpact', focus: 'Unified Contextual Intelligence', evidence: 'Explosive Multi-Tool', impact: 'Deep Contextual', cycle: 'Full Highlight', ai: 'Grounded Evidence', isUs: true }
];

export const INITIAL_LOGS: TerminalLog[] = [
  { id: 1, type: 'info', text: '[SYSTEM] CodeImpact Engine initialized in high-performance Red Mode.' },
  { id: 2, type: 'success', text: '[STATIC] Connected to Knip, jscpd, and Madge analysis drivers.' }
];

export const DEFAULT_SUMMARY: AnalysisSummary = {
  repoUrl: 'https://github.com/facebook/react',
  branch: 'main',
  analyzedFiles: 412,
  totalFindings: 7,
  potentiallyUnusedCount: 14,
  duplicationClonesCount: 6,
  circularCyclesCount: 3,
  hotspotRiskIndex: 88,
  healthScore: '89%'
};
