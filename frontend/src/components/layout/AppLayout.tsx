import React, { useState } from 'react';
import { Navbar } from './Navbar';
import { Sidebar } from './Sidebar';
import { HUDDock } from './HUDDock';
import { ReportModal } from '../shared/ReportModal';
import { AnalysisSummary, Finding } from '../../types';

interface AppLayoutProps {
  children: React.ReactNode;
  activeTab: string;
  setActiveTab: (tab: string) => void;
  onTriggerScan: () => void;
  isScanning: boolean;
  activeRepo: string;
  branch: string;
  summary: AnalysisSummary;
  findings: Finding[];
}

export const AppLayout: React.FC<AppLayoutProps> = ({
  children,
  activeTab,
  setActiveTab,
  onTriggerScan,
  isScanning,
  activeRepo,
  branch,
  summary,
  findings
}) => {
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false);
  const [isReportModalOpen, setIsReportModalOpen] = useState(false);

  return (
    <div className="min-h-screen bg-[#FAF9F9] text-slate-900 font-sans selection:bg-[#FF2E55] selection:text-white flex overflow-x-hidden">
      {/* Desktop Developer Sidebar */}
      <Sidebar
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        isCollapsed={isSidebarCollapsed}
        setIsCollapsed={setIsSidebarCollapsed}
        activeRepo={activeRepo}
        branch={branch}
        onOpenReport={() => setActiveTab('reports')}
      />

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Top Navigation Bar with Marquee & Laser line */}
        <Navbar
          activeTab={activeTab}
          setActiveTab={setActiveTab}
          onTriggerScan={onTriggerScan}
          isScanning={isScanning}
          onOpenReport={() => setActiveTab('reports')}
        />

        {/* Page Content */}
        <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8">
          {children}
        </main>

        {/* Floating Status HUD Dock */}
        <HUDDock
          findingsCount={findings.length}
          healthScore={summary.healthScore}
          isScanning={isScanning}
        />

        {/* Report Modal */}
        <ReportModal
          isOpen={isReportModalOpen}
          onClose={() => setIsReportModalOpen(false)}
          summary={summary}
          findings={findings}
        />
      </div>
    </div>
  );
};
