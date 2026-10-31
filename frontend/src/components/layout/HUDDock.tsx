import React from 'react';
import { Activity } from 'lucide-react';

interface HUDDockProps {
  findingsCount: number;
  healthScore?: string;
  isScanning: boolean;
}

export const HUDDock: React.FC<HUDDockProps> = ({
  findingsCount,
  healthScore = '89%',
  isScanning
}) => {
  return (
    <div className="fixed bottom-4 right-4 z-50 bg-[#0F0F12]/95 backdrop-blur-md text-white px-4 py-2.5 rounded-2xl border border-red-900/60 shadow-2xl flex items-center gap-3 text-xs font-mono select-none">
      <span className="flex h-2 w-2 relative">
        <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-red-400 opacity-75"></span>
        <span className="relative inline-flex rounded-full h-2 w-2 bg-[#FF2E55]"></span>
      </span>
      <span className="font-bold text-red-400 flex items-center gap-1.5">
        <span>RED MODE ENGINE</span>
      </span>
      <span className="text-slate-600">|</span>
      <span className="text-slate-300">
        {isScanning ? 'Scan in progress' : `${findingsCount} Active Findings`}
      </span>
      <span className="text-slate-600 hidden sm:inline">|</span>
      <span className="text-emerald-400 font-bold hidden sm:inline">Health: {healthScore}</span>
    </div>
  );
};
