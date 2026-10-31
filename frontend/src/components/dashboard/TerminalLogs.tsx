import React, { useRef, useEffect } from 'react';
import { Terminal, RefreshCw } from 'lucide-react';
import { TerminalLog } from '../../types';

interface TerminalLogsProps {
  logs: TerminalLog[];
  onClearLogs?: () => void;
}

export const TerminalLogs: React.FC<TerminalLogsProps> = ({ logs, onClearLogs }) => {
  const containerRef = useRef<HTMLDivElement | null>(null);

  // Auto-scroll to latest log
  useEffect(() => {
    if (containerRef.current) {
      containerRef.current.scrollTop = containerRef.current.scrollHeight;
    }
  }, [logs]);

  return (
    <div className="p-5 rounded-3xl bg-[#0F0F12] border border-red-900/40 text-slate-200 font-mono text-xs space-y-3 shadow-xl">
      <div className="flex items-center justify-between pb-2 border-b border-slate-800">
        <span className="flex items-center gap-2 font-bold text-red-400">
          <Terminal className="w-4 h-4 text-[#FF2E55]" />
          REALTIME ANALYSIS LOG EMULATOR
        </span>
        <div className="flex items-center gap-2">
          {onClearLogs && (
            <button
              onClick={onClearLogs}
              className="text-[10px] text-slate-400 hover:text-slate-200 flex items-center gap-1 hover:underline mr-2"
              title="Clear terminal logs"
            >
              <RefreshCw className="w-3 h-3" />
              <span>Clear</span>
            </button>
          )}
          <span className="text-[10px] bg-slate-800 px-2 py-0.5 rounded text-red-400 font-semibold flex items-center gap-1">
            <span className="w-1.5 h-1.5 rounded-full bg-[#FF2E55] animate-ping" />
            STREAMING
          </span>
        </div>
      </div>

      <div ref={containerRef} className="space-y-1.5 max-h-40 overflow-y-auto pr-1">
        {logs.map((log) => (
          <div key={log.id} className="flex items-start gap-2 text-[11px] leading-relaxed">
            <span className="text-slate-500 select-none">&gt;</span>
            <span
              className={
                log.type === 'error'
                  ? 'text-red-400 font-bold'
                  : log.type === 'warn'
                  ? 'text-amber-400 font-bold'
                  : log.type === 'success'
                  ? 'text-rose-300 font-bold'
                  : 'text-slate-300'
              }
            >
              {log.text}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
};
