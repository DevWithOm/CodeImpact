import React from 'react';
import { RotateCw } from 'lucide-react';

interface LoadingProps {
  label?: string;
  subtext?: string;
}

export const Loading: React.FC<LoadingProps> = ({
  label = 'Analyzing Codebase...',
  subtext = 'Correlating AST, cycle matrices, and clone blocks'
}) => {
  return (
    <div className="p-12 text-center flex flex-col items-center justify-center space-y-3 bg-white rounded-3xl border border-red-100 shadow-xl">
      <div className="w-12 h-12 rounded-2xl bg-red-50 text-[#FF2E55] flex items-center justify-center border border-red-200">
        <RotateCw className="w-6 h-6 animate-spin" />
      </div>
      <h3 className="text-base font-black text-slate-900">{label}</h3>
      <p className="text-xs text-slate-500 font-medium max-w-sm">{subtext}</p>
    </div>
  );
};
