import React from 'react';
import { History, GitBranch, ArrowUpRight, CheckCircle2, Clock, AlertCircle } from 'lucide-react';

export interface RecentAnalysisItem {
  id: string;
  repo: string;
  branch: string;
  timestamp: string;
  healthScore: string;
  findingsCount: number;
  status: 'Completed' | 'Analyzing' | 'Cached';
  isMockFixture?: boolean;
}

interface RecentActivityProps {
  items: RecentAnalysisItem[];
  onSelectRepo: (repo: string) => void;
}

export const RecentActivity: React.FC<RecentActivityProps> = ({ items, onSelectRepo }) => {
  return (
    <div className="p-6 rounded-3xl bg-white border border-red-100 shadow-xl shadow-red-500/5 space-y-4">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-xl bg-red-50 text-[#FF2E55] flex items-center justify-center border border-red-200">
            <History className="w-4 h-4" />
          </div>
          <div>
            <h3 className="text-base font-black text-slate-900">Recent Analysis Runs & Pipeline Activity</h3>
            <p className="text-xs text-slate-500 font-medium">
              Cached scan snapshots and previous repository cleanup evaluations
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <span className="px-2.5 py-1 rounded-full text-[10px] font-mono font-bold bg-amber-50 text-amber-800 border border-amber-200 flex items-center gap-1">
            <AlertCircle className="w-3 h-3 text-amber-600" />
            <span>MOCK DATA: DEMO FIXTURES</span>
          </span>
        </div>
      </div>

      <div className="overflow-x-auto rounded-2xl border border-slate-100">
        <table className="w-full text-left border-collapse">
          <thead>
            <tr className="border-b border-slate-200 text-[10px] font-black uppercase text-slate-400 bg-slate-50 font-mono">
              <th className="py-3 px-4">Repository</th>
              <th className="py-3 px-4">Branch</th>
              <th className="py-3 px-4">Health Index</th>
              <th className="py-3 px-4">Flagged Findings</th>
              <th className="py-3 px-4">Time</th>
              <th className="py-3 px-4">Status</th>
              <th className="py-3 px-4 text-right">Action</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100 text-xs font-medium">
            {items.map((item) => (
              <tr key={item.id} className="hover:bg-slate-50/80 transition-colors group">
                <td className="py-3.5 px-4 font-bold text-slate-900 font-mono flex items-center gap-2">
                  <GitBranch className="w-3.5 h-3.5 text-[#FF2E55]" />
                  <span>{item.repo}</span>
                </td>
                <td className="py-3.5 px-4 text-slate-600 font-mono text-[11px]">{item.branch}</td>
                <td className="py-3.5 px-4">
                  <span className="px-2 py-0.5 rounded-full text-[11px] font-black bg-red-50 text-[#FF2E55] border border-red-200">
                    {item.healthScore}
                  </span>
                </td>
                <td className="py-3.5 px-4 text-slate-700 font-bold">{item.findingsCount} issues</td>
                <td className="py-3.5 px-4 text-slate-500 font-mono text-[11px] flex items-center gap-1">
                  <Clock className="w-3 h-3 text-slate-400" />
                  <span>{item.timestamp}</span>
                </td>
                <td className="py-3.5 px-4">
                  <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-extrabold uppercase bg-emerald-50 text-emerald-700 border border-emerald-200">
                    <CheckCircle2 className="w-3 h-3 text-emerald-600" />
                    <span>{item.status}</span>
                  </span>
                </td>
                <td className="py-3.5 px-4 text-right">
                  <button
                    onClick={() => onSelectRepo(`https://github.com/${item.repo}`)}
                    className="px-2.5 py-1 text-xs font-bold text-slate-700 hover:text-[#FF2E55] bg-white hover:bg-red-50 border border-slate-200 hover:border-red-200 rounded-lg transition-all inline-flex items-center gap-1 group-hover:border-red-200"
                  >
                    <span>Load</span>
                    <ArrowUpRight className="w-3 h-3" />
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};
