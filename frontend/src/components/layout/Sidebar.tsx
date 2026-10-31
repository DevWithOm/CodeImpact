import React from 'react';
import {
  Activity,
  Layers,
  GitBranch,
  Sparkles,
  Cpu,
  FileText,
  ShieldCheck,
  Zap,
  ChevronLeft,
  ChevronRight,
  ExternalLink
} from 'lucide-react';

interface SidebarProps {
  activeTab: string;
  setActiveTab: (tab: string) => void;
  isCollapsed: boolean;
  setIsCollapsed: (collapsed: boolean) => void;
  activeRepo: string;
  branch?: string;
  onOpenReport?: () => void;
}

export const Sidebar: React.FC<SidebarProps> = ({
  activeTab,
  setActiveTab,
  isCollapsed,
  setIsCollapsed,
  activeRepo,
  branch = 'main',
  onOpenReport
}) => {
  const navItems = [
    { id: 'overview', label: 'Overview', icon: Activity, badge: null },
    { id: 'findings', label: 'Findings', icon: Layers, badge: '5' },
    { id: 'graph', label: 'Dependency Graph', icon: GitBranch, badge: 'Cycle' },
    { id: 'ai', label: 'Contextual AI', icon: Sparkles, badge: 'Gemma 4' },
    { id: 'matrix', label: 'Competitor Matrix', icon: Cpu, badge: null }
  ];

  const repoName = activeRepo.replace('https://github.com/', '').trim();

  return (
    <aside
      className={`hidden lg:flex flex-col border-r border-red-100/80 bg-white z-30 transition-all duration-300 select-none ${
        isCollapsed ? 'w-20' : 'w-64'
      }`}
    >
      {/* Brand Header */}
      <div className="h-16 px-4 flex items-center justify-between border-b border-red-100">
        <div
          onClick={() => setActiveTab('overview')}
          className="flex items-center gap-3 cursor-pointer overflow-hidden"
        >
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-[#FF2E55] to-red-700 p-0.5 shadow-md shadow-red-500/20 shrink-0">
            <div className="w-full h-full bg-white rounded-[10px] flex items-center justify-center">
              <Zap className="w-5 h-5 text-[#FF2E55] fill-[#FF2E55]" />
            </div>
          </div>
          {!isCollapsed && (
            <div className="leading-tight">
              <span className="font-black text-lg tracking-tight text-slate-900 uppercase">
                Code<span className="text-[#FF2E55]">Impact</span>
              </span>
              <div className="text-[9px] font-black tracking-widest uppercase text-[#FF2E55]">
                GEN-Z RED ENGINE
              </div>
            </div>
          )}
        </div>

        <button
          onClick={() => setIsCollapsed(!isCollapsed)}
          className="p-1.5 rounded-lg text-slate-400 hover:text-slate-700 hover:bg-slate-100 transition-colors"
          title={isCollapsed ? 'Expand Sidebar' : 'Collapse Sidebar'}
        >
          {isCollapsed ? <ChevronRight className="w-4 h-4" /> : <ChevronLeft className="w-4 h-4" />}
        </button>
      </div>

      {/* Navigation Menu */}
      <nav className="flex-1 px-3 py-4 space-y-1.5 overflow-y-auto">
        <div className="px-2 pb-2 text-[10px] font-black uppercase tracking-wider text-slate-400">
          {!isCollapsed && 'Navigation'}
        </div>

        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = activeTab === item.id;
          return (
            <button
              key={item.id}
              onClick={() => setActiveTab(item.id)}
              className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-2xl text-xs font-extrabold transition-all duration-200 group relative ${
                isActive
                  ? 'bg-gradient-to-r from-[#FF2E55] to-red-600 text-white shadow-md shadow-red-500/25'
                  : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100/80'
              }`}
              title={isCollapsed ? item.label : undefined}
            >
              <Icon className={`w-4 h-4 shrink-0 ${isActive ? 'text-white' : 'text-slate-500 group-hover:text-[#FF2E55]'}`} />

              {!isCollapsed && (
                <div className="flex-1 flex items-center justify-between text-left">
                  <span>{item.label}</span>
                  {item.badge && (
                    <span
                      className={`text-[9px] font-black uppercase px-2 py-0.5 rounded-full ${
                        isActive
                          ? 'bg-white/20 text-white'
                          : item.badge === 'Cycle'
                          ? 'bg-red-100 text-[#FF2E55]'
                          : 'bg-slate-200 text-slate-700'
                      }`}
                    >
                      {item.badge}
                    </span>
                  )}
                </div>
              )}
            </button>
          );
        })}

        {/* Export Report Action in Nav */}
        {onOpenReport && (
          <button
            onClick={onOpenReport}
            className="w-full flex items-center gap-3 px-3 py-2.5 rounded-2xl text-xs font-extrabold text-slate-600 hover:text-[#FF2E55] hover:bg-red-50/60 transition-all duration-200 group"
            title={isCollapsed ? 'Export Report' : undefined}
          >
            <FileText className="w-4 h-4 text-slate-500 group-hover:text-[#FF2E55] shrink-0" />
            {!isCollapsed && <span>Audit Report</span>}
          </button>
        )}
      </nav>

      {/* Active Workspace / Target Box */}
      {!isCollapsed ? (
        <div className="p-3 m-3 rounded-2xl bg-slate-50 border border-slate-200 space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-[10px] font-black uppercase text-slate-400">Target Workspace</span>
            <span className="text-[10px] font-mono text-emerald-600 font-bold bg-emerald-50 px-1.5 py-0.5 rounded">
              Ready
            </span>
          </div>
          <div className="font-mono text-xs font-bold text-slate-800 truncate" title={repoName}>
            {repoName || 'facebook/react'}
          </div>
          <div className="text-[11px] text-slate-500 font-mono flex items-center justify-between">
            <span>Branch:</span>
            <span className="text-slate-700 font-bold">{branch}</span>
          </div>
          <div className="pt-1.5 border-t border-slate-200 flex items-center gap-1.5 text-[10px] text-slate-500 font-medium">
            <ShieldCheck className="w-3.5 h-3.5 text-[#FF2E55] shrink-0" />
            <span>Static verification guardrails active</span>
          </div>
        </div>
      ) : (
        <div className="p-3 flex justify-center border-t border-slate-100">
          <div className="w-8 h-8 rounded-xl bg-slate-100 flex items-center justify-center text-[#FF2E55]" title={`Target: ${repoName}`}>
            <ShieldCheck className="w-4 h-4" />
          </div>
        </div>
      )}
    </aside>
  );
};
