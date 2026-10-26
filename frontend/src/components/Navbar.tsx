import React from 'react';
import { FlaskConical, FileText, Database } from 'lucide-react';

interface NavbarProps {
  onExportClick: () => void;
  activeTab: 'workspace' | 'evidence' | 'evaluation' | 'batch' | 'governance';
  onSelectTab: (tab: 'workspace' | 'evidence' | 'evaluation' | 'batch' | 'governance') => void;
  apiMetadata?: {
    pubchemLive: boolean;
    chemblLive: boolean;
    openFdaLive: boolean;
  };
}

export const Navbar: React.FC<NavbarProps> = ({
  onExportClick,
  activeTab,
  onSelectTab,
  apiMetadata,
}) => {
  return (
    <header className="sticky top-0 z-40 bg-slate-950/90 backdrop-blur-md border-b border-slate-800 px-6 py-3.5 flex items-center justify-between gap-8">
      {/* Zone 1: Brand Wordmark */}
      <div className="flex items-center gap-3 shrink-0">
        <div className="w-8 h-8 rounded-lg bg-cyan-950/80 border border-cyan-500/40 flex items-center justify-center text-cyan-400">
          <FlaskConical className="w-4 h-4" />
        </div>
        <div>
          <span className="text-base font-bold tracking-tight text-white font-sans">
            AuditDDI
          </span>
          <span className="hidden sm:inline-block ml-2 text-xs text-slate-400 font-mono">
            R&D Platform
          </span>
        </div>
      </div>

      {/* Zone 2: Navigation Links (single-line, 5 concise modules) */}
      <nav className="hidden md:flex items-center gap-6 text-xs font-medium text-slate-300">
        <button
          onClick={() => onSelectTab('workspace')}
          className={`whitespace-nowrap transition-colors hover:text-cyan-400 ${
            activeTab === 'workspace' ? 'text-cyan-400 font-semibold' : ''
          }`}
        >
          Prediction Workspace
        </button>
        <button
          onClick={() => onSelectTab('evidence')}
          className={`whitespace-nowrap transition-colors hover:text-emerald-400 ${
            activeTab === 'evidence' ? 'text-emerald-400 font-semibold' : ''
          }`}
        >
          Evidence & Datasets
        </button>
        <button
          onClick={() => onSelectTab('evaluation')}
          className={`whitespace-nowrap transition-colors hover:text-purple-400 ${
            activeTab === 'evaluation' ? 'text-purple-400 font-semibold' : ''
          }`}
        >
          Evaluation Lab
        </button>
        <button
          onClick={() => onSelectTab('batch')}
          className={`whitespace-nowrap transition-colors hover:text-amber-400 ${
            activeTab === 'batch' ? 'text-amber-400 font-semibold' : ''
          }`}
        >
          Batch Screening
        </button>
        <button
          onClick={() => onSelectTab('governance')}
          className={`whitespace-nowrap transition-colors hover:text-sky-400 ${
            activeTab === 'governance' ? 'text-sky-400 font-semibold' : ''
          }`}
        >
          Model Governance
        </button>
      </nav>

      {/* Zone 3: Single Primary Action */}
      <div className="flex items-center gap-3 shrink-0">
        {apiMetadata && (
          <div className="hidden lg:flex items-center gap-2 text-[11px] font-mono text-slate-400 mr-2">
            <Database className="w-3.5 h-3.5 text-slate-500" />
            <span className={apiMetadata.pubchemLive ? 'text-emerald-400' : 'text-slate-400'}>
              PubChem
            </span>
            <span>·</span>
            <span className={apiMetadata.chemblLive ? 'text-emerald-400' : 'text-slate-400'}>
              ChEMBL
            </span>
            <span>·</span>
            <span className={apiMetadata.openFdaLive ? 'text-emerald-400' : 'text-slate-400'}>
              openFDA
            </span>
          </div>
        )}
        <button
          onClick={onExportClick}
          className="flex items-center gap-2 px-3.5 py-1.5 text-xs font-semibold text-slate-100 bg-slate-900 border border-slate-700 hover:border-cyan-500 hover:text-cyan-300 rounded-lg transition-colors whitespace-nowrap shadow-sm"
        >
          <FileText className="w-3.5 h-3.5" />
          Export IND Dossier
        </button>
      </div>
    </header>
  );
};
