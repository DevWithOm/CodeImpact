import React from 'react';
import { Cpu, Sparkles, Check, X, Shield, ArrowUpRight } from 'lucide-react';
import { CompetitorRow } from '../../types';

interface CompetitorMatrixProps {
  competitors: CompetitorRow[];
}

export const CompetitorMatrix: React.FC<CompetitorMatrixProps> = ({ competitors }) => {
  return (
    <div className="space-y-6 animate-fadeIn">
      <div className="p-6 sm:p-8 rounded-3xl bg-white border border-red-100 shadow-xl space-y-6">
        <div>
          <h3 className="text-xl font-black text-slate-900 flex items-center gap-2">
            <Cpu className="w-5 h-5 text-[#FF2E55]" />
            Competitive Landscape Matrix
          </h3>
          <p className="text-xs sm:text-sm text-slate-500 font-medium mt-1">
            How existing standalone static analysis tools compare against CodeImpact's unified context framework.
          </p>
        </div>

        {/* Matrix Table */}
        <div className="overflow-x-auto rounded-2xl border border-slate-200">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="border-b border-slate-200 text-[11px] font-black uppercase text-slate-400 bg-slate-50">
                <th className="p-4">Tool</th>
                <th className="p-4">Primary Purpose</th>
                <th className="p-4">Evidence Clarity</th>
                <th className="p-4">Impact Risk Context</th>
                <th className="p-4">Cycle Support</th>
                <th className="p-4">Grounded AI</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 text-xs font-medium">
              {competitors.map((row) => (
                <tr
                  key={row.tool}
                  className={
                    row.isUs
                      ? 'bg-gradient-to-r from-red-50 to-rose-50 font-extrabold border-l-4 border-l-[#FF2E55]'
                      : 'hover:bg-slate-50 transition-colors'
                  }
                >
                  <td className="p-4 font-black text-slate-900 flex items-center gap-2">
                    {row.isUs && <Sparkles className="w-4 h-4 text-[#FF2E55]" />}
                    <span className={row.isUs ? 'text-[#FF2E55] text-sm' : ''}>{row.tool}</span>
                    {row.isUs && (
                      <span className="px-1.5 py-0.5 rounded text-[9px] bg-[#FF2E55] text-white uppercase tracking-wider font-bold">
                        This App
                      </span>
                    )}
                  </td>
                  <td className="p-4 text-slate-600">{row.focus}</td>
                  <td className="p-4">
                    <span
                      className={`px-2 py-0.5 rounded text-[11px] font-bold ${
                        row.evidence.includes('High') || row.evidence.includes('Multi')
                          ? 'bg-emerald-50 text-emerald-700'
                          : 'bg-slate-100 text-slate-600'
                      }`}
                    >
                      {row.evidence}
                    </span>
                  </td>
                  <td className="p-4">
                    <span
                      className={`px-2 py-0.5 rounded text-[11px] font-bold ${
                        row.impact.includes('Deep') || row.impact.includes('High')
                          ? 'bg-emerald-50 text-emerald-700'
                          : row.impact === 'None'
                          ? 'bg-rose-50 text-rose-700'
                          : 'bg-slate-100 text-slate-600'
                      }`}
                    >
                      {row.impact}
                    </span>
                  </td>
                  <td className="p-4">{row.cycle}</td>
                  <td className="p-4">
                    <span
                      className={`px-2 py-0.5 rounded text-[11px] font-bold ${
                        row.ai.includes('Grounded') || row.ai.includes('Strong')
                          ? 'bg-red-50 text-[#FF2E55]'
                          : 'bg-slate-100 text-slate-600'
                      }`}
                    >
                      {row.ai}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* Value Prop Summary */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 pt-2">
          <div className="p-4 rounded-2xl bg-slate-50 border border-slate-200 space-y-1">
            <h4 className="text-xs font-black uppercase text-slate-800">No Siloed Analysers</h4>
            <p className="text-xs text-slate-600">
              Knip flags exports, Madge traces cycles, and jscpd finds clones. CodeImpact correlates them into a single graph.
            </p>
          </div>
          <div className="p-4 rounded-2xl bg-slate-50 border border-slate-200 space-y-1">
            <h4 className="text-xs font-black uppercase text-slate-800">Dependency Blast Radius</h4>
            <p className="text-xs text-slate-600">
              Shows how many modules and tests rely on flagged code so you never delete something with high downstream risk.
            </p>
          </div>
          <div className="p-4 rounded-2xl bg-slate-50 border border-slate-200 space-y-1">
            <h4 className="text-xs font-black uppercase text-slate-800">Grounded Reliability</h4>
            <p className="text-xs text-slate-600">
              The AI never invents facts or claims safety. It presents deterministic evidence and guided manual verification.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};
