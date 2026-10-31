import React from 'react';

interface StatusBadgeProps {
  status: 'active' | 'scanning' | 'idle' | 'completed' | 'failed';
  text?: string;
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({ status, text }) => {
  return (
    <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[11px] font-bold border border-red-200 bg-red-50 text-[#FF2E55]">
      <span className="w-1.5 h-1.5 rounded-full bg-[#FF2E55] animate-pulse" />
      <span>{text || status.toUpperCase()}</span>
    </span>
  );
};
