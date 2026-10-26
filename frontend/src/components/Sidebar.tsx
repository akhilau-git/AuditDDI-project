import React from 'react';
import {
  Brain,
  Activity,
  AlertOctagon,
  Scale,
  Layers,
  AlertCircle,
  Sliders,
  Database,
  BarChart3,
  FileSpreadsheet,
  ShieldCheck,
  FlaskConical,
} from 'lucide-react';

export type PageId =
  | 'ddi'
  | 'admet'
  | 'toxicity'
  | 'ichm12'
  | 'synergy'
  | 'adrs'
  | 'simulator'
  | 'evidence'
  | 'evaluation'
  | 'batch'
  | 'governance';

interface SidebarProps {
  activePage: PageId;
  onSelectPage: (page: PageId) => void;
  apiMetadata?: {
    pubchemLive: boolean;
    chemblLive: boolean;
    openFdaLive: boolean;
  };
}

export const Sidebar: React.FC<SidebarProps> = ({
  activePage,
  onSelectPage,
  apiMetadata,
}) => {
  const navSections = [
    {
      group: 'Prediction & Profiling',
      items: [
        { id: 'ddi' as PageId, label: 'DDI Prediction Analysis', icon: Brain, badge: 'AI' },
        { id: 'admet' as PageId, label: 'ADMET Property Checking', icon: Activity, badge: '3D' },
        { id: 'toxicity' as PageId, label: 'Toxicity Liability Evaluation', icon: AlertOctagon },
        { id: 'ichm12' as PageId, label: 'ICH M12 Regulatory Compliance', icon: Scale },
        { id: 'synergy' as PageId, label: 'Preclinical Co-Dosing Synergy', icon: Layers },
        { id: 'adrs' as PageId, label: 'ADR Spectrum & Double-Hit', icon: AlertCircle },
        { id: 'simulator' as PageId, label: 'PK Clearance Simulator', icon: Sliders },
      ],
    },
    {
      group: 'Evidence & Validation',
      items: [
        { id: 'evidence' as PageId, label: 'Multisource Evidence Explorer', icon: Database, badge: '7-DB' },
        { id: 'evaluation' as PageId, label: 'Model Evaluation & Reliability Lab', icon: BarChart3, badge: 'S1/S2' },
      ],
    },
    {
      group: 'High-Throughput & Registry',
      items: [
        { id: 'batch' as PageId, label: 'High-Throughput Batch Screening', icon: FileSpreadsheet },
        { id: 'governance' as PageId, label: 'Model Governance & Run Registry', icon: ShieldCheck },
      ],
    },
  ];

  return (
    <aside className="w-64 bg-slate-950 border-r border-slate-800 flex flex-col shrink-0 select-none">
      {/* Brand Header */}
      <div className="p-4 border-b border-slate-800 flex items-center gap-2.5">
        <div className="w-8 h-8 rounded-lg bg-cyan-950/80 border border-cyan-500/40 flex items-center justify-center text-cyan-400">
          <FlaskConical className="w-4 h-4" />
        </div>
        <div>
          <span className="text-base font-bold tracking-tight text-white block leading-none font-sans">
            AuditDDI
          </span>
          <span className="text-[10px] text-slate-400 font-mono mt-0.5 block">
            R&D Safety Platform
          </span>
        </div>
      </div>

      {/* Nav Menu */}
      <nav className="flex-1 overflow-y-auto p-3 space-y-4">
        {navSections.map((sec, idx) => (
          <div key={idx}>
            <span className="text-[10px] font-mono uppercase tracking-wider text-slate-500 block px-2 mb-1.5 font-bold">
              {sec.group}
            </span>
            <div className="space-y-0.5">
              {sec.items.map((item) => {
                const Icon = item.icon;
                const isActive = activePage === item.id;

                return (
                  <button
                    key={item.id}
                    onClick={() => onSelectPage(item.id)}
                    className={`w-full text-left px-2.5 py-2 rounded-lg text-xs font-mono transition-colors flex items-center justify-between group ${
                      isActive
                        ? 'bg-cyan-950/70 text-cyan-300 font-semibold border border-cyan-800/80'
                        : 'text-slate-400 hover:text-white hover:bg-slate-900'
                    }`}
                  >
                    <div className="flex items-center gap-2.5 truncate">
                      <Icon
                        className={`w-4 h-4 shrink-0 transition-colors ${
                          isActive ? 'text-cyan-400' : 'text-slate-500 group-hover:text-slate-300'
                        }`}
                      />
                      <span className="truncate">{item.label}</span>
                    </div>

                    {item.badge && (
                      <span
                        className={`text-[9px] px-1.5 py-0.2 rounded font-bold ${
                          isActive
                            ? 'bg-cyan-900 text-cyan-200'
                            : 'bg-slate-900 text-slate-400 border border-slate-800'
                        }`}
                      >
                        {item.badge}
                      </span>
                    )}
                  </button>
                );
              })}
            </div>
          </div>
        ))}
      </nav>

      {/* Live Data Sources Status Footer */}
      <div className="p-3 border-t border-slate-800/80 bg-slate-950 text-[10px] font-mono text-slate-400">
        <span className="block mb-1 text-slate-500 font-bold uppercase text-[9px]">
          Federated Data Feeds
        </span>
        <div className="flex items-center justify-between text-slate-300">
          <span className="flex items-center gap-1">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" /> PubChem
          </span>
          <span className="flex items-center gap-1">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" /> ChEMBL
          </span>
          <span className="flex items-center gap-1">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" /> openFDA
          </span>
        </div>
      </div>
    </aside>
  );
};
