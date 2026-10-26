import React, { useState } from 'react';
import { Sliders, AlertCircle, ShieldCheck } from 'lucide-react';

interface SimulatorProps {
  leadName: string;
  coMedName: string;
  hasInhibition: boolean;
}

export const MetabolicSimulator: React.FC<SimulatorProps> = ({
  leadName,
  coMedName,
  hasInhibition,
}) => {
  const [doseMg, setDoseMg] = useState<number>(100);
  const [staggerHours, setStaggerHours] = useState<number>(0);
  const [inhibitionStrength, setInhibitionStrength] = useState<number>(hasInhibition ? 75 : 20);

  // 1-compartment PK calculation over 24 hours (0 to 24 with 0.5h steps)
  // Parameters:
  // ka = absorption rate = 1.2 / hr
  // ke_baseline = elimination rate = 0.25 / hr (half life ~ 2.8 hr)
  // ke_inhibited = ke_baseline * (1 - inhibitionStrength/100 * overlap_factor)
  const ka = 1.2;
  const keBaseline = 0.25;
  const mtc = 65.0; // Minimum toxic concentration (ng/mL)
  const mec = 20.0; // Minimum effective concentration (ng/mL)

  const timePoints: { t: number; concBaseline: number; concInhibited: number }[] = [];
  let maxInhibitedConc = 0;
  let timeAboveMtc = 0;

  for (let t = 0; t <= 24; t += 0.5) {
    // Baseline single drug profile (given at t=0)
    const concBase = (doseMg * 0.8 * ka) / (ka - keBaseline) * (Math.exp(-keBaseline * t) - Math.exp(-ka * t));
    const cleanBase = Math.max(0, concBase);

    // Inhibited profile with staggered dosing delta
    // Lead inhibitor peak activity is around t = 1.5 to 4h
    // If coMed is given at t = staggerHours:
    const tCoMed = Math.max(0, t - staggerHours);
    let currentKe = keBaseline;

    if (t >= staggerHours) {
      // Overlap with inhibitor presence:
      const inhibitorConcAtTime = Math.exp(-0.15 * t); // inhibitor concentration decaying
      const activeInhibition = (inhibitionStrength / 100) * inhibitorConcAtTime;
      currentKe = keBaseline * (1 - Math.min(0.85, activeInhibition));
    }

    let concInhib = 0;
    if (t >= staggerHours) {
      concInhib = (doseMg * 0.8 * ka) / (ka - currentKe) * (Math.exp(-currentKe * tCoMed) - Math.exp(-ka * tCoMed));
      concInhib = Math.max(0, concInhib);
    }

    if (concInhib > maxInhibitedConc) maxInhibitedConc = concInhib;
    if (concInhib > mtc) timeAboveMtc += 0.5;

    timePoints.push({
      t,
      concBaseline: cleanBase,
      concInhibited: concInhib,
    });
  }

  // SVG Chart bounds
  const svgWidth = 540;
  const svgHeight = 220;
  const paddingLeft = 45;
  const paddingBottom = 30;
  const chartW = svgWidth - paddingLeft - 20;
  const chartH = svgHeight - paddingBottom - 20;

  const maxValY = 110;

  const toX = (t: number) => paddingLeft + (t / 24) * chartW;
  const toY = (val: number) => 20 + chartH - (Math.min(maxValY, val) / maxValY) * chartH;

  const baselinePath = timePoints
    .map((pt, i) => `${i === 0 ? 'M' : 'L'} ${toX(pt.t).toFixed(1)} ${toY(pt.concBaseline).toFixed(1)}`)
    .join(' ');

  const inhibitedPath = timePoints
    .map((pt, i) => `${i === 0 ? 'M' : 'L'} ${toX(pt.t).toFixed(1)} ${toY(pt.concInhibited).toFixed(1)}`)
    .join(' ');

  const toxicToxicityExceeded = maxInhibitedConc > mtc;

  return (
    <section id="simulator" className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-sm">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between pb-4 border-b border-slate-800 gap-2">
        <div className="flex items-center gap-2">
          <Sliders className="w-4 h-4 text-sky-400" />
          <h2 className="text-sm font-semibold tracking-wide text-white uppercase">
            Pharmacokinetic "Metabolic Plumbing" Clearance Simulator
          </h2>
        </div>
        <span className="text-xs font-mono text-slate-400">
          1-Compartment IVIVE Dynamic PK Engine
        </span>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-5 mt-4">
        {/* Controls Column */}
        <div className="lg:col-span-4 bg-slate-950/60 rounded-lg border border-slate-800/80 p-4 space-y-4">
          <span className="text-xs font-semibold text-slate-200 block pb-2 border-b border-slate-800">
            Dosing & Schedule Parameters
          </span>

          <div>
            <div className="flex justify-between text-xs mb-1">
              <span className="text-slate-300">{coMedName} Administered Dose</span>
              <span className="font-mono text-cyan-400 font-bold tabular-nums">{doseMg} mg</span>
            </div>
            <input
              type="range"
              min="25"
              max="200"
              step="5"
              value={doseMg}
              onChange={(e) => setDoseMg(parseInt(e.target.value, 10))}
              className="w-full accent-cyan-400 cursor-pointer h-1.5 bg-slate-800 rounded-lg"
            />
            <div className="flex justify-between text-[10px] text-slate-400 font-mono mt-0.5">
              <span>25 mg</span>
              <span>200 mg</span>
            </div>
          </div>

          <div>
            <div className="flex justify-between text-xs mb-1">
              <span className="text-slate-300">Staggered Dosing Offset (Δt)</span>
              <span className="font-mono text-emerald-400 font-bold tabular-nums">+{staggerHours} Hours</span>
            </div>
            <input
              type="range"
              min="0"
              max="8"
              step="1"
              value={staggerHours}
              onChange={(e) => setStaggerHours(parseInt(e.target.value, 10))}
              className="w-full accent-emerald-400 cursor-pointer h-1.5 bg-slate-800 rounded-lg"
            />
            <div className="flex justify-between text-[10px] text-slate-400 font-mono mt-0.5">
              <span>Co-ingested (0h)</span>
              <span>8h Delayed</span>
            </div>
          </div>

          <div>
            <div className="flex justify-between text-xs mb-1">
              <span className="text-slate-300">{leadName} CYP Inhibition Potency</span>
              <span className="font-mono text-amber-400 font-bold tabular-nums">{inhibitionStrength}%</span>
            </div>
            <input
              type="range"
              min="0"
              max="95"
              step="5"
              value={inhibitionStrength}
              onChange={(e) => setInhibitionStrength(parseInt(e.target.value, 10))}
              className="w-full accent-amber-400 cursor-pointer h-1.5 bg-slate-800 rounded-lg"
            />
            <div className="flex justify-between text-[10px] text-slate-400 font-mono mt-0.5">
              <span>0% (No conflict)</span>
              <span>95% (Near complete block)</span>
            </div>
          </div>

          {/* Real-time Stagger Advice */}
          <div className="pt-2 border-t border-slate-800">
            {toxicToxicityExceeded ? (
              <div className="p-2.5 rounded bg-rose-950/40 border border-rose-900/60 text-xs text-rose-300 flex items-start gap-2">
                <AlertCircle className="w-4 h-4 text-rose-400 shrink-0 mt-0.5" />
                <div>
                  <strong>Toxicity Window Breached!</strong> Peak concentration ({maxInhibitedConc.toFixed(1)} ng/mL) exceeds MTC threshold. Increase spacing to ≥4 hours or reduce dose.
                </div>
              </div>
            ) : (
              <div className="p-2.5 rounded bg-emerald-950/40 border border-emerald-900/60 text-xs text-emerald-300 flex items-start gap-2">
                <ShieldCheck className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
                <div>
                  <strong>Therapeutic Window Preserved!</strong> Peak concentration ({maxInhibitedConc.toFixed(1)} ng/mL) remains safely buffered between MEC and MTC.
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Dynamic Plasma Concentration Graph */}
        <div className="lg:col-span-8 bg-slate-950/60 rounded-lg border border-slate-800/80 p-4 flex flex-col justify-between">
          <div>
            <div className="flex flex-wrap items-center justify-between text-xs text-slate-400 mb-2 gap-2">
              <span className="font-medium text-slate-200">
                Plasma Concentration Over Time: <strong className="text-cyan-300">{coMedName}</strong>
              </span>
              <div className="flex items-center gap-4 text-[11px] font-mono">
                <span className="flex items-center gap-1.5 text-slate-400">
                  <span className="w-2.5 h-0.5 bg-slate-400" /> Monotherapy Baseline
                </span>
                <span className="flex items-center gap-1.5 text-rose-400">
                  <span className="w-2.5 h-0.5 bg-rose-500" /> With DDI Inhibition
                </span>
                <span className="flex items-center gap-1 text-rose-400">
                  <span className="w-2 h-0 border-t border-dashed border-rose-500" /> MTC ({mtc})
                </span>
              </div>
            </div>

            {/* SVG Plot */}
            <div className="w-full overflow-x-auto">
              <svg viewBox={`0 0 ${svgWidth} ${svgHeight}`} className="w-full h-auto min-w-[420px]">
                {/* Therapeutic Corridor Shading */}
                <rect
                  x={paddingLeft}
                  y={toY(mtc)}
                  width={chartW}
                  height={toY(mec) - toY(mtc)}
                  fill="rgba(16, 185, 129, 0.05)"
                />

                {/* Toxic Zone Shading */}
                <rect
                  x={paddingLeft}
                  y={20}
                  width={chartW}
                  height={toY(mtc) - 20}
                  fill="rgba(244, 63, 94, 0.08)"
                />

                {/* Grid Lines */}
                {[0, 20, 40, 60, 80, 100].map((val) => (
                  <g key={val}>
                    <line
                      x1={paddingLeft}
                      y1={toY(val)}
                      x2={paddingLeft + chartW}
                      y2={toY(val)}
                      stroke="#1e293b"
                      strokeWidth="1"
                    />
                    <text
                      x={paddingLeft - 8}
                      y={toY(val) + 3}
                      textAnchor="end"
                      fill="#64748b"
                      fontSize="9"
                      fontFamily="monospace"
                    >
                      {val}
                    </text>
                  </g>
                ))}

                {/* Time Axis Grid */}
                {[0, 4, 8, 12, 16, 20, 24].map((t) => (
                  <g key={t}>
                    <line
                      x1={toX(t)}
                      y1={20}
                      x2={toX(t)}
                      y2={20 + chartH}
                      stroke="#1e293b"
                      strokeWidth="1"
                    />
                    <text
                      x={toX(t)}
                      y={20 + chartH + 16}
                      textAnchor="middle"
                      fill="#64748b"
                      fontSize="9"
                      fontFamily="monospace"
                    >
                      {t}h
                    </text>
                  </g>
                ))}

                {/* MTC Threshold Line */}
                <line
                  x1={paddingLeft}
                  y1={toY(mtc)}
                  x2={paddingLeft + chartW}
                  y2={toY(mtc)}
                  stroke="#f43f5e"
                  strokeWidth="1.5"
                  strokeDasharray="4,4"
                />

                {/* MEC Threshold Line */}
                <line
                  x1={paddingLeft}
                  y1={toY(mec)}
                  x2={paddingLeft + chartW}
                  y2={toY(mec)}
                  stroke="#10b981"
                  strokeWidth="1.2"
                  strokeDasharray="3,3"
                />

                {/* Baseline Concentration Curve */}
                <path d={baselinePath} fill="none" stroke="#64748b" strokeWidth="1.8" />

                {/* Inhibited Concentration Curve */}
                <path
                  d={inhibitedPath}
                  fill="none"
                  stroke={toxicToxicityExceeded ? '#f43f5e' : '#06b6d4'}
                  strokeWidth="2.5"
                />
              </svg>
            </div>
          </div>

          <div className="mt-3 pt-2 border-t border-slate-800 flex items-center justify-between text-xs text-slate-400 font-mono">
            <span>Peak Conc (Cmax): <strong className="text-white">{maxInhibitedConc.toFixed(1)} ng/mL</strong></span>
            <span>Duration Above MTC: <strong className={timeAboveMtc > 0 ? 'text-rose-400' : 'text-emerald-400'}>{timeAboveMtc}h</strong></span>
            <span>Elimination Clearance: <strong className="text-white">{(keBaseline * (1 - inhibitionStrength / 100)).toFixed(3)} L/h</strong></span>
          </div>
        </div>
      </div>
    </section>
  );
};
