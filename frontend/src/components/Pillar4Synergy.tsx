import React from 'react';
import { SynergySignal, OrganStress } from '../types/pharmacology.ts';
import { Layers, TrendingUp, AlertTriangle } from 'lucide-react';

interface Pillar4Props {
  leadName: string;
  coMedName: string;
  synergySignals: SynergySignal[];
  organStressList: OrganStress[];
}

export const Pillar4Synergy: React.FC<Pillar4Props> = ({
  leadName,
  coMedName,
  synergySignals,
  organStressList,
}) => {
  const maxCount = Math.max(...synergySignals.map((s) => s.coAdminCount), 100);

  return (
    <section id="synergy" className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-sm">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between pb-4 border-b border-slate-800 gap-2">
        <div className="flex items-center gap-2">
          <Layers className="w-4 h-4 text-purple-400" />
          <h2 className="text-sm font-semibold tracking-wide text-white uppercase">
            Preclinical Co-Dosing Synergy & Cumulative Organ Burden
          </h2>
        </div>
        <span className="text-xs font-mono text-slate-400">
          openFDA FAERS Signals & ROR Metrics
        </span>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-5 mt-4">
        {/* Left Column: Real-World Co-Dosing FAERS Adverse Signals */}
        <div className="lg:col-span-7 bg-slate-950/60 rounded-lg border border-slate-800/80 p-4">
          <div className="flex items-center justify-between mb-3 pb-2 border-b border-slate-800">
            <div>
              <span className="text-xs font-semibold text-slate-200 block">
                FDA Co-Administration Adverse Reaction Signals
              </span>
              <span className="text-[11px] text-slate-400">
                Reporting Odds Ratio (ROR) &gt; 2.5 indicates synergistic risk amplification
              </span>
            </div>
            <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-purple-950 text-purple-300 border border-purple-800">
              Co-Dosing Cohort
            </span>
          </div>

          {/* SVG Comparative Horizontal Bar Chart */}
          <div className="space-y-3.5 my-2">
            {synergySignals.map((signal, idx) => {
              const widthPct = Math.min(100, Math.max(15, (signal.coAdminCount / maxCount) * 100));
              const isSevere = signal.rorScore > 5.0;

              return (
                <div key={idx} className="space-y-1">
                  <div className="flex items-baseline justify-between text-xs">
                    <span className="text-slate-200 font-medium truncate max-w-[260px] sm:max-w-[320px]">
                      {signal.reaction}
                    </span>
                    <div className="flex items-center gap-2 font-mono text-[11px] shrink-0">
                      <span className="text-slate-400 tabular-nums">n = {signal.coAdminCount}</span>
                      <span
                        className={`px-1.5 py-0.2 rounded font-bold ${
                          isSevere
                            ? 'text-rose-400 bg-rose-950/80 border border-rose-800/80'
                            : 'text-purple-300 bg-purple-950/80 border border-purple-800/80'
                        }`}
                      >
                        ROR: {signal.rorScore}x
                      </span>
                    </div>
                  </div>

                  {/* Dual Bar Graphic: Combo vs Solo Background */}
                  <div className="w-full bg-slate-900 h-3 rounded-md overflow-hidden relative border border-slate-800">
                    <div
                      className={`h-full rounded-md transition-all duration-500 ${
                        isSevere
                          ? 'bg-gradient-to-r from-purple-500 to-rose-500'
                          : 'bg-gradient-to-r from-indigo-500 to-purple-500'
                      }`}
                      style={{ width: `${widthPct}%` }}
                    />
                  </div>

                  <div className="flex justify-between text-[10px] text-slate-400 font-mono">
                    <span>
                      Solo reports: {leadName} ({signal.leadSoloCount}) · {coMedName} ({signal.coMedSoloCount})
                    </span>
                    <span className={isSevere ? 'text-rose-400' : 'text-purple-400'}>
                      {signal.synergyLevel}
                    </span>
                  </div>
                </div>
              );
            })}
          </div>

          <div className="mt-4 pt-3 border-t border-slate-800 text-[11px] text-slate-400 flex items-center gap-2">
            <TrendingUp className="w-4 h-4 text-purple-400 shrink-0" />
            <span>
              Disproportionality algorithm calculates departure from null additivity hypothesis using spontaneous FAERS reports.
            </span>
          </div>
        </div>

        {/* Right Column: Cumulative Multi-Organ Stress Meters */}
        <div className="lg:col-span-5 bg-slate-950/60 rounded-lg border border-slate-800/80 p-4 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-3 pb-2 border-b border-slate-800">
              <span className="text-xs font-semibold text-slate-200">
                Cumulative Organ Burden
              </span>
              <span className="text-[11px] font-mono text-slate-400">
                Baseline vs Combo
              </span>
            </div>

            <div className="space-y-3.5">
              {organStressList.map((organ, idx) => {
                const isOverload = organ.liabilityStatus === 'Hazardous Overload';
                const isElevated = organ.liabilityStatus === 'Elevated Stress';

                return (
                  <div key={idx} className="p-2.5 rounded-lg bg-slate-900/80 border border-slate-800/80">
                    <div className="flex items-center justify-between text-xs mb-1">
                      <span className="font-semibold text-slate-200">{organ.organ} System</span>
                      <span
                        className={`text-[10px] font-mono font-bold px-1.5 py-0.5 rounded ${
                          isOverload
                            ? 'bg-rose-950 text-rose-300 border border-rose-800'
                            : isElevated
                            ? 'bg-amber-950 text-amber-300 border border-amber-800'
                            : 'bg-emerald-950 text-emerald-300 border border-emerald-800'
                        }`}
                      >
                        {organ.liabilityStatus}
                      </span>
                    </div>

                    {/* Comparative Stress Bar */}
                    <div className="w-full bg-slate-950 h-2 rounded-full overflow-hidden my-1 flex gap-0.5">
                      <div
                        className="h-full bg-slate-600 rounded-l-full"
                        style={{ width: `${organ.baselineScore}%` }}
                        title={`Baseline Stress: ${organ.baselineScore}%`}
                      />
                      <div
                        className={`h-full rounded-r-full ${
                          isOverload ? 'bg-rose-500' : isElevated ? 'bg-amber-500' : 'bg-emerald-500'
                        }`}
                        style={{ width: `${Math.max(0, organ.amplifiedScore - organ.baselineScore)}%` }}
                        title={`Combo Amplification: +${organ.amplifiedScore - organ.baselineScore}%`}
                      />
                    </div>

                    <div className="flex justify-between text-[10px] text-slate-400 font-mono">
                      <span>Baseline: {organ.baselineScore}%</span>
                      <span className="font-bold text-slate-300">Combo Burden: {organ.amplifiedScore}%</span>
                    </div>

                    <p className="text-[10px] text-slate-400 mt-1 leading-tight">{organ.pathwayNotes}</p>
                  </div>
                );
              })}
            </div>
          </div>

          <div className="mt-3 pt-2 border-t border-slate-800 flex items-center gap-1.5 text-[11px] text-amber-300/90">
            <AlertTriangle className="w-3.5 h-3.5 text-amber-400 shrink-0" />
            <span>High cumulative stress compounds failure rates in co-morbid preclinical animal trials.</span>
          </div>
        </div>
      </div>
    </section>
  );
};
