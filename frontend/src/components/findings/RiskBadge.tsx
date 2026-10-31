import React from 'react';
import { ImpactRiskType, FindingSeverity, ReviewStatus } from '../../types';

interface RiskBadgeProps {
  type: ImpactRiskType | FindingSeverity | ReviewStatus | string;
  label?: string;
  className?: string;
}

export const RiskBadge: React.FC<RiskBadgeProps> = ({ type, label, className = '' }) => {
  const normalized = String(type).toLowerCase();

  let styles = 'bg-slate-100 text-slate-700 border-slate-200';

  if (normalized === 'critical' || normalized.includes('critical') || normalized.includes('do not touch')) {
    styles = 'bg-red-100 text-red-800 border-red-300 font-black';
  } else if (normalized === 'high' || normalized.includes('high risk')) {
    styles = 'bg-rose-50 text-rose-700 border-rose-200';
  } else if (normalized === 'medium' || normalized.includes('medium risk')) {
    styles = 'bg-amber-50 text-amber-700 border-amber-200';
  } else if (normalized === 'low' || normalized.includes('low risk')) {
    styles = 'bg-emerald-50 text-emerald-700 border-emerald-200';
  } else if (normalized.includes('verified')) {
    styles = 'bg-emerald-100 text-emerald-800 border-emerald-300 font-black';
  } else if (normalized.includes('in review')) {
    styles = 'bg-sky-50 text-sky-700 border-sky-200';
  } else if (normalized.includes('false positive')) {
    styles = 'bg-purple-50 text-purple-700 border-purple-200';
  } else if (normalized.includes('pending')) {
    styles = 'bg-slate-100 text-slate-700 border-slate-300';
  }

  return (
    <span
      className={`inline-flex items-center px-2 py-0.5 rounded text-[10px] font-extrabold uppercase tracking-wider border ${styles} ${className}`}
    >
      {label || type}
    </span>
  );
};
