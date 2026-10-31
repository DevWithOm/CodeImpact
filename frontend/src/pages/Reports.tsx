import React, { useState } from 'react';
import {
  FileText,
  Download,
  Printer,
  FileSpreadsheet,
  FileCode,
  ShieldCheck,
  CheckCircle2,
  AlertTriangle,
  FolderGit2,
  Filter,
  Eye,
  Clock
} from 'lucide-react';

import {
  AnalysisSummary,
  Finding,
  GraphNode,
  GraphEdge,
  ReportCustomization,
  GeneratedReport
} from '../types';
import { api } from '../services/api';
import { GRAPH_NODES, GRAPH_EDGES } from '../services/mockData';

interface ReportsPageProps {
  summary: AnalysisSummary;
  findings: Finding[];
  graphNodes?: GraphNode[];
  graphEdges?: GraphEdge[];
  analysisId?: string;
  onNavigateToFindings?: () => void;
  onNavigateToGraph?: () => void;
}

export const ReportsPage: React.FC<ReportsPageProps> = ({
  summary,
  findings,
  graphNodes = GRAPH_NODES,
  graphEdges = GRAPH_EDGES,
  analysisId
}) => {
  const [activeTab, setActiveTab] = useState<'overview' | 'preview'>('overview');
  const [downloadSuccess, setDownloadSuccess] = useState<string | null>(null);

  // Customization state
  const [customization, setCustomization] = useState<ReportCustomization>({
    includeExecutiveSummary: true,
    includeFindingsOverview: true,
    includeDependencyImpact: true,
    includeTestImpact: true,
    includeVerificationChecklist: true,
    filterCategory: 'all',
    filterSeverity: 'all'
  });

  // Local report generation history
  const [reportHistory, setReportHistory] = useState<GeneratedReport[]>([
    {
      id: 'REP-101',
      repoUrl: summary.repoUrl,
      branch: summary.branch,
      generatedAt: 'Today, 1:15 PM',
      format: 'PDF',
      totalFindings: findings.length,
      criticalCount: findings.filter((f) => f.severity === 'Critical' || f.severity === 'High').length,
      healthScore: summary.healthScore,
      fileSize: '142 KB'
    },
    {
      id: 'REP-102',
      repoUrl: summary.repoUrl,
      branch: summary.branch,
      generatedAt: 'Today, 1:28 PM',
      format: 'JSON',
      totalFindings: findings.length,
      criticalCount: findings.filter((f) => f.severity === 'Critical' || f.severity === 'High').length,
      healthScore: summary.healthScore,
      fileSize: '48 KB'
    }
  ]);

  // Filtered findings for preview & export
  const filteredFindings = findings.filter((f) => {
    if (customization.filterCategory !== 'all' && f.category !== customization.filterCategory) {
      return false;
    }
    if (customization.filterSeverity !== 'all' && f.severity !== customization.filterSeverity) {
      return false;
    }
    return true;
  });

  const recordDownload = (format: 'PDF' | 'JSON' | 'CSV' | 'Markdown', size: string) => {
    setDownloadSuccess(format);
    setTimeout(() => setDownloadSuccess(null), 3000);

    const newRecord: GeneratedReport = {
      id: `REP-${Date.now().toString().slice(-4)}`,
      repoUrl: summary.repoUrl,
      branch: summary.branch,
      generatedAt: 'Just now',
      format,
      totalFindings: filteredFindings.length,
      criticalCount: filteredFindings.filter((f) => f.severity === 'Critical' || f.severity === 'High').length,
      healthScore: summary.healthScore,
      fileSize: size
    };
    setReportHistory((prev) => [newRecord, ...prev.slice(0, 4)]);
  };

  // Export handlers
  const handleExportPdf = () => {
    api.exportReportPdf(summary, filteredFindings, graphNodes, graphEdges, customization);
    recordDownload('PDF', '~150 KB');
  };

  const handleExportJson = () => {
    const jsonStr = api.generateStructuredJsonReport(summary, findings, graphNodes, graphEdges, customization);
    api.downloadFile(jsonStr, `CodeImpact-Audit-${Date.now()}.json`, 'application/json');
    recordDownload('JSON', `${(jsonStr.length / 1024).toFixed(1)} KB`);
  };

  const handleExportCsv = () => {
    const csvStr = api.generateCsvFindings(filteredFindings);
    api.downloadFile(csvStr, `CodeImpact-Findings-${Date.now()}.csv`, 'text/csv;charset=utf-8;');
    recordDownload('CSV', `${(csvStr.length / 1024).toFixed(1)} KB`);
  };

  const handleExportMarkdown = async () => {
    if (analysisId) {
      const downloaded = await api.downloadServerReport(analysisId);
      if (downloaded) {
        recordDownload('Markdown', 'Audit Report');
        return;
      }
    }
    const mdStr = api.generateMarkdownReport(summary, findings, customization);
    api.downloadFile(mdStr, `CodeImpact-Report-${Date.now()}.md`, 'text/markdown;charset=utf-8;');
    recordDownload('Markdown', `${(mdStr.length / 1024).toFixed(1)} KB`);
  };

  return (
    <div className="space-y-6 animate-fadeIn pb-12">
      {/* 1. Header Banner */}
      <div className="p-6 rounded-3xl bg-white border border-red-100 shadow-xl flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="space-y-1">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-[10px] font-black uppercase tracking-widest px-2.5 py-0.5 rounded-full bg-red-50 text-[#FF2E55] border border-red-200">
              Executive Audit & Compliance
            </span>
            <span className="text-[10px] font-mono text-slate-500 bg-slate-100 px-2 py-0.5 rounded">
              Engine: Deterministic AST & Dependency Impact
            </span>
          </div>

          <h2 className="text-xl font-black text-slate-900 flex items-center gap-2">
            <FileText className="w-5 h-5 text-[#FF2E55]" />
            Reports & Artifact Export
          </h2>

          <p className="text-xs text-slate-600 font-medium max-w-2xl">
            Generate audit-grade engineering reports in PDF, JSON, and CSV formats. Export structural findings, blast radius metrics, and verification steps for pull request compliance.
          </p>
        </div>

        {/* Target Workspace Info */}
        <div className="p-3 rounded-2xl bg-[#0F0F12] text-white flex items-center gap-3 border border-red-900/40 shadow-xs shrink-0 font-mono text-xs">
          <FolderGit2 className="w-5 h-5 text-[#FF2E55]" />
          <div>
            <div className="font-bold text-white truncate max-w-[180px]">
              {summary.repoUrl.replace('https://github.com/', '')}
            </div>
            <div className="text-[10px] text-slate-400">Branch: {summary.branch} &bull; Score: {summary.healthScore}</div>
          </div>
        </div>
      </div>

      {/* 2. Success Alert notification */}
      {downloadSuccess && (
        <div className="p-3.5 rounded-2xl bg-emerald-50 border border-emerald-200 text-emerald-950 text-xs font-bold flex items-center gap-2 animate-fadeIn shadow-xs">
          <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
          <span>Successfully generated and downloaded <strong>{downloadSuccess}</strong> audit artifact!</span>
        </div>
      )}

      {/* 3. Metric Summary Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
        <div className="p-4 rounded-2xl bg-white border border-slate-200/90 shadow-sm text-center">
          <span className="text-[10px] font-bold text-slate-400 uppercase block">Total Findings</span>
          <span className="text-xl font-black text-slate-900">{findings.length}</span>
          <span className="text-[10px] text-slate-500 block font-mono">AST Verified</span>
        </div>

        <div className="p-4 rounded-2xl bg-white border border-slate-200/90 shadow-sm text-center">
          <span className="text-[10px] font-bold text-slate-400 uppercase block">Potentially Unused</span>
          <span className="text-xl font-black text-amber-600">{summary.potentiallyUnusedCount}</span>
          <span className="text-[10px] text-slate-500 block font-mono">Knip AST</span>
        </div>

        <div className="p-4 rounded-2xl bg-white border border-slate-200/90 shadow-sm text-center">
          <span className="text-[10px] font-bold text-slate-400 uppercase block">Duplicate Clones</span>
          <span className="text-xl font-black text-purple-600">{summary.duplicationClonesCount}</span>
          <span className="text-[10px] text-slate-500 block font-mono">jscpd Structural</span>
        </div>

        <div className="p-4 rounded-2xl bg-white border border-slate-200/90 shadow-sm text-center">
          <span className="text-[10px] font-bold text-slate-400 uppercase block">Circular Cycles</span>
          <span className="text-xl font-black text-[#FF2E55]">{summary.circularCyclesCount}</span>
          <span className="text-[10px] text-slate-500 block font-mono">Madge Matrix</span>
        </div>

        <div className="p-4 rounded-2xl bg-white border border-slate-200/90 shadow-sm text-center">
          <span className="text-[10px] font-bold text-slate-400 uppercase block">Hotspot Index</span>
          <span className="text-xl font-black text-rose-600">{summary.hotspotRiskIndex}/100</span>
          <span className="text-[10px] text-slate-500 block font-mono">Fan-in Risk</span>
        </div>

        <div className="p-4 rounded-2xl bg-white border border-slate-200/90 shadow-sm text-center">
          <span className="text-[10px] font-bold text-slate-400 uppercase block">Code Health</span>
          <span className="text-xl font-black text-emerald-600">{summary.healthScore}</span>
          <span className="text-[10px] text-slate-500 block font-mono">Overall Score</span>
        </div>
      </div>

      {/* 4. Tab Navigation: Overview & Generator vs Live Preview */}
      <div className="flex items-center gap-2 border-b border-slate-200 pb-2">
        <button
          onClick={() => setActiveTab('overview')}
          className={`px-4 py-2 rounded-xl text-xs font-black transition-all flex items-center gap-1.5 ${
            activeTab === 'overview'
              ? 'bg-[#FF2E55] text-white shadow-md shadow-red-500/20'
              : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100'
          }`}
        >
          <Download className="w-3.5 h-3.5" />
          <span>Report Generator & Formats</span>
        </button>

        <button
          onClick={() => setActiveTab('preview')}
          className={`px-4 py-2 rounded-xl text-xs font-black transition-all flex items-center gap-1.5 ${
            activeTab === 'preview'
              ? 'bg-[#FF2E55] text-white shadow-md shadow-red-500/20'
              : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100'
          }`}
        >
          <Eye className="w-3.5 h-3.5" />
          <span>Interactive Report Preview ({filteredFindings.length})</span>
        </button>
      </div>

      {/* 5. Tab Content: Generator & Customization */}
      {activeTab === 'overview' && (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
          {/* Left Column: Export Actions & Customization (8 Cols) */}
          <div className="lg:col-span-8 space-y-6">
            {/* Quick Export Cards */}
            <div className="p-6 rounded-3xl bg-white border border-slate-200/90 shadow-xl space-y-4">
              <h3 className="text-sm font-black uppercase tracking-wider text-slate-800 font-mono">
                Available Export Formats
              </h3>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3.5">
                {/* PDF Card */}
                <div className="p-4 rounded-2xl border border-slate-200 bg-slate-50 hover:bg-white hover:border-red-300 transition-all shadow-xs flex flex-col justify-between space-y-3">
                  <div className="flex items-start gap-3">
                    <div className="w-10 h-10 rounded-xl bg-red-100 text-[#FF2E55] flex items-center justify-center shrink-0">
                      <Printer className="w-5 h-5" />
                    </div>
                    <div>
                      <h4 className="text-sm font-black text-slate-900">PDF Executive Audit</h4>
                      <p className="text-xs text-slate-500 leading-snug">
                        Formatted print document with CodeImpact branding, summary matrices, and verification checklists.
                      </p>
                    </div>
                  </div>
                  <button
                    onClick={handleExportPdf}
                    className="w-full py-2 px-3 rounded-xl bg-[#FF2E55] hover:bg-red-600 text-white text-xs font-extrabold flex items-center justify-center gap-1.5 shadow-xs transition-colors"
                  >
                    <Download className="w-3.5 h-3.5" />
                    <span>Download / Print PDF</span>
                  </button>
                </div>

                {/* JSON Card */}
                <div className="p-4 rounded-2xl border border-slate-200 bg-slate-50 hover:bg-white hover:border-blue-300 transition-all shadow-xs flex flex-col justify-between space-y-3">
                  <div className="flex items-start gap-3">
                    <div className="w-10 h-10 rounded-xl bg-blue-100 text-blue-600 flex items-center justify-center shrink-0">
                      <FileCode className="w-5 h-5" />
                    </div>
                    <div>
                      <h4 className="text-sm font-black text-slate-900">JSON Machine Payload</h4>
                      <p className="text-xs text-slate-500 leading-snug">
                        Full structured schema including AST nodes, dependency edges, cycle chains, and test mappings.
                      </p>
                    </div>
                  </div>
                  <button
                    onClick={handleExportJson}
                    className="w-full py-2 px-3 rounded-xl bg-slate-900 hover:bg-slate-800 text-white text-xs font-extrabold flex items-center justify-center gap-1.5 shadow-xs transition-colors"
                  >
                    <Download className="w-3.5 h-3.5" />
                    <span>Download JSON Payload</span>
                  </button>
                </div>

                {/* CSV Card */}
                <div className="p-4 rounded-2xl border border-slate-200 bg-slate-50 hover:bg-white hover:border-emerald-300 transition-all shadow-xs flex flex-col justify-between space-y-3">
                  <div className="flex items-start gap-3">
                    <div className="w-10 h-10 rounded-xl bg-emerald-100 text-emerald-600 flex items-center justify-center shrink-0">
                      <FileSpreadsheet className="w-5 h-5" />
                    </div>
                    <div>
                      <h4 className="text-sm font-black text-slate-900">CSV Spreadsheet</h4>
                      <p className="text-xs text-slate-500 leading-snug">
                        RFC 4180 tabular breakdown for spreadsheets, Jira import, and tracking engineering debt.
                      </p>
                    </div>
                  </div>
                  <button
                    onClick={handleExportCsv}
                    className="w-full py-2 px-3 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-extrabold flex items-center justify-center gap-1.5 shadow-xs transition-colors"
                  >
                    <Download className="w-3.5 h-3.5" />
                    <span>Download CSV Summary</span>
                  </button>
                </div>

                {/* Markdown Card */}
                <div className="p-4 rounded-2xl border border-slate-200 bg-slate-50 hover:bg-white hover:border-purple-300 transition-all shadow-xs flex flex-col justify-between space-y-3">
                  <div className="flex items-start gap-3">
                    <div className="w-10 h-10 rounded-xl bg-purple-100 text-purple-600 flex items-center justify-center shrink-0">
                      <FileText className="w-5 h-5" />
                    </div>
                    <div>
                      <h4 className="text-sm font-black text-slate-900">Markdown (.md)</h4>
                      <p className="text-xs text-slate-500 leading-snug">
                        GitHub-flavored markdown report ready to paste into Pull Request descriptions or repository docs.
                      </p>
                    </div>
                  </div>
                  <button
                    onClick={handleExportMarkdown}
                    className="w-full py-2 px-3 rounded-xl bg-purple-600 hover:bg-purple-700 text-white text-xs font-extrabold flex items-center justify-center gap-1.5 shadow-xs transition-colors"
                  >
                    <Download className="w-3.5 h-3.5" />
                    <span>Download Markdown</span>
                  </button>
                </div>
              </div>
            </div>

            {/* Customization Options Box */}
            <div className="p-6 rounded-3xl bg-white border border-slate-200/90 shadow-xl space-y-4">
              <div className="flex items-center justify-between">
                <h3 className="text-sm font-black uppercase tracking-wider text-slate-800 font-mono flex items-center gap-1.5">
                  <Filter className="w-4 h-4 text-[#FF2E55]" />
                  <span>Report Customization & Filters</span>
                </h3>
                <span className="text-[10px] text-slate-400 font-mono">
                  Active Filter: {filteredFindings.length} of {findings.length} findings
                </span>
              </div>

              {/* Category & Severity Selectors */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-1">
                <div>
                  <label className="text-xs font-bold text-slate-700 block mb-1">Filter by Category:</label>
                  <select
                    value={customization.filterCategory}
                    onChange={(e) => setCustomization((prev) => ({ ...prev, filterCategory: e.target.value }))}
                    className="w-full bg-slate-50 border border-slate-200 rounded-xl px-3 py-2 text-xs font-bold text-slate-800 focus:outline-none focus:border-[#FF2E55]"
                  >
                    <option value="all">All Finding Categories ({findings.length})</option>
                    <option value="Potentially unused code">Potentially unused code</option>
                    <option value="Duplicate code">Duplicate code clones</option>
                    <option value="Circular dependencies">Circular dependencies</option>
                    <option value="Potentially unused files">Potentially unused files</option>
                    <option value="High-risk hotspots">High-risk hotspots</option>
                  </select>
                </div>

                <div>
                  <label className="text-xs font-bold text-slate-700 block mb-1">Filter by Severity:</label>
                  <select
                    value={customization.filterSeverity}
                    onChange={(e) => setCustomization((prev) => ({ ...prev, filterSeverity: e.target.value }))}
                    className="w-full bg-slate-50 border border-slate-200 rounded-xl px-3 py-2 text-xs font-bold text-slate-800 focus:outline-none focus:border-[#FF2E55]"
                  >
                    <option value="all">All Severities</option>
                    <option value="Critical">Critical Severity</option>
                    <option value="High">High Severity</option>
                    <option value="Medium">Medium Severity</option>
                    <option value="Low">Low Severity</option>
                  </select>
                </div>
              </div>

              {/* Section Inclusion Checkboxes */}
              <div className="pt-3 border-t border-slate-100 space-y-2">
                <span className="text-xs font-bold text-slate-700 block">Include Report Sections:</span>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs">
                  <label className="flex items-center gap-2 p-2 rounded-xl bg-slate-50 border border-slate-200/80 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={customization.includeExecutiveSummary}
                      onChange={(e) => setCustomization((prev) => ({ ...prev, includeExecutiveSummary: e.target.checked }))}
                      className="accent-[#FF2E55] w-4 h-4 rounded"
                    />
                    <span className="font-medium text-slate-700">Executive Summary & Health</span>
                  </label>

                  <label className="flex items-center gap-2 p-2 rounded-xl bg-slate-50 border border-slate-200/80 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={customization.includeFindingsOverview}
                      onChange={(e) => setCustomization((prev) => ({ ...prev, includeFindingsOverview: e.target.checked }))}
                      className="accent-[#FF2E55] w-4 h-4 rounded"
                    />
                    <span className="font-medium text-slate-700">Detailed Findings Breakdown</span>
                  </label>

                  <label className="flex items-center gap-2 p-2 rounded-xl bg-slate-50 border border-slate-200/80 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={customization.includeDependencyImpact}
                      onChange={(e) => setCustomization((prev) => ({ ...prev, includeDependencyImpact: e.target.checked }))}
                      className="accent-[#FF2E55] w-4 h-4 rounded"
                    />
                    <span className="font-medium text-slate-700">Dependency & Cycle Impact</span>
                  </label>

                  <label className="flex items-center gap-2 p-2 rounded-xl bg-slate-50 border border-slate-200/80 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={customization.includeVerificationChecklist}
                      onChange={(e) => setCustomization((prev) => ({ ...prev, includeVerificationChecklist: e.target.checked }))}
                      className="accent-[#FF2E55] w-4 h-4 rounded"
                    />
                    <span className="font-medium text-slate-700">Responsible Verification Checklist</span>
                  </label>
                </div>
              </div>
            </div>
          </div>

          {/* Right Column: Generation History & Caveat (4 Cols) */}
          <div className="lg:col-span-4 space-y-6">
            {/* Previously Generated Reports */}
            <div className="p-5 rounded-3xl bg-white border border-slate-200/90 shadow-xl space-y-3">
              <div className="flex items-center justify-between">
                <h4 className="text-xs font-black uppercase tracking-wider text-slate-800 font-mono flex items-center gap-1.5">
                  <Clock className="w-3.5 h-3.5 text-slate-400" />
                  <span>Recent Audit History</span>
                </h4>
                <span className="text-[10px] text-slate-400 font-mono">{reportHistory.length} files</span>
              </div>

              <div className="space-y-2">
                {reportHistory.map((item) => (
                  <div
                    key={item.id}
                    className="p-3 rounded-2xl bg-slate-50 border border-slate-200/80 flex items-center justify-between gap-2"
                  >
                    <div>
                      <div className="flex items-center gap-1.5">
                        <span className="text-[10px] font-mono font-bold px-1.5 py-0.2 rounded bg-slate-200 text-slate-700">
                          {item.format}
                        </span>
                        <span className="text-xs font-bold text-slate-800">{item.id}</span>
                      </div>
                      <div className="text-[10px] text-slate-400 font-mono mt-0.5">
                        {item.generatedAt} &bull; {item.fileSize || '120 KB'}
                      </div>
                    </div>

                    <button
                      onClick={() => {
                        if (item.format === 'PDF') handleExportPdf();
                        else if (item.format === 'JSON') handleExportJson();
                        else if (item.format === 'CSV') handleExportCsv();
                        else handleExportMarkdown();
                      }}
                      className="p-1.5 rounded-xl hover:bg-slate-200 text-slate-600 hover:text-[#FF2E55] transition-colors"
                      title="Download again"
                    >
                      <Download className="w-3.5 h-3.5" />
                    </button>
                  </div>
                ))}
              </div>
            </div>

            {/* Static Analysis Disclaimer Notice */}
            <div className="p-4 rounded-3xl bg-red-50/70 border border-red-200 text-xs text-red-950 space-y-2 leading-relaxed">
              <div className="flex items-center gap-1.5 font-black uppercase text-red-700 text-[11px]">
                <AlertTriangle className="w-4 h-4 text-[#FF2E55]" />
                <span>Static Analysis Safety Boundary</span>
              </div>
              <p className="font-medium text-[11px]">
                CodeImpact reports categorize potential tech debt and circular cycles. Static AST analysis cannot mathematically prove that code is completely unused due to dynamic imports, reflection, or downstream consumption.
              </p>
              <div className="pt-1 text-[10px] text-red-800/80 font-mono">
                Always review automated test results before merging refactoring PRs.
              </div>
            </div>
          </div>
        </div>
      )}

      {/* 6. Tab Content: Live Interactive Report Preview */}
      {activeTab === 'preview' && (
        <div className="rounded-3xl bg-white border border-slate-200 shadow-xl overflow-hidden p-6 sm:p-8 space-y-6 max-w-5xl mx-auto">
          {/* Preview Action Bar */}
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-4 border-b border-slate-200">
            <div>
              <span className="text-[10px] font-black uppercase tracking-wider text-[#FF2E55] bg-red-50 px-2.5 py-0.5 rounded-full border border-red-200">
                Live Interactive Report Preview
              </span>
              <h3 className="text-lg font-black text-slate-900 mt-1">CodeImpact Audit Report Preview</h3>
            </div>

            <div className="flex items-center gap-2">
              <button
                onClick={handleExportPdf}
                className="px-3.5 py-2 rounded-xl bg-[#FF2E55] text-white text-xs font-bold shadow-md shadow-red-500/20 flex items-center gap-1.5 hover:bg-red-600 transition-colors"
              >
                <Printer className="w-3.5 h-3.5" />
                <span>Print / Save PDF</span>
              </button>

              <button
                onClick={handleExportJson}
                className="px-3 py-2 rounded-xl bg-slate-900 text-white text-xs font-bold flex items-center gap-1.5 hover:bg-slate-800 transition-colors"
              >
                <Download className="w-3.5 h-3.5" />
                <span>JSON</span>
              </button>

              <button
                onClick={handleExportCsv}
                className="px-3 py-2 rounded-xl bg-emerald-600 text-white text-xs font-bold flex items-center gap-1.5 hover:bg-emerald-700 transition-colors"
              >
                <Download className="w-3.5 h-3.5" />
                <span>CSV</span>
              </button>
            </div>
          </div>

          {/* Report Document Surface */}
          <div className="space-y-6 text-slate-800 font-sans">
            {/* Report Header */}
            <div className="border-b-2 border-[#FF2E55] pb-4 flex flex-col sm:flex-row justify-between sm:items-end gap-3">
              <div>
                <h1 className="text-2xl font-black text-[#FF2E55] tracking-tight">CodeImpact</h1>
                <p className="text-xs text-slate-500 font-medium">Automated Codebase Cleanup & Dependency Risk Assessment</p>
              </div>

              <div className="text-left sm:text-right text-xs font-mono text-slate-500 space-y-0.5">
                <div><strong>Repository:</strong> {summary.repoUrl.replace('https://github.com/', '')}</div>
                <div><strong>Branch:</strong> {summary.branch} | <strong>Date:</strong> {new Date().toLocaleDateString()}</div>
                <div><strong>Audit ID:</strong> CIP-{Date.now()}</div>
              </div>
            </div>

            {/* Section A: Executive Summary */}
            {customization.includeExecutiveSummary && (
              <div className="space-y-3">
                <h3 className="text-sm font-black uppercase text-slate-900 tracking-wider">
                  1. Executive Summary
                </h3>
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-center">
                  <div className="p-3 rounded-xl bg-slate-50 border border-slate-200">
                    <span className="text-base font-black text-slate-900">{filteredFindings.length}</span>
                    <span className="text-[10px] text-slate-500 uppercase block font-bold">Total Findings</span>
                  </div>
                  <div className="p-3 rounded-xl bg-slate-50 border border-slate-200">
                    <span className="text-base font-black text-[#FF2E55]">{summary.circularCyclesCount}</span>
                    <span className="text-[10px] text-slate-500 uppercase block font-bold">Circular Cycles</span>
                  </div>
                  <div className="p-3 rounded-xl bg-slate-50 border border-slate-200">
                    <span className="text-base font-black text-rose-600">{summary.hotspotRiskIndex}/100</span>
                    <span className="text-[10px] text-slate-500 uppercase block font-bold">Hotspot Risk</span>
                  </div>
                  <div className="p-3 rounded-xl bg-slate-50 border border-slate-200">
                    <span className="text-base font-black text-emerald-600">{summary.healthScore}</span>
                    <span className="text-[10px] text-slate-500 uppercase block font-bold">Health Score</span>
                  </div>
                </div>
              </div>
            )}

            {/* Section B: Findings Breakdown */}
            {customization.includeFindingsOverview && (
              <div className="space-y-3">
                <h3 className="text-sm font-black uppercase text-slate-900 tracking-wider">
                  2. Priority Findings Overview ({filteredFindings.length})
                </h3>

                {filteredFindings.length === 0 ? (
                  <p className="text-xs text-slate-400 italic">No findings match the selected category and severity filters.</p>
                ) : (
                  <div className="space-y-3">
                    {filteredFindings.map((f, idx) => (
                      <div key={f.id} className="p-4 rounded-2xl bg-slate-50 border border-slate-200 space-y-2">
                        <div className="flex items-center justify-between gap-2">
                          <span className="text-xs font-black text-slate-900 font-mono">
                            {idx + 1}. [{f.id}] {f.title}
                          </span>
                          <span className={`text-[10px] font-bold px-2 py-0.5 rounded uppercase font-mono ${
                            f.severity === 'Critical' || f.severity === 'High'
                              ? 'bg-red-100 text-red-700'
                              : 'bg-amber-100 text-amber-800'
                          }`}>
                            {f.severity} Risk
                          </span>
                        </div>

                        <div className="text-[11px] text-slate-500 font-mono">
                          {f.file} ({f.lines}) &bull; Analyzer: <strong>{f.analyzer}</strong> &bull; Confidence: <strong>{f.confidence}%</strong>
                        </div>

                        <p className="text-xs text-slate-700 leading-relaxed font-medium">
                          {f.description}
                        </p>

                        <div className="pt-1 text-[11px] text-slate-500 font-mono flex items-center gap-4">
                          <span>Inbound: {f.dependencyContext.incoming}</span>
                          <span>Outbound: {f.dependencyContext.outgoing}</span>
                          <span>Tests: {(f.testImpactContext?.testFiles || f.dependencyContext.affectedTests).length} mapped</span>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}

            {/* Section C: Dependency & Cycle Impact */}
            {customization.includeDependencyImpact && (
              <div className="space-y-3 pt-2">
                <h3 className="text-sm font-black uppercase text-slate-900 tracking-wider">
                  3. Dependency & Cycle Impact
                </h3>
                <div className="p-4 rounded-2xl bg-slate-50 border border-slate-200 space-y-2 text-xs text-slate-700">
                  <p>
                    Analyzed <strong>{graphNodes.length} module nodes</strong> connected by <strong>{graphEdges.length} static import edges</strong>.
                  </p>
                  <p>
                    <strong>{summary.circularCyclesCount} active circular cycle(s)</strong> detected by Madge analyzer (<code className="text-[#FF2E55] font-mono">sessionProvider.tsx ⇄ userProfile.tsx</code>).
                  </p>
                </div>
              </div>
            )}

            {/* Section D: Verification Checklist */}
            {customization.includeVerificationChecklist && (
              <div className="space-y-3 pt-2">
                <h3 className="text-sm font-black uppercase text-slate-900 tracking-wider">
                  4. Responsible Verification Checklist
                </h3>
                <div className="p-4 rounded-2xl bg-amber-50/80 border border-amber-200 space-y-2 text-xs text-amber-950">
                  <ul className="space-y-1.5 list-disc list-inside">
                    <li>Verify whether flagged files are accessed via dynamic import statements or runtime reflection.</li>
                    <li>Run automated test suites targeting caller components before removing symbols.</li>
                    <li>If modifying circular dependencies, extract shared interface contracts into isolated type files.</li>
                    <li>Never execute automatic deletion without manual engineering confirmation.</li>
                  </ul>
                </div>
              </div>
            )}

            {/* Static Analysis Caveat Banner */}
            <div className="p-4 rounded-2xl bg-slate-100 border border-slate-200 text-xs text-slate-600 space-y-1">
              <strong className="text-slate-800 font-bold block">Static Analysis Limitation Notice:</strong>
              <p className="text-[11px] leading-relaxed">
                Findings in this report represent candidates for engineering review. Static analysis cannot mathematically prove that code is completely unused due to runtime dynamics, reflection, or external consumers.
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
