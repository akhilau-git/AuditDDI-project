import React, { useState, useEffect } from 'react';
import { EvaluationLabData } from '../types/pharmacology.ts';
import { LineChart, BarChart3, AlertOctagon, CheckCircle2, RefreshCw, Zap } from 'lucide-react';

export const EvaluationLab: React.FC = () => {
  const [data, setData] = useState<EvaluationLabData | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [selectedSplit, setSelectedSplit] = useState<'transductive' | 's1UnseenDrug' | 's2UnseenPair'>('s2UnseenPair');

  useEffect(() => {
    async function fetchEval() {
      try {
        const res = await fetch('/api/evaluation');
        if (res.ok) {
          const json = await res.json();
          setData(json);
        }
      } catch (err) {
        console.error('Failed to load evaluation data', err);
      } finally {
        setLoading(false);
      }
    }
    fetchEval();
  }, []);

  if (loading || !data) {
    return (
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-8 text-center text-xs font-mono text-slate-400">
        <RefreshCw className="w-5 h-5 text-cyan-400 animate-spin mx-auto mb-2" />
        <span>Loading Benchmark Validation Splits & Calibration Logs...</span>
      </div>
    );
  }

  const currentSplit = data.splits[selectedSplit];

  // SVG Reliability Diagram Math (10 bins from 0 to 1)
  const chartW = 320;
  const chartH = 220;
  const pL = 40;
  const pB = 30;
  const plotW = chartW - pL - 15;
  const plotH = chartH - pB - 15;

  const toX = (val: number) => pL + val * plotW;
  const toY = (val: number) => 15 + plotH - val * plotH;

  const curvePoints = data.calibrationBins
    .map((b, i) => `${i === 0 ? 'M' : 'L'} ${toX(b.predictedMean).toFixed(1)} ${toY(b.observedFraction).toFixed(1)}`)
    .join(' ');

  return (
    <section className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-sm space-y-5">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between pb-3 border-b border-slate-800 gap-2">
        <div className="flex items-center gap-2">
          <BarChart3 className="w-4 h-4 text-cyan-400" />
          <h2 className="text-sm font-semibold tracking-wide text-white uppercase">
            Model Evaluation & Reliability Lab
          </h2>
        </div>

        {/* Split Regime Toggle */}
        <div className="flex items-center bg-slate-950 p-1 rounded-lg border border-slate-800 text-xs font-mono">
          <button
            onClick={() => setSelectedSplit('transductive')}
            className={`px-2.5 py-1 rounded transition ${
              selectedSplit === 'transductive'
                ? 'bg-cyan-950 text-cyan-300 font-bold border border-cyan-800'
                : 'text-slate-400 hover:text-white'
            }`}
          >
            Transductive (Graph)
          </button>
          <button
            onClick={() => setSelectedSplit('s1UnseenDrug')}
            className={`px-2.5 py-1 rounded transition ${
              selectedSplit === 's1UnseenDrug'
                ? 'bg-cyan-950 text-cyan-300 font-bold border border-cyan-800'
                : 'text-slate-400 hover:text-white'
            }`}
          >
            S1 (Unseen Drug)
          </button>
          <button
            onClick={() => setSelectedSplit('s2UnseenPair')}
            className={`px-2.5 py-1 rounded transition ${
              selectedSplit === 's2UnseenPair'
                ? 'bg-cyan-950 text-cyan-300 font-bold border border-cyan-800'
                : 'text-slate-400 hover:text-white'
            }`}
          >
            S2 (Unseen Pair / Inductive)
          </button>
        </div>
      </div>

      {/* Split Comparison KPI Grid */}
      <div className="grid grid-cols-2 sm:grid-cols-5 gap-3">
        <div className="p-3 bg-slate-950/70 rounded-lg border border-slate-800">
          <span className="text-[11px] text-slate-400 font-mono block">AUROC</span>
          <p className="text-xl font-bold font-mono text-cyan-400 mt-0.5 tabular-nums">{currentSplit.auroc}</p>
          <span className="text-[10px] text-slate-500 font-mono">Area under ROC curve</span>
        </div>

        <div className="p-3 bg-slate-950/70 rounded-lg border border-slate-800">
          <span className="text-[11px] text-slate-400 font-mono block">PR-AUC</span>
          <p className="text-xl font-bold font-mono text-emerald-400 mt-0.5 tabular-nums">{currentSplit.prAuc}</p>
          <span className="text-[10px] text-slate-500 font-mono">Precision-Recall AUC</span>
        </div>

        <div className="p-3 bg-slate-950/70 rounded-lg border border-slate-800">
          <span className="text-[11px] text-slate-400 font-mono block">MCC</span>
          <p className="text-xl font-bold font-mono text-white mt-0.5 tabular-nums">{currentSplit.mcc}</p>
          <span className="text-[10px] text-slate-500 font-mono">Matthews correlation</span>
        </div>

        <div className="p-3 bg-slate-950/70 rounded-lg border border-slate-800">
          <span className="text-[11px] text-slate-400 font-mono block">Brier Score</span>
          <p className="text-xl font-bold font-mono text-amber-400 mt-0.5 tabular-nums">{currentSplit.brierScore}</p>
          <span className="text-[10px] text-slate-500 font-mono">Calibration loss (lower=better)</span>
        </div>

        <div className="p-3 bg-slate-950/70 rounded-lg border border-slate-800">
          <span className="text-[11px] text-slate-400 font-mono block">ECE (Expected Error)</span>
          <p className="text-xl font-bold font-mono text-purple-400 mt-0.5 tabular-nums">{currentSplit.ece}</p>
          <span className="text-[10px] text-slate-500 font-mono">Tested on {currentSplit.nPairs.toLocaleString()} pairs</span>
        </div>
      </div>

      {/* Center 2-Column: Calibration Reliability Diagram & Conformal Prediction */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-5">
        {/* Left: Calibration Plot */}
        <div className="lg:col-span-6 bg-slate-950/60 rounded-lg border border-slate-800/80 p-4">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-semibold text-slate-200 font-mono">
              Reliability Diagram (Calibration Curve)
            </span>
            <span className="text-[10px] font-mono text-cyan-400">
              ECE = {currentSplit.ece}
            </span>
          </div>
          <p className="text-[11px] text-slate-400 mb-2">
            Compares mean predicted probability with empirical observed frequency across 10 probability deciles.
          </p>

          <div className="w-full flex justify-center">
            <svg viewBox={`0 0 ${chartW} ${chartH}`} className="w-full max-w-[340px]">
              {/* Grid Lines */}
              {[0, 0.25, 0.5, 0.75, 1.0].map((v) => (
                <g key={v}>
                  <line
                    x1={pL}
                    y1={toY(v)}
                    x2={pL + plotW}
                    y2={toY(v)}
                    stroke="#1e293b"
                    strokeWidth="1"
                  />
                  <line
                    x1={toX(v)}
                    y1={15}
                    x2={toX(v)}
                    y2={15 + plotH}
                    stroke="#1e293b"
                    strokeWidth="1"
                  />
                  <text
                    x={pL - 6}
                    y={toY(v) + 3}
                    textAnchor="end"
                    fill="#64748b"
                    fontSize="9"
                    fontFamily="monospace"
                  >
                    {v.toFixed(2)}
                  </text>
                  <text
                    x={toX(v)}
                    y={15 + plotH + 16}
                    textAnchor="middle"
                    fill="#64748b"
                    fontSize="9"
                    fontFamily="monospace"
                  >
                    {v.toFixed(2)}
                  </text>
                </g>
              ))}

              {/* Ideal Diagonal (y = x) */}
              <line
                x1={toX(0)}
                y1={toY(0)}
                x2={toX(1)}
                y2={toY(1)}
                stroke="#475569"
                strokeWidth="1.2"
                strokeDasharray="4,4"
              />

              {/* Model Observed Curve */}
              <path d={curvePoints} fill="none" stroke="#06b6d4" strokeWidth="2.2" />

              {/* Data points */}
              {data.calibrationBins.map((b) => (
                <circle
                  key={b.binIndex}
                  cx={toX(b.predictedMean)}
                  cy={toY(b.observedFraction)}
                  r="3.5"
                  fill="#06b6d4"
                  stroke="#020617"
                  strokeWidth="1.5"
                />
              ))}
            </svg>
          </div>

          <div className="flex justify-between text-[10px] text-slate-400 font-mono mt-1 pt-2 border-t border-slate-800">
            <span>Dashed: Ideal y = x calibration</span>
            <span className="text-cyan-400 font-bold">Platt-calibrated AuditDDI-GNN</span>
          </div>
        </div>

        {/* Right: Conformal Prediction & Confusion Matrix */}
        <div className="lg:col-span-6 bg-slate-950/60 rounded-lg border border-slate-800/80 p-4 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-semibold text-slate-200 font-mono">
                Conformal Coverage & Confusion Matrix
              </span>
              <span className="text-[10px] font-mono text-emerald-400">
                Split: {selectedSplit}
              </span>
            </div>

            {/* Conformal Coverage Banner */}
            <div className="p-3 rounded-lg bg-slate-900 border border-slate-800 text-xs mb-3">
              <div className="flex justify-between font-mono mb-1">
                <span className="text-slate-400">Target Coverage Level:</span>
                <span className="font-bold text-white">95.0%</span>
              </div>
              <div className="flex justify-between font-mono mb-1">
                <span className="text-slate-400">Empirical Coverage on Test Set:</span>
                <span className="font-bold text-emerald-400">
                  {(data.conformalCoverage.empiricalCoverage * 100).toFixed(1)}%
                </span>
              </div>
              <div className="flex justify-between font-mono">
                <span className="text-slate-400">Average Interval Width:</span>
                <span className="font-bold text-cyan-400">
                  ±{(data.conformalCoverage.meanIntervalWidth / 2 * 100).toFixed(1)}%
                </span>
              </div>
            </div>

            {/* 2x2 Confusion Matrix */}
            <span className="text-[11px] font-mono text-slate-400 block mb-1.5">
              Held-Out Test Confusion Matrix (τ = 0.50):
            </span>
            <div className="grid grid-cols-2 gap-2 text-xs font-mono">
              <div className="p-2.5 rounded bg-emerald-950/40 border border-emerald-900/60">
                <span className="text-[10px] text-slate-400 block">True Positives (TP)</span>
                <p className="text-base font-bold text-emerald-300 tabular-nums">{data.confusionMatrix.tp}</p>
                <span className="text-[10px] text-slate-500">Correctly identified DDIs</span>
              </div>
              <div className="p-2.5 rounded bg-rose-950/40 border border-rose-900/60">
                <span className="text-[10px] text-slate-400 block">False Positives (FP)</span>
                <p className="text-base font-bold text-rose-300 tabular-nums">{data.confusionMatrix.fp}</p>
                <span className="text-[10px] text-slate-500">Predicted DDI, ground truth neg</span>
              </div>
              <div className="p-2.5 rounded bg-rose-950/40 border border-rose-900/60">
                <span className="text-[10px] text-slate-400 block">False Negatives (FN)</span>
                <p className="text-base font-bold text-rose-300 tabular-nums">{data.confusionMatrix.fn}</p>
                <span className="text-[10px] text-slate-500">Missed severe interaction</span>
              </div>
              <div className="p-2.5 rounded bg-emerald-950/40 border border-emerald-900/60">
                <span className="text-[10px] text-slate-400 block">True Negatives (TN)</span>
                <p className="text-base font-bold text-emerald-300 tabular-nums">{data.confusionMatrix.tn}</p>
                <span className="text-[10px] text-slate-500">Correctly identified safe pairs</span>
              </div>
            </div>
          </div>

          <div className="mt-3 pt-2 border-t border-slate-800 text-[10px] text-slate-400 font-mono">
            Sensitivity: {((data.confusionMatrix.tp / (data.confusionMatrix.tp + data.confusionMatrix.fn)) * 100).toFixed(1)}% · Specificity: {((data.confusionMatrix.tn / (data.confusionMatrix.tn + data.confusionMatrix.fp)) * 100).toFixed(1)}%
          </div>
        </div>
      </div>

      {/* Error Analysis Studio */}
      <div className="p-4 rounded-lg bg-slate-950/60 border border-slate-800">
        <div className="flex items-center gap-2 mb-2 pb-2 border-b border-slate-800">
          <AlertOctagon className="w-4 h-4 text-amber-400" />
          <h3 className="text-xs font-bold text-slate-200 uppercase font-mono">
            Error Analysis Studio (Root-Cause Investigation)
          </h3>
        </div>
        <p className="text-xs text-slate-400 mb-3">
          Deep diagnostic audit of false positive (FP) and false negative (FN) pairs to identify chemical representation liabilities and model blind spots:
        </p>

        <div className="space-y-2.5">
          {data.errorStudioCases.map((c, i) => (
            <div key={i} className="p-3 rounded bg-slate-900 border border-slate-800 text-xs">
              <div className="flex flex-wrap items-center justify-between gap-2 mb-1">
                <span className="font-bold text-slate-200 font-mono">{c.pair}</span>
                <div className="flex items-center gap-2 font-mono text-[11px]">
                  <span
                    className={`px-2 py-0.2 rounded font-bold border ${
                      c.errorType.includes('FN')
                        ? 'bg-rose-950 text-rose-300 border-rose-800'
                        : 'bg-amber-950 text-amber-300 border-amber-800'
                    }`}
                  >
                    {c.errorType}
                  </span>
                  <span className="text-slate-400">P(DDI) = {(c.predictedProb * 100).toFixed(0)}%</span>
                </div>
              </div>
              <div className="text-[11px] text-cyan-300 font-mono mb-1">
                Liability: {c.structuralLiability}
              </div>
              <p className="text-[11px] text-slate-400 leading-relaxed">{c.rootCauseAnalysis}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
};
