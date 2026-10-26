import React, { useState } from 'react';
import { ICHM12Assessment, CYPConflict } from '../types/pharmacology.ts';
import { Scale, CheckCircle2, AlertTriangle, ShieldX } from 'lucide-react';

interface Pillar3Props {
  ichM12: ICHM12Assessment;
  cypConflicts: CYPConflict[];
}

export const Pillar3ICHM12: React.FC<Pillar3Props> = ({ ichM12, cypConflicts }) => {
  // Allow user to dynamically test custom in vitro preclinical measurements
  const [iMax, setIMax] = useState<number>(ichM12.iMaxUnbound);
  const [ki, setKi] = useState<number>(ichM12.kiUnbound);

  const calculatedR1 = Number((1 + iMax / Math.max(0.001, ki)).toFixed(3));
  const triggersClinicalStudy = calculatedR1 >= 1.02;
  const isSevereConflict = calculatedR1 >= 1.25;

  return (
    <section id="ichm12" className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-sm">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between pb-4 border-b border-slate-800 gap-2">
        <div className="flex items-center gap-2">
          <Scale className="w-4 h-4 text-amber-400" />
          <h2 className="text-sm font-semibold tracking-wide text-white uppercase">
            ICH M12 Regulatory Compliance Engine
          </h2>
        </div>
        <span className="text-xs font-mono text-slate-400">
          ICH M12 Standard (FDA/EMA/PMDA)
        </span>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-5 mt-4">
        {/* Left Column: ICH M12 Equation & Interactive Sliders */}
        <div className="lg:col-span-6 bg-slate-950/60 rounded-lg border border-slate-800/80 p-4 flex flex-col justify-between">
          <div>
            <div className="flex items-baseline justify-between mb-3 pb-2 border-b border-slate-800">
              <span className="text-xs font-semibold text-slate-200">
                Reversible Inhibition Basic Model
              </span>
              <span className="text-[11px] font-mono text-slate-400">
                R₁ = 1 + (Imax,u / Ki,u)
              </span>
            </div>

            {/* R1 Display Banner */}
            <div className="p-4 rounded-lg bg-slate-900 border border-slate-800 flex items-center justify-between">
              <div>
                <span className="text-xs text-slate-400 block font-mono">Calculated Ratio (R₁)</span>
                <span
                  className={`text-3xl font-mono font-bold tracking-tight tabular-nums ${
                    isSevereConflict ? 'text-rose-400' : triggersClinicalStudy ? 'text-amber-400' : 'text-emerald-400'
                  }`}
                >
                  {calculatedR1}
                </span>
                <span className="text-[11px] text-slate-400 block font-mono mt-0.5">
                  Statutory Cutoff: R₁ ≥ 1.02
                </span>
              </div>

              <div className="text-right">
                <span className="text-xs text-slate-400 block font-mono">Regulatory Status</span>
                <span
                  className={`text-xs font-bold uppercase tracking-wider px-2.5 py-1 rounded-md border inline-block mt-1 font-mono ${
                    isSevereConflict
                      ? 'bg-rose-950 text-rose-300 border-rose-800'
                      : triggersClinicalStudy
                      ? 'bg-amber-950 text-amber-300 border-amber-800'
                      : 'bg-emerald-950 text-emerald-300 border-emerald-800'
                  }`}
                >
                  {isSevereConflict ? 'High Liability' : triggersClinicalStudy ? 'Trial Mandated' : 'De-risked'}
                </span>
              </div>
            </div>

            {/* In Vitro Preclinical Parameter Sliders */}
            <div className="space-y-4 mt-4">
              <div>
                <div className="flex justify-between text-xs mb-1">
                  <span className="text-slate-300 font-medium">Unbound Max Plasma Conc. (Imax,u)</span>
                  <span className="font-mono text-cyan-400 font-bold tabular-nums">{iMax} µM</span>
                </div>
                <input
                  type="range"
                  min="0.01"
                  max="0.50"
                  step="0.01"
                  value={iMax}
                  onChange={(e) => setIMax(parseFloat(e.target.value))}
                  className="w-full accent-cyan-400 cursor-pointer h-1.5 bg-slate-800 rounded-lg"
                />
                <div className="flex justify-between text-[10px] text-slate-400 font-mono mt-0.5">
                  <span>0.01 µM (Low dose)</span>
                  <span>0.50 µM (Supratherapeutic)</span>
                </div>
              </div>

              <div>
                <div className="flex justify-between text-xs mb-1">
                  <span className="text-slate-300 font-medium">In Vitro Inhibition Constant (Ki,u)</span>
                  <span className="font-mono text-amber-400 font-bold tabular-nums">{ki} µM</span>
                </div>
                <input
                  type="range"
                  min="0.02"
                  max="2.00"
                  step="0.02"
                  value={ki}
                  onChange={(e) => setKi(parseFloat(e.target.value))}
                  className="w-full accent-amber-400 cursor-pointer h-1.5 bg-slate-800 rounded-lg"
                />
                <div className="flex justify-between text-[10px] text-slate-400 font-mono mt-0.5">
                  <span>0.02 µM (Potent blocker)</span>
                  <span>2.00 µM (Weak affinity)</span>
                </div>
              </div>
            </div>
          </div>

          {/* Statutory Verdict Callout */}
          <div className="mt-4 pt-3 border-t border-slate-800">
            {triggersClinicalStudy ? (
              <div className="flex items-start gap-2.5 p-3 rounded bg-amber-950/30 border border-amber-900/60 text-xs text-amber-200">
                <AlertTriangle className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
                <div>
                  <strong className="block font-semibold">ICH M12 Statutory Trigger Met</strong>
                  Calculated R₁ ({calculatedR1}) exceeds 1.02. Sponsors must conduct an in vivo clinical DDI study using sensitive probe substrate or qualify a physiologically-based pharmacokinetic (PBPK) model before NDA submission.
                </div>
              </div>
            ) : (
              <div className="flex items-start gap-2.5 p-3 rounded bg-emerald-950/30 border border-emerald-900/60 text-xs text-emerald-200">
                <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
                <div>
                  <strong className="block font-semibold">Sub-Threshold / De-risked</strong>
                  Calculated R₁ ({calculatedR1}) &lt; 1.02. Reversible in vivo inhibition clearance risk is mathematically negligible under ICH M12 criteria.
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Right Column: CYP Metabolism & Transporter Conflict Matrix */}
        <div className="lg:col-span-6 bg-slate-950/60 rounded-lg border border-slate-800/80 p-4 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-3 pb-2 border-b border-slate-800">
              <span className="text-xs font-semibold text-slate-200">
                Enzyme & Transporter Conflict Matrix
              </span>
              <span className="text-[11px] font-mono text-slate-400">
                {cypConflicts.length} Conflict(s)
              </span>
            </div>

            <div className="space-y-3">
              {cypConflicts.map((c, i) => (
                <div key={i} className="p-3 bg-slate-900 rounded-lg border border-slate-800">
                  <div className="flex items-center justify-between gap-2 mb-1">
                    <span className="text-xs font-bold font-mono text-cyan-300 flex items-center gap-1.5">
                      {c.severity === 'Contraindicated' ? (
                        <ShieldX className="w-3.5 h-3.5 text-rose-500" />
                      ) : (
                        <AlertTriangle className="w-3.5 h-3.5 text-amber-500" />
                      )}
                      {c.enzyme} ({c.mechanism})
                    </span>

                    <span
                      className={`text-[10px] font-bold font-mono px-2 py-0.5 rounded uppercase ${
                        c.severity === 'Contraindicated'
                          ? 'bg-rose-950 text-rose-300 border border-rose-800'
                          : c.severity === 'Major'
                          ? 'bg-amber-950 text-amber-300 border border-amber-800'
                          : 'bg-slate-800 text-slate-300'
                      }`}
                    >
                      {c.severity}
                    </span>
                  </div>

                  <div className="text-[11px] text-slate-400 font-mono mb-1.5">
                    Perpetrator: <span className="text-slate-200 font-semibold">{c.perpetrator}</span> → Victim:{' '}
                    <span className="text-slate-200 font-semibold">{c.victim}</span>
                  </div>

                  <p className="text-xs text-slate-300/90 leading-relaxed">{c.description}</p>
                </div>
              ))}
            </div>
          </div>

          <p className="text-[11px] text-slate-400 font-mono mt-3 pt-2 border-t border-slate-800">
            Mechanism-based Time Dependent Inhibition (TDI) requires kinact/KI validation in human liver microsomes.
          </p>
        </div>
      </div>
    </section>
  );
};
