import React, { useState } from 'react';
import { CompoundProfile, DoubleHitADR } from '../types/pharmacology.ts';
import { AlertCircle, ShieldAlert, CheckCircle, Activity, Heart, Search } from 'lucide-react';

interface ADRProfileCardProps {
  lead: CompoundProfile;
  coMed: CompoundProfile;
  doubleHitADRs: DoubleHitADR[];
}

export const ADRProfileCard: React.FC<ADRProfileCardProps> = ({
  lead,
  coMed,
  doubleHitADRs,
}) => {
  const [filterQuery, setFilterQuery] = useState('');

  const filteredLeadADRs = lead.monotherapyADRs.filter((a) =>
    a.term.toLowerCase().includes(filterQuery.toLowerCase()) ||
    a.organClass.toLowerCase().includes(filterQuery.toLowerCase())
  );

  const filteredCoMedADRs = coMed.monotherapyADRs.filter((a) =>
    a.term.toLowerCase().includes(filterQuery.toLowerCase()) ||
    a.organClass.toLowerCase().includes(filterQuery.toLowerCase())
  );

  return (
    <section id="adrs" className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-sm">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between pb-4 border-b border-slate-800 gap-2">
        <div className="flex items-center gap-2">
          <AlertCircle className="w-4 h-4 text-emerald-400" />
          <h2 className="text-sm font-semibold tracking-wide text-white uppercase">
            Adverse Drug Reaction (ADR) Spectrum & "Double-Hit" Analysis
          </h2>
        </div>
        <div className="relative">
          <Search className="w-3.5 h-3.5 absolute left-2.5 top-1/2 -translate-y-1/2 text-slate-500" />
          <input
            type="text"
            placeholder="Filter ADR terms..."
            value={filterQuery}
            onChange={(e) => setFilterQuery(e.target.value)}
            className="bg-slate-950 border border-slate-800 rounded-md pl-8 pr-3 py-1 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-cyan-500 w-44 font-mono"
          />
        </div>
      </div>

      {/* Double-Hit Compounded Liability Alert Banner */}
      {doubleHitADRs.length > 0 ? (
        <div className="my-4 p-4 rounded-lg bg-rose-950/30 border border-rose-900/60">
          <div className="flex items-center gap-2 mb-2">
            <ShieldAlert className="w-4 h-4 text-rose-400" />
            <h3 className="text-xs font-bold uppercase tracking-wider text-rose-300 font-mono">
              Compounded Organ Liability Detected ("Double-Hit" Phenotype)
            </h3>
          </div>
          <p className="text-xs text-rose-200/90 mb-3 leading-relaxed">
            Both candidates independently target identical physiological pathways. Simultaneous exposure removes metabolic redundancy, triggering acute clinical decompensation:
          </p>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
            {doubleHitADRs.map((dh, i) => (
              <div key={i} className="p-2.5 rounded bg-slate-950/80 border border-rose-900/40 text-xs">
                <div className="flex items-center justify-between mb-1">
                  <span className="font-semibold text-rose-200">{dh.reaction}</span>
                  <span className="text-[10px] font-mono px-1.5 py-0.2 rounded bg-rose-950 text-rose-300 border border-rose-800">
                    {dh.severityGrade}
                  </span>
                </div>
                <span className="text-[10px] text-slate-400 block font-mono mb-1">{dh.systemOrganClass}</span>
                <p className="text-[11px] text-slate-400 leading-tight">{dh.clinicalImpact}</p>
              </div>
            ))}
          </div>
        </div>
      ) : (
        <div className="my-4 p-3 rounded-lg bg-slate-950/60 border border-slate-800 flex items-center gap-2 text-xs text-slate-400">
          <CheckCircle className="w-4 h-4 text-emerald-400 shrink-0" />
          <span>No direct identical MedDRA adverse reaction overlap detected between single-agent profiles.</span>
        </div>
      )}

      {/* Side-by-Side ADR Profiles */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-5 mt-2">
        {/* Drug A (Lead) Monotherapy ADRs */}
        <div className="bg-slate-950/60 rounded-lg border border-slate-800/80 p-4">
          <div className="flex items-center justify-between mb-3 pb-2 border-b border-slate-800">
            <span className="text-xs font-semibold text-slate-200 flex items-center gap-1.5">
              <Activity className="w-3.5 h-3.5 text-cyan-400" />
              {lead.name} Monotherapy ADRs
            </span>
            <span className="text-[11px] font-mono text-slate-400">
              openFDA FAERS Reports
            </span>
          </div>

          <div className="space-y-2 max-h-64 overflow-y-auto pr-1">
            {filteredLeadADRs.map((adr, i) => (
              <div
                key={i}
                className="flex items-center justify-between p-2 rounded bg-slate-900 border border-slate-800 text-xs"
              >
                <div>
                  <span className="font-medium text-slate-200 block">{adr.term}</span>
                  <span className="text-[10px] text-slate-400 font-mono">{adr.organClass}</span>
                </div>
                <span className="font-mono text-cyan-400 text-[11px] font-semibold tabular-nums">
                  {adr.count.toLocaleString()} cases
                </span>
              </div>
            ))}
            {filteredLeadADRs.length === 0 && (
              <div className="text-center py-6 text-slate-400 text-xs font-mono">
                No matching ADR terms found.
              </div>
            )}
          </div>
        </div>

        {/* Drug B (Co-Med) Monotherapy ADRs */}
        <div className="bg-slate-950/60 rounded-lg border border-slate-800/80 p-4">
          <div className="flex items-center justify-between mb-3 pb-2 border-b border-slate-800">
            <span className="text-xs font-semibold text-slate-200 flex items-center gap-1.5">
              <Heart className="w-3.5 h-3.5 text-purple-400" />
              {coMed.name} Monotherapy ADRs
            </span>
            <span className="text-[11px] font-mono text-slate-400">
              openFDA FAERS Reports
            </span>
          </div>

          <div className="space-y-2 max-h-64 overflow-y-auto pr-1">
            {filteredCoMedADRs.map((adr, i) => (
              <div
                key={i}
                className="flex items-center justify-between p-2 rounded bg-slate-900 border border-slate-800 text-xs"
              >
                <div>
                  <span className="font-medium text-slate-200 block">{adr.term}</span>
                  <span className="text-[10px] text-slate-400 font-mono">{adr.organClass}</span>
                </div>
                <span className="font-mono text-purple-400 text-[11px] font-semibold tabular-nums">
                  {adr.count.toLocaleString()} cases
                </span>
              </div>
            ))}
            {filteredCoMedADRs.length === 0 && (
              <div className="text-center py-6 text-slate-400 text-xs font-mono">
                No matching ADR terms found.
              </div>
            )}
          </div>
        </div>
      </div>
    </section>
  );
};
