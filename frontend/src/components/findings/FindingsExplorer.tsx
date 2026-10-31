import React, { useState, useMemo } from 'react';
import {
  Search,
  Filter,
  ArrowUpDown,
  RotateCcw,
  Layers,
  FileCode,
  Cpu,
  AlertTriangle,
  CheckCircle2,
  SlidersHorizontal,
  ChevronRight,
  ShieldCheck,
  ShieldAlert
} from 'lucide-react';
import { Finding, FindingCategory, FindingSeverity, ReviewStatus } from '../../types';
import { EvidenceDrawer } from './EvidenceDrawer';
import { RiskBadge } from './RiskBadge';

interface FindingsExplorerProps {
  findings: Finding[];
  activeFinding: Finding | null;
  setActiveFinding: (finding: Finding) => void;
  onUpdateReviewStatus: (findingId: string, status: ReviewStatus) => void;
  onAskAI?: (finding: Finding) => void;
  onViewInGraph?: (finding: Finding) => void;
}

type SortOption = 'priority' | 'severity' | 'confidence' | 'file';

export const FindingsExplorer: React.FC<FindingsExplorerProps> = ({
  findings,
  activeFinding,
  setActiveFinding,
  onUpdateReviewStatus,
  onAskAI,
  onViewInGraph
}) => {
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCategory, setSelectedCategory] = useState<string>('All');
  const [selectedSeverity, setSelectedSeverity] = useState<string>('All');
  const [selectedStatus, setSelectedStatus] = useState<string>('All');
  const [sortBy, setSortBy] = useState<SortOption>('priority');

  const categories: Array<{ id: string; label: string }> = [
    { id: 'All', label: 'All Categories' },
    { id: 'Potentially unused code', label: 'Potentially unused code' },
    { id: 'Duplicate code', label: 'Duplicate code' },
    { id: 'Circular dependencies', label: 'Circular dependencies' },
    { id: 'Potentially unused files', label: 'Potentially unused files' },
    { id: 'High-risk hotspots', label: 'High-risk hotspots' }
  ];

  const severities: string[] = ['All', 'Critical', 'High', 'Medium', 'Low'];

  const reviewStatuses: string[] = [
    'All',
    'Pending Review',
    'In Review',
    'Verified for Refactor',
    'False Positive (Keep)',
    'High Risk (Do Not Touch)'
  ];

  // Active filters count
  const activeFiltersCount = (selectedCategory !== 'All' ? 1 : 0) +
    (selectedSeverity !== 'All' ? 1 : 0) +
    (selectedStatus !== 'All' ? 1 : 0) +
    (searchQuery.trim() !== '' ? 1 : 0);

  const handleClearFilters = () => {
    setSearchQuery('');
    setSelectedCategory('All');
    setSelectedSeverity('All');
    setSelectedStatus('All');
    setSortBy('priority');
  };

  // Severity rank for sorting
  const severityRank: Record<FindingSeverity, number> = {
    Critical: 4,
    High: 3,
    Medium: 2,
    Low: 1
  };

  // Filtered and sorted findings
  const filteredFindings = useMemo(() => {
    const list = findings.filter((f) => {
      // 1. Search filter
      const q = searchQuery.toLowerCase();
      const matchSearch =
        !q ||
        f.title.toLowerCase().includes(q) ||
        f.file.toLowerCase().includes(q) ||
        f.category.toLowerCase().includes(q) ||
        f.analyzer.toLowerCase().includes(q);

      // 2. Category filter
      const matchCat =
        selectedCategory === 'All' || f.category === selectedCategory;

      // 3. Severity filter
      const matchSev =
        selectedSeverity === 'All' || f.severity === selectedSeverity;

      // 4. Status filter
      const matchStatus =
        selectedStatus === 'All' || f.reviewStatus === selectedStatus;

      return matchSearch && matchCat && matchSev && matchStatus;
    });

    // Sort list
    return list.sort((a, b) => {
      if (sortBy === 'priority') {
        return b.impactScore - a.impactScore;
      }
      if (sortBy === 'severity') {
        return severityRank[b.severity] - severityRank[a.severity];
      }
      if (sortBy === 'confidence') {
        return b.confidence - a.confidence;
      }
      if (sortBy === 'file') {
        return a.file.localeCompare(b.file);
      }
      return 0;
    });
  }, [findings, searchQuery, selectedCategory, selectedSeverity, selectedStatus, sortBy]);

  return (
    <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 animate-fadeIn">
      {/* Left Column: Filterable List & Controls */}
      <div className="lg:col-span-7 space-y-4">
        {/* Controls Container Card */}
        <div className="p-5 rounded-3xl bg-white border border-red-100 shadow-xl shadow-red-500/5 space-y-4">
          {/* Search bar & Sort Controls */}
          <div className="flex flex-col sm:flex-row gap-3">
            <div className="relative flex-1">
              <Search className="w-4 h-4 text-slate-400 absolute left-3.5 top-3" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search findings by title, file path, or analyzer..."
                className="w-full pl-10 pr-4 py-2.5 bg-slate-50 border border-slate-200 rounded-2xl text-xs sm:text-sm font-bold text-slate-800 placeholder-slate-400 focus:outline-none focus:border-[#FF2E55] transition-colors"
              />
            </div>

            {/* Sort Control */}
            <div className="flex items-center gap-1.5 bg-slate-50 border border-slate-200 rounded-2xl px-3 py-1.5 shrink-0">
              <ArrowUpDown className="w-3.5 h-3.5 text-slate-400" />
              <span className="text-[11px] font-bold text-slate-500">Sort:</span>
              <select
                value={sortBy}
                onChange={(e) => setSortBy(e.target.value as SortOption)}
                className="bg-transparent text-xs font-bold text-slate-800 focus:outline-none cursor-pointer"
              >
                <option value="priority">Impact Priority</option>
                <option value="severity">Severity Rank</option>
                <option value="confidence">Confidence Level</option>
                <option value="file">File Path (A-Z)</option>
              </select>
            </div>
          </div>

          {/* Category Chips */}
          <div className="space-y-1.5">
            <div className="flex items-center justify-between">
              <span className="text-[10px] font-black uppercase text-slate-400 flex items-center gap-1 font-mono">
                <Filter className="w-3 h-3 text-[#FF2E55]" />
                Category:
              </span>
              {activeFiltersCount > 0 && (
                <button
                  onClick={handleClearFilters}
                  className="text-[11px] font-bold text-[#FF2E55] hover:underline flex items-center gap-1 transition-colors"
                >
                  <RotateCcw className="w-3 h-3" />
                  <span>Clear Filters ({activeFiltersCount})</span>
                </button>
              )}
            </div>

            <div className="flex flex-wrap gap-1.5">
              {categories.map((cat) => {
                const isSelected = selectedCategory === cat.id;
                return (
                  <button
                    key={cat.id}
                    onClick={() => setSelectedCategory(cat.id)}
                    className={`px-3 py-1.5 rounded-xl text-xs font-extrabold transition-all ${
                      isSelected
                        ? 'bg-[#FF2E55] text-white shadow-md shadow-red-500/20 scale-102'
                        : 'bg-slate-100 text-slate-600 hover:bg-slate-200/80 hover:text-slate-900'
                    }`}
                  >
                    {cat.label}
                  </button>
                );
              })}
            </div>
          </div>

          {/* Secondary Filters: Severity & Review Status */}
          <div className="pt-3 border-t border-slate-100 grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
            {/* Severity Filter */}
            <div className="flex items-center gap-1.5 flex-wrap">
              <span className="text-[10px] font-black uppercase text-slate-400 font-mono">Severity:</span>
              {severities.map((sev) => (
                <button
                  key={sev}
                  onClick={() => setSelectedSeverity(sev)}
                  className={`px-2 py-0.5 rounded-lg text-[10px] font-black uppercase transition-all ${
                    selectedSeverity === sev
                      ? 'bg-slate-900 text-white'
                      : 'text-slate-600 hover:bg-slate-100'
                  }`}
                >
                  {sev}
                </button>
              ))}
            </div>

            {/* Review Status Filter */}
            <div className="flex items-center gap-1.5 justify-start sm:justify-end">
              <span className="text-[10px] font-black uppercase text-slate-400 font-mono">Status:</span>
              <select
                value={selectedStatus}
                onChange={(e) => setSelectedStatus(e.target.value)}
                className="bg-slate-50 border border-slate-200 rounded-xl px-2 py-1 text-xs font-bold text-slate-700 focus:outline-none focus:border-[#FF2E55]"
              >
                {reviewStatuses.map((st) => (
                  <option key={st} value={st}>{st}</option>
                ))}
              </select>
            </div>
          </div>
        </div>

        {/* Results Counter Bar */}
        <div className="flex items-center justify-between px-2 text-xs text-slate-500 font-mono">
          <span>
            Displaying <strong className="text-slate-900 font-bold">{filteredFindings.length}</strong> of {findings.length} findings
          </span>
          <span className="text-[11px] text-slate-400">
            Click finding to view analyzer evidence & checklist
          </span>
        </div>

        {/* Findings List */}
        <div className="space-y-3">
          {filteredFindings.length === 0 ? (
            <div className="p-12 text-center bg-white rounded-3xl border border-slate-200 shadow-sm space-y-3">
              <div className="w-12 h-12 rounded-2xl bg-red-50 text-[#FF2E55] flex items-center justify-center mx-auto border border-red-200">
                <Filter className="w-6 h-6" />
              </div>
              <h4 className="text-base font-black text-slate-800">No matching findings found</h4>
              <p className="text-xs text-slate-500 max-w-sm mx-auto">
                No items matched your current search and filter combination. Try clearing some filters or searching for another file.
              </p>
              <button
                onClick={handleClearFilters}
                className="px-4 py-2 rounded-xl bg-[#FF2E55] text-white text-xs font-bold shadow-md hover:bg-red-600 transition-colors"
              >
                Clear all filters
              </button>
            </div>
          ) : (
            filteredFindings.map((finding) => {
              const isSelected = activeFinding?.id === finding.id;

              return (
                <div
                  key={finding.id}
                  onClick={() => setActiveFinding(finding)}
                  className={`p-4 sm:p-5 rounded-2xl border transition-all cursor-pointer relative ${
                    isSelected
                      ? 'bg-gradient-to-r from-red-50/90 via-rose-50/50 to-white border-[#FF2E55] shadow-lg shadow-red-500/10 ring-2 ring-[#FF2E55]/30'
                      : 'bg-white border-slate-200/90 hover:border-red-200 hover:bg-slate-50/80 shadow-xs'
                  }`}
                >
                  <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-3">
                    <div className="space-y-1.5 flex-1 min-w-0">
                      {/* Top Badges */}
                      <div className="flex flex-wrap items-center gap-2">
                        <RiskBadge type={finding.severity} />
                        <span className="text-xs font-black text-slate-800">{finding.category}</span>
                        <span className="text-[10px] text-slate-400 font-mono">[{finding.id}]</span>
                        <span className="text-[10px] text-slate-500 font-mono bg-slate-100 px-1.5 py-0.5 rounded">
                          {finding.analyzer}
                        </span>
                        <RiskBadge type={finding.reviewStatus} />
                      </div>

                      {/* Title */}
                      <h4 className="text-sm sm:text-base font-extrabold text-slate-900 leading-snug">
                        {finding.title}
                      </h4>

                      {/* File Path & Line */}
                      <div className="flex items-center gap-1.5 text-xs text-slate-500 font-mono pt-0.5">
                        <FileCode className="w-3.5 h-3.5 text-slate-400 shrink-0" />
                        <span className="truncate">{finding.file}</span>
                        <span className="text-slate-400 shrink-0">({finding.lines})</span>
                      </div>
                    </div>

                    {/* Right Risk & Confidence Box */}
                    <div className="flex sm:flex-col items-center sm:items-end justify-between sm:justify-start gap-1 shrink-0 pt-2 sm:pt-0 border-t sm:border-t-0 border-slate-100">
                      <div className="text-left sm:text-right">
                        <span className={`text-xs font-black block ${
                          finding.impactRiskType === 'high'
                            ? 'text-red-600'
                            : finding.impactRiskType === 'medium'
                            ? 'text-amber-600'
                            : 'text-emerald-600'
                        }`}>
                          {finding.impactRisk}
                        </span>
                        <span className="text-[10px] text-slate-500 font-mono block">
                          Impact: {finding.impactScore}/100
                        </span>
                      </div>

                      <div className="text-right">
                        <span className="text-[10px] text-slate-600 font-mono font-bold bg-slate-100 px-2 py-0.5 rounded">
                          Conf: {finding.confidence}%
                        </span>
                      </div>
                    </div>
                  </div>
                </div>
              );
            })
          )}
        </div>
      </div>

      {/* Right Column: Finding Details & Evidence Panel */}
      <div className="lg:col-span-5">
        <EvidenceDrawer
          finding={activeFinding}
          onAskAI={onAskAI}
          onViewInGraph={onViewInGraph}
          onUpdateReviewStatus={onUpdateReviewStatus}
        />
      </div>
    </div>
  );
};
