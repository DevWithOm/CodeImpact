import React from 'react';
import {
  Zap,
  Activity,
  Layers,
  GitBranch,
  Sparkles,
  Cpu,
  Radio,
  Flame,
  FileDown
} from 'lucide-react';

interface NavbarProps {
  activeTab: string;
  setActiveTab: (tab: string) => void;
  onTriggerScan: () => void;
  isScanning: boolean;
  onOpenReport?: () => void;
}

export const Navbar: React.FC<NavbarProps> = ({
  activeTab,
  setActiveTab,
  onTriggerScan,
  isScanning,
  onOpenReport
}) => {
  const navTabs = [
    { id: 'overview', label: 'Overview', icon: Activity },
    { id: 'findings', label: 'Findings', icon: Layers },
    { id: 'graph', label: 'Dependency Graph', icon: GitBranch },
    { id: 'ai', label: 'Contextual AI', icon: Sparkles },
    { id: 'matrix', label: 'Competitor Matrix', icon: Cpu }
  ];

  return (
    <>
      {/* Laser Top Accent Line */}
      <div className="h-1.5 w-full bg-gradient-to-r from-red-600 via-[#FF2E55] to-rose-500 animate-pulse shadow-lg shadow-red-500/50" />

      {/* Marquee Dynamic Ticker Ribbon */}
      <div className="bg-[#0F0F12] text-white py-1.5 px-4 text-[11px] font-mono tracking-wider flex items-center overflow-hidden whitespace-nowrap border-b border-red-900/50 select-none">
        <div className="flex items-center gap-6 animate-marquee">
          <span className="flex items-center gap-1.5 text-red-400 font-bold">
            <Flame className="w-3.5 h-3.5 text-[#FF2E55]" /> CODEIMPACT RED SCANNER LIVE
          </span>
          <span className="text-slate-400">• UNUSED EXPORTS CHECK: ACTIVE</span>
          <span className="text-slate-400">• AST CLONE DETECTOR: ONLINE</span>
          <span className="text-[#FF2E55] font-bold">• CIRCULAR CYCLE DETECTED IN AUTH MODULE</span>
          <span className="text-slate-400">• RESPONSIBLE RECOMMENDATION ENGINE: READY</span>
          <span className="text-slate-500">• NEVER AUTO-DELETE CODE WITHOUT DEPENDENCY VERIFICATION</span>
        </div>
      </div>

      {/* Sticky Main Navigation Header */}
      <header className="sticky top-0 z-40 backdrop-blur-xl bg-white/85 border-b border-red-100 shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">

          {/* Logo & Product Name */}
          <div
            onClick={() => setActiveTab('overview')}
            className="flex items-center gap-3 cursor-pointer group"
          >
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-[#FF2E55] to-red-700 p-0.5 shadow-md shadow-red-500/20 group-hover:rotate-6 transition-transform">
              <div className="w-full h-full bg-white rounded-[10px] flex items-center justify-center">
                <Zap className="w-5 h-5 text-[#FF2E55] fill-[#FF2E55]" />
              </div>
            </div>
            <div>
              <span className="font-black text-xl tracking-tight text-slate-900 uppercase">
                Code<span className="text-[#FF2E55]">Impact</span>
              </span>
              <span className="ml-2 px-2 py-0.5 text-[10px] font-black tracking-widest uppercase rounded-full bg-red-50 text-[#FF2E55] border border-red-200">
                GEN-Z RED
              </span>
            </div>
          </div>

          {/* Desktop Navigation Tabs */}
          <nav className="hidden md:flex items-center gap-1 bg-slate-100 p-1 rounded-2xl border border-slate-200">
            {navTabs.map((tab) => {
              const Icon = tab.icon;
              const isActive = activeTab === tab.id;
              return (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`flex items-center gap-2 px-3.5 py-1.5 rounded-xl text-xs font-extrabold transition-all duration-200 ${
                    isActive
                      ? 'bg-[#FF2E55] text-white shadow-md shadow-red-500/30 scale-105'
                      : 'text-slate-600 hover:text-slate-900 hover:bg-slate-200/60'
                  }`}
                >
                  <Icon className="w-3.5 h-3.5" />
                  {tab.label}
                </button>
              );
            })}
          </nav>

          {/* Actions: Export Report & Trigger Scan */}
          <div className="flex items-center gap-2 sm:gap-3">
            {onOpenReport && (
              <button
                onClick={onOpenReport}
                className="hidden sm:flex items-center gap-1.5 px-3 py-2 text-xs font-bold text-slate-700 hover:text-[#FF2E55] bg-slate-50 hover:bg-red-50 border border-slate-200 hover:border-red-200 rounded-xl transition-all"
                title="Export Analysis Report"
              >
                <FileDown className="w-3.5 h-3.5 text-[#FF2E55]" />
                <span>Export</span>
              </button>
            )}

            <button
              onClick={onTriggerScan}
              disabled={isScanning}
              className="px-4 py-2 text-xs font-black uppercase tracking-wider text-white bg-gradient-to-r from-[#FF2E55] to-red-700 rounded-xl shadow-lg shadow-red-500/25 hover:shadow-red-500/40 hover:scale-105 active:scale-95 transition-all flex items-center gap-2 disabled:opacity-60 disabled:cursor-not-allowed"
            >
              <Radio className={`w-3.5 h-3.5 ${isScanning ? 'animate-spin' : 'animate-pulse'}`} />
              <span>{isScanning ? 'Analyzing...' : 'Trigger Scan'}</span>
            </button>
          </div>

        </div>
      </header>

      {/* Mobile Navigation Scroll Ribbon */}
      <div className="md:hidden flex overflow-x-auto gap-2 px-4 py-3 bg-white border-b border-slate-200 no-scrollbar">
        {navTabs.map((tab) => {
          const Icon = tab.icon;
          const isActive = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-bold whitespace-nowrap transition-all ${
                isActive
                  ? 'bg-[#FF2E55] text-white shadow-md'
                  : 'bg-slate-50 text-slate-700 border border-slate-200'
              }`}
            >
              <Icon className="w-3.5 h-3.5" />
              {tab.label}
            </button>
          );
        })}
      </div>
    </>
  );
};
