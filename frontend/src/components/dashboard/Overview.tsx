import React from 'react';
import { HeroScanner } from './HeroScanner';
import { MetricCards } from './MetricCards';
import { WorkflowStoryCard } from './WorkflowStoryCard';
import { TerminalLogs } from './TerminalLogs';
import { RecentActivity, RecentAnalysisItem } from './RecentActivity';
import { DemoRepo, AnalysisSummary, TerminalLog } from '../../types';

interface OverviewProps {
  repoUrl: string;
  setRepoUrl: (url: string) => void;
  isScanning: boolean;
  scanProgress: number;
  scanStatus: string;
  onTriggerScan: (customUrl?: string) => void;
  demoRepos: DemoRepo[];
  summary: AnalysisSummary;
  terminalLogs: TerminalLog[];
  onClearLogs: () => void;
  onSelectTab: (tab: string) => void;
}

export const Overview: React.FC<OverviewProps> = ({
  repoUrl,
  setRepoUrl,
  isScanning,
  scanProgress,
  scanStatus,
  onTriggerScan,
  demoRepos,
  summary,
  terminalLogs,
  onClearLogs,
  onSelectTab
}) => {
  const recentItems: RecentAnalysisItem[] = [
    {
      id: 'rec-1',
      repo: 'facebook/react',
      branch: 'main',
      timestamp: '12 mins ago',
      healthScore: '89%',
      findingsCount: 5,
      status: 'Completed',
      isMockFixture: true
    },
    {
      id: 'rec-2',
      repo: 'tailwindlabs/tailwindcss',
      branch: 'main',
      timestamp: '1 hour ago',
      healthScore: '94%',
      findingsCount: 3,
      status: 'Cached',
      isMockFixture: true
    },
    {
      id: 'rec-3',
      repo: 'vercel/next.js',
      branch: 'canary',
      timestamp: '3 hours ago',
      healthScore: '86%',
      findingsCount: 8,
      status: 'Completed',
      isMockFixture: true
    },
    {
      id: 'rec-4',
      repo: 'expressjs/express',
      branch: 'master',
      timestamp: '1 day ago',
      healthScore: '78%',
      findingsCount: 12,
      status: 'Completed',
      isMockFixture: true
    }
  ];

  return (
    <div className="space-y-8 animate-fadeIn">
      {/* 1. Hero Scanner with Live Particle Canvas & Laser Code Simulator */}
      <HeroScanner
        repoUrl={repoUrl}
        setRepoUrl={setRepoUrl}
        isScanning={isScanning}
        scanProgress={scanProgress}
        scanStatus={scanStatus}
        onTriggerScan={onTriggerScan}
        demoRepos={demoRepos}
      />

      {/* 2. Summary Metric Cards */}
      <MetricCards
        summary={summary}
        onSelectTab={onSelectTab}
      />

      {/* 3. Core Workflow Story Pattern */}
      <WorkflowStoryCard
        onInspectPriorityQueue={() => onSelectTab('findings')}
      />

      {/* 4. Recent Analysis Runs & Activity */}
      <RecentActivity
        items={recentItems}
        onSelectRepo={(url) => {
          setRepoUrl(url);
          onTriggerScan(url);
        }}
      />

      {/* 5. Realtime Terminal Stream Log Console */}
      <TerminalLogs
        logs={terminalLogs}
        onClearLogs={onClearLogs}
      />
    </div>
  );
};
