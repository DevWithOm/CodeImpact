import React from 'react';
import { AlertTriangle, RefreshCw } from 'lucide-react';

interface ErrorStateProps {
  title?: string;
  message?: string;
  onRetry?: () => void;
}

export const ErrorState: React.FC<ErrorStateProps> = ({
  title = 'Analysis Engine Failed',
  message = 'An unexpected error occurred while communicating with the analysis pipeline.',
  onRetry
}) => {
  return (
    <div className="p-8 text-center flex flex-col items-center justify-center space-y-3 bg-red-50/50 rounded-3xl border border-red-200 shadow-lg">
      <div className="w-12 h-12 rounded-2xl bg-red-100 text-red-600 flex items-center justify-center">
        <AlertTriangle className="w-6 h-6" />
      </div>
      <h3 className="text-base font-black text-slate-900">{title}</h3>
      <p className="text-xs text-slate-600 font-medium max-w-md">{message}</p>
      {onRetry && (
        <button
          onClick={onRetry}
          className="mt-2 px-4 py-2 rounded-xl bg-[#FF2E55] text-white text-xs font-bold flex items-center gap-1.5 shadow-md hover:bg-red-600 transition-colors"
        >
          <RefreshCw className="w-3.5 h-3.5" />
          <span>Retry Operation</span>
        </button>
      )}
    </div>
  );
};
