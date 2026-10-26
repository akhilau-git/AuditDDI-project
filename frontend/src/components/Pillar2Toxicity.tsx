import React from 'react';
import { CompoundProfile } from '../types/pharmacology.ts';
import { AlertOctagon, Heart, Zap, FileWarning } from 'lucide-react';

interface Pillar2Props {
  lead: CompoundProfile;
  coMed: CompoundProfile;
}

export const Pillar2Toxicity: React.FC<Pillar2Props> = ({ lead }) => {
  const cipa = lead.cipaProfile;
  const dili = lead.diliProfile;

  const isHergCritical = cipa.hergIc50 < 1.0;
  const isHergModerate = cipa.hergIc50 >= 1.0 && cipa.hergIc50 < 10.0;

  return (
    <section id="toxicity" className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-sm">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between pb-4 border-b border-slate-800 gap-2">
        <div className="flex items-center gap-2">
          <AlertOctagon className="w-4 h-4 text-rose-400" />
          <h2 className="text-sm font-semibold tracking-wide text-white uppercase">
            Toxicity Liability Evaluation & CiPA Panel
          </h2>
        </div>
        <span className="text-xs font-mono text-slate-400">
          Target Assays & FDA Label
        </span>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-5 mt-4">
        {/* CiPA Multi-Ion Channel Cardiotoxicity */}
        <div className="bg-slate-950/60 rounded-lg border border-slate-800/80 p-4 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-3 pb-2 border-b border-slate-800">
              <span className="text-xs font-semibold text-slate-200 flex items-center gap-1.5">
                <Heart className="w-3.5 h-3.5 text-rose-400" /> CiPA In Vitro Proarrhythmia
              </span>
              <span
                className={`text-[11px] font-mono font-semibold px-2 py-0.5 rounded border ${
                  isHergCritical
                    ? 'bg-rose-950 text-rose-300 border-rose-800'
                    : isHergModerate
                    ? 'bg-amber-950 text-amber-300 border-amber-800'
                    : 'bg-emerald-950 text-emerald-300 border-emerald-800'
                }`}
              >
                Risk: {cipa.netArrhythmiaRisk}
              </span>
            </div>

            {/* Ion Channel Affinity Rows */}
            <div className="space-y-3">
              <div>
                <div className="flex justify-between text-xs mb-1">
                  <span className="text-slate-400 font-mono">hERG (IKr) Potassium Blockade</span>
                  <span className={`font-mono font-bold ${isHergCritical ? 'text-rose-400' : 'text-slate-200'}`}>
                    IC50: {cipa.hergIc50} µM
                  </span>
                </div>
                <div className="w-full bg-slate-800 h-2 rounded-full overflow-hidden">
                  <div
                    className={`h-full ${isHergCritical ? 'bg-rose-500' : isHergModerate ? 'bg-amber-500' : 'bg-emerald-500'}`}
                    style={{ width: `${Math.min(100, Math.max(10, (1 / Math.max(0.1, cipa.hergIc50)) * 25))}%` }}
                  />
                </div>
                <span className="text-[10px] text-slate-400 font-mono">Safety Margin: {cipa.hergSafetyMargin}x therapeutic Cmax</span>
              </div>

              <div>
                <div className="flex justify-between text-xs mb-1">
                  <span className="text-slate-400 font-mono">Nav1.5 (INa) Sodium Influx</span>
                  <span className="font-mono text-slate-300">IC50: {cipa.nav15Ic50} µM</span>
                </div>
                <div className="w-full bg-slate-800 h-1.5 rounded-full overflow-hidden">
                  <div className="h-full bg-sky-500" style={{ width: '30%' }} />
                </div>
              </div>

              <div>
                <div className="flex justify-between text-xs mb-1">
                  <span className="text-slate-400 font-mono">Cav1.2 (ICa,L) L-Type Calcium</span>
                  <span className="font-mono text-slate-300">IC50: {cipa.cav12Ic50} µM</span>
                </div>
                <div className="w-full bg-slate-800 h-1.5 rounded-full overflow-hidden">
                  <div className="h-full bg-indigo-500" style={{ width: '40%' }} />
                </div>
              </div>
            </div>
          </div>

          <p className="text-[11px] text-slate-400 mt-3 pt-2 border-t border-slate-800">
            {cipa.qtProlongationLikelihood}
          </p>
        </div>

        {/* DILI & Mutagenic Toxicity Profiler */}
        <div className="bg-slate-950/60 rounded-lg border border-slate-800/80 p-4 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-3 pb-2 border-b border-slate-800">
              <span className="text-xs font-semibold text-slate-200 flex items-center gap-1.5">
                <Zap className="w-3.5 h-3.5 text-amber-400" /> DILI & Mechanistic Biomarkers
              </span>
              <span className="text-[11px] font-mono text-slate-400">
                Concern: {dili.diliConcernScore}
              </span>
            </div>

            <div className="space-y-2.5">
              <div className="flex items-center justify-between p-2 rounded bg-slate-900 border border-slate-800 text-xs">
                <div>
                  <span className="font-medium text-slate-300 block">BSEP Canalicular Transporter</span>
                  <span className="text-[10px] text-slate-400">Bile Salt Export Pump inhibition (cholestasis marker)</span>
                </div>
                <span
                  className={`font-mono text-[11px] font-bold px-2 py-0.5 rounded ${
                    dili.bsepInhibition
                      ? 'bg-rose-950/80 text-rose-300 border border-rose-800'
                      : 'bg-emerald-950/80 text-emerald-300 border border-emerald-800'
                  }`}
                >
                  {dili.bsepInhibition ? 'INHIBITOR' : 'NEGATIVE'}
                </span>
              </div>

              <div className="flex items-center justify-between p-2 rounded bg-slate-900 border border-slate-800 text-xs">
                <div>
                  <span className="font-medium text-slate-300 block">Mitochondrial Membrane Disruption</span>
                  <span className="text-[10px] text-slate-400">ATP depletion & electron transport chain stress</span>
                </div>
                <span
                  className={`font-mono text-[11px] font-bold px-2 py-0.5 rounded ${
                    dili.mitochondrialToxicity
                      ? 'bg-amber-950/80 text-amber-300 border border-amber-800'
                      : 'bg-emerald-950/80 text-emerald-300 border border-emerald-800'
                  }`}
                >
                  {dili.mitochondrialToxicity ? 'ALERT' : 'NEGATIVE'}
                </span>
              </div>

              <div className="flex items-center justify-between p-2 rounded bg-slate-900 border border-slate-800 text-xs">
                <div>
                  <span className="font-medium text-slate-300 block">ICH M7 Genotoxicity / Ames</span>
                  <span className="text-[10px] text-slate-400">DNA-reactive structural alert scanning</span>
                </div>
                <span className="font-mono text-[11px] font-semibold text-emerald-400 px-2 py-0.5 rounded bg-emerald-950/50 border border-emerald-800">
                  {lead.ichM7AmesMutagenicity}
                </span>
              </div>
            </div>
          </div>

          <div className="mt-3 pt-2 border-t border-slate-800 text-[11px] text-slate-400">
            Reactive metabolite liability:{' '}
            <strong className="text-slate-300">
              {dili.reactiveMetaboliteLiability ? 'Detected (GSH conjugation screen advised)' : 'Low liability'}
            </strong>
          </div>
        </div>
      </div>

      {/* Boxed Warnings Section (From openFDA Drug Labeling) */}
      {lead.boxedWarnings && lead.boxedWarnings.length > 0 && (
        <div className="mt-4 p-3.5 rounded-lg bg-rose-950/20 border border-rose-900/60">
          <div className="flex items-center gap-2 mb-1.5 text-xs font-semibold text-rose-300">
            <FileWarning className="w-4 h-4 text-rose-400" />
            <span>FDA Regulatory Product Labeling & Black Box Warnings</span>
          </div>
          <ul className="space-y-1 text-xs text-rose-200/90 pl-6 list-disc">
            {lead.boxedWarnings.map((warn, i) => (
              <li key={i}>{warn}</li>
            ))}
          </ul>
        </div>
      )}
    </section>
  );
};
