export type FindingCategory =
  | 'Potentially unused code'
  | 'Duplicate code'
  | 'Circular dependencies'
  | 'Potentially unused files'
  | 'High-risk hotspots';

export type FindingSeverity = 'Critical' | 'High' | 'Medium' | 'Low';

export type ImpactRiskType = 'low' | 'medium' | 'high' | 'critical';

export type ReviewStatus =
  | 'Pending Review'
  | 'In Review'
  | 'Verified for Refactor'
  | 'False Positive (Keep)'
  | 'High Risk (Do Not Touch)';

export interface DependencyContext {
  incoming: number;
  outgoing: number;
  affectedModules: string[];
  affectedTests: string[];
}

export interface TestImpactContext {
  testFiles: string[];
  whyAffected: string;
}

export interface Finding {
  id: string;
  category: FindingCategory;
  title: string;
  file: string;
  lines: string;
  severity: FindingSeverity;
  confidence: number;
  impactScore: number;
  impactRisk: string;
  impactRiskType: ImpactRiskType;
  analyzer: string;
  description: string;
  codeSnippet: string;
  dependencyContext: DependencyContext;
  testImpactContext?: TestImpactContext;
  verificationSteps: string[];
  reviewStatus: ReviewStatus;
  runtimeCaveat?: string;
}

export interface DemoRepo {
  name: string;
  label: string;
  branch: string;
  stars: string;
  health: string;
  description?: string;
}

export interface GraphNode {
  id: string;
  label: string;
  type: 'entry' | 'cycle' | 'duplicate' | 'unused' | 'hotspot' | 'standard';
  risk: 'low' | 'medium' | 'high' | 'critical';
  x: number;
  y: number;
  val: number;
  filePath?: string;
  findingCount?: number;
  incomingCount?: number;
  outgoingCount?: number;
  affectedModules?: string[];
  affectedTests?: string[];
  riskEvidence?: string;
  verificationSteps?: string[];
  cycleWith?: string[];
  isEntry?: boolean;
}

export interface GraphEdge {
  id?: string;
  from: string;
  to: string;
  source?: string;
  target?: string;
  isCycle?: boolean;
  label?: string;
}

export interface DependencyCycleInfo {
  id: string;
  name: string;
  nodeIds: string[];
  description: string;
  severity: FindingSeverity;
}

export interface CompetitorRow {
  tool: string;
  focus: string;
  evidence: string;
  impact: string;
  cycle: string;
  ai: string;
  isUs?: boolean;
}

export interface TerminalLog {
  id: number | string;
  type: 'info' | 'warn' | 'error' | 'success';
  text: string;
  timestamp?: string;
}

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  text: string;
  timestamp?: string;
  groundingFindingId?: string;
  groundingFile?: string;
  source?: 'backend-gemini' | 'grounded-engine';
}

export interface AnalysisSummary {
  repoUrl: string;
  branch: string;
  analyzedFiles: number;
  totalFindings: number;
  potentiallyUnusedCount: number;
  duplicationClonesCount: number;
  circularCyclesCount: number;
  hotspotRiskIndex: number;
  healthScore: string;
}

export interface GeneratedReport {
  id: string;
  repoUrl: string;
  branch: string;
  generatedAt: string;
  format: 'PDF' | 'JSON' | 'CSV' | 'Markdown';
  totalFindings: number;
  criticalCount: number;
  healthScore: string;
  fileSize?: string;
}

export interface ReportCustomization {
  includeExecutiveSummary: boolean;
  includeFindingsOverview: boolean;
  includeDependencyImpact: boolean;
  includeTestImpact: boolean;
  includeVerificationChecklist: boolean;
  filterCategory: string;
  filterSeverity: string;
}

export interface AnalysisScanStep {
  progress: number;
  status: string;
  log: string;
  type: 'info' | 'warn' | 'error' | 'success';
}
