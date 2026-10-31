import React, { useState } from 'react';
import { GitBranch, Play, RotateCw, Check, ShieldAlert } from 'lucide-react';
import { DemoRepo } from '../../types';

interface RepositoryFormProps {
  repoUrl: string;
  setRepoUrl: (url: string) => void;
  branch: string;
  setBranch: (branch: string) => void;
  isScanning: boolean;
  onStartAnalysis: (url?: string, branch?: string) => void;
  demoRepos: DemoRepo[];
}

export const RepositoryForm: React.FC<RepositoryFormProps> = ({
  repoUrl,
  setRepoUrl,
  branch,
  setBranch,
  isScanning,
  onStartAnalysis,
  demoRepos
}) => {
  const [inputUrl, setInputUrl] = useState(repoUrl);
  const [inputBranch, setInputBranch] = useState(branch);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputUrl.trim() || isScanning) return;
    setRepoUrl(inputUrl);
    setBranch(inputBranch);
    onStartAnalysis(inputUrl, inputBranch);
  };

  const handleSelectPreset = (preset: DemoRepo) => {
    const fullUrl = `https://github.com/${preset.name}`;
    setInputUrl(fullUrl);
    setInputBranch(preset.branch);
    setRepoUrl(fullUrl);
    setBranch(preset.branch);
    onStartAnalysis(fullUrl, preset.branch);
  };

  return (
    <div className="space-y-4">
      <form onSubmit={handleSubmit} className="p-2 bg-slate-50 rounded-2xl border border-red-200 shadow-lg shadow-red-500/10 flex flex-col sm:flex-row items-center gap-2">
        <div className="flex items-center gap-2 px-3 w-full sm:w-auto flex-1">
          <GitBranch className="w-5 h-5 text-[#FF2E55] shrink-0" />
          <input
            type="text"
            value={inputUrl}
            onChange={(e) => setInputUrl(e.target.value)}
            placeholder="GitHub Repo URL (e.g. https://github.com/facebook/react)"
            className="w-full bg-transparent text-xs sm:text-sm font-extrabold text-slate-800 placeholder-slate-400 focus:outline-none"
          />
        </div>

        <div className="hidden md:flex items-center gap-1.5 px-3 py-1.5 bg-white rounded-xl border border-slate-200 text-xs font-mono">
          <span className="text-slate-400">branch:</span>
          <input
            type="text"
            value={inputBranch}
            onChange={(e) => setInputBranch(e.target.value)}
            placeholder="main"
            className="w-16 bg-transparent text-slate-800 font-bold focus:outline-none"
          />
        </div>

        <button
          type="submit"
          disabled={isScanning || !inputUrl.trim()}
          className="w-full sm:w-auto px-6 py-3 rounded-xl bg-[#FF2E55] hover:bg-red-600 text-white font-black text-xs uppercase tracking-wider shadow-md shadow-red-500/30 transition-all flex items-center justify-center gap-2 shrink-0 disabled:opacity-50"
        >
          {isScanning ? (
            <>
              <RotateCw className="w-4 h-4 animate-spin" />
              <span>Analyzing...</span>
            </>
          ) : (
            <>
              <Play className="w-4 h-4 fill-white" />
              <span>Start Analysis</span>
            </>
          )}
        </button>
      </form>

      {/* Preset repository chips */}
      <div className="flex flex-wrap items-center gap-2 text-xs">
        <span className="text-slate-400 font-bold uppercase text-[10px]">Quick Presets:</span>
        {demoRepos.map((r) => {
          const isSelected = inputUrl.includes(r.name);
          return (
            <button
              key={r.name}
              type="button"
              onClick={() => handleSelectPreset(r)}
              className={`px-2.5 py-1 rounded-lg border text-[11px] font-bold transition-all shadow-sm flex items-center gap-1 ${
                isSelected
                  ? 'bg-red-50 border-red-300 text-[#FF2E55]'
                  : 'bg-white border-red-100 hover:border-red-300 text-slate-700 hover:text-[#FF2E55]'
              }`}
            >
              <span>{r.label}</span>
              {isSelected && <Check className="w-3 h-3 text-[#FF2E55]" />}
            </button>
          );
        })}
      </div>
    </div>
  );
};
