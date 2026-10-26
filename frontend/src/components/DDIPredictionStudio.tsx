import React from 'react';
import { DDIModelPrediction } from '../types/pharmacology.ts';
import { Brain, ShieldAlert, CheckCircle2, AlertTriangle, Fingerprint, Cpu } from 'lucide-react';

interface DDIPredictionStudioProps {
  prediction: DDIModelPrediction;
}

export const DDIPredictionStudio: React.FC<DDIPredictionStudioProps> = ({ prediction }) => {
  if (prediction.status === 'unavailable') {
    return (
      <section className="bg-slate-900 border border-amber-800/60 rounded-xl p-5 shadow-sm space-y-3">
        <div className="flex items-center gap-2 text-white"><Brain className="w-4 h-4 text-amber-400" /><h2 className="text-sm font-semibold uppercase">DDI model unavailable</h2></div>
        <p className="text-sm text-amber-100">{prediction.message}</p>
        <p className="text-xs text-slate-400">The app will not substitute a simulated score. Start the FastAPI service and configure a compatible trained checkpoint and feature bundle.</p>
      </section>
    );
  }

  const isInteracting = prediction.interactionPredicted;
  const probPercent = (prediction.calibratedScore * 100).toFixed(1);
  const uncertaintyAvailable = prediction.uncertainty.status.startsWith('available');
  const inDomain = prediction.applicabilityDomain.outsideDomain === false;

  return (
    <section className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-sm space-y-4">
      <div className="flex flex-wrap items-center justify-between pb-3 border-b border-slate-800 gap-2">
        <div className="flex items-center gap-2">
          <Brain className="w-4 h-4 text-cyan-400" />
          <h2 className="text-sm font-semibold tracking-wide text-white uppercase">
            DDI Prediction Analysis
          </h2>
        </div>
        <div className="flex items-center gap-2 text-xs font-mono text-slate-400">
          <Cpu className="w-3.5 h-3.5 text-cyan-400" />
          <span>Model: {prediction.modelArchitecture}</span>
        </div>
      </div>

      {/* Main Prediction Scoreboard */}
      <div className="grid grid-cols-1 md:grid-cols-12 gap-4">
        {/* Probability Card */}
        <div className="md:col-span-5 bg-slate-950/70 border border-slate-800 rounded-lg p-4 flex flex-col justify-between">
          <div>
            <span className="text-[11px] font-mono uppercase text-slate-400 block mb-1">
              {prediction.calibration.status === 'internally_calibrated' ? 'Calibrated reported-interaction score' : 'Reported-interaction model score'}
            </span>
            <div className="flex items-baseline gap-2">
              <span
                className={`text-4xl font-mono font-bold tracking-tight tabular-nums ${
                  isInteracting ? 'text-rose-400' : 'text-emerald-400'
                }`}
              >
                {probPercent}%
              </span>
              <span className="text-xs font-mono text-slate-400">
                (research estimate, not clinical probability)
              </span>
            </div>

            {/* Threshold Bar */}
            <div className="mt-3">
              <div className="flex justify-between text-[10px] font-mono text-slate-400 mb-1">
                <span>Decision Threshold (τ = {prediction.decisionThreshold.toFixed(3)})</span>
                <span>Calibrated: {prediction.calibratedScore.toFixed(4)}</span>
              </div>
              <div className="w-full bg-slate-800 h-2 rounded-full overflow-hidden relative">
                <div
                  className={`h-full ${isInteracting ? 'bg-rose-500' : 'bg-emerald-500'}`}
                  style={{ width: `${prediction.calibratedScore * 100}%` }}
                />
                <div
                  className="absolute top-0 bottom-0 w-0.5 bg-amber-400"
                  style={{ left: `${prediction.decisionThreshold * 100}%` }}
                  title={`Decision Threshold ${prediction.decisionThreshold}`}
                />
              </div>
            </div>
          </div>

          <div className="mt-4 pt-3 border-t border-slate-800/80 flex items-center justify-between text-xs">
            <span className="text-slate-400">Model Classification:</span>
            <span
              className={`font-mono font-bold px-2 py-0.5 rounded text-[11px] border ${
                isInteracting
                  ? 'bg-rose-950 text-rose-300 border-rose-800'
                  : 'bg-emerald-950 text-emerald-300 border-emerald-800'
              }`}
            >
              {isInteracting ? 'Reported interaction predicted' : 'Reported interaction not predicted'}
            </span>
          </div>
        </div>

        {/* Uncertainty & Conformal Interval Card */}
        <div className="md:col-span-4 bg-slate-950/70 border border-slate-800 rounded-lg p-4 flex flex-col justify-between">
          <div>
            <span className="text-[11px] font-mono uppercase text-slate-400 block mb-1">
              Prediction uncertainty
            </span>
            <div className="font-mono text-sm font-bold text-white mt-2">{uncertaintyAvailable ? prediction.uncertainty.prediction_set : 'Not available'}</div>
            <p className="text-[11px] text-slate-400 mt-2 leading-relaxed">
              {prediction.uncertainty.note}
            </p>
          </div>

          <div className="mt-3 pt-2 border-t border-slate-800/80 flex items-center justify-between text-xs">
            <span className="text-slate-400">Calibration:</span>
            <span className="font-mono text-cyan-300 font-semibold">{prediction.calibration.method || prediction.calibration.status}</span>
          </div>
        </div>

        {/* Applicability Domain (AD) Card */}
        <div className="md:col-span-3 bg-slate-950/70 border border-slate-800 rounded-lg p-4 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-1">
              <span className="text-[11px] font-mono uppercase text-slate-400">
                Applicability Domain
              </span>
              <Fingerprint className="w-3.5 h-3.5 text-cyan-400" />
            </div>

            <div className="flex items-center gap-1.5 mt-1">
              {inDomain ? (
                <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
              ) : (
                <AlertTriangle className="w-4 h-4 text-amber-400 shrink-0" />
              )}
              <span className="font-mono text-xs font-semibold text-white">
                {prediction.applicabilityDomain.outsideDomain === null ? 'Not assessed' : inDomain ? 'Within reference domain' : 'Outside reference domain'}
              </span>
            </div>

            <div className="text-[11px] font-mono text-slate-400 mt-2 space-y-0.5">
              <div>Pair minimum similarity: <strong className="text-slate-200">{prediction.applicabilityDomain.pairMinimumSimilarity === null ? 'Unavailable' : prediction.applicabilityDomain.pairMinimumSimilarity.toFixed(3)}</strong></div>
              <div className="text-[10px]">{prediction.applicabilityDomain.note}</div>
            </div>
          </div>

          <div className="mt-2 pt-2 border-t border-slate-800/80 text-[10px] text-slate-500 font-mono">
            Checkpoint: {prediction.checkpointHash ? prediction.checkpointHash.slice(0, 16) + '…' : 'hash unavailable'}
          </div>
        </div>
      </div>

      {prediction.sevenBranchInputCoverage && (
        <div className="rounded-lg border border-slate-800 bg-slate-950/50 p-3">
          <h3 className="text-[11px] font-mono uppercase text-slate-400 mb-2">Seven-input feature availability</h3>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
            {Object.entries(prediction.sevenBranchInputCoverage).map(([branch, coverage]) => (
              <div key={branch} className="text-[10px] text-slate-300">
                <span className="capitalize">{branch.replaceAll('_', ' ')}</span>: {coverage.drug_a && coverage.drug_b ? 'both drugs' : coverage.drug_a || coverage.drug_b ? 'one drug' : 'neither drug'}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Scientific Clarification Callout */}
      <div className="p-3 bg-slate-950/50 rounded-lg border border-slate-800/80 flex items-start gap-2.5 text-xs text-slate-400">
        <ShieldAlert className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
        <div>
          <strong className="text-slate-300 block font-semibold mb-0.5">
            Methodological Epistemic Note (TWOSIDES / R&D Scope)
          </strong>
          {prediction.interactionLabelNote} {prediction.interactionRiskNote} {prediction.disclaimer}
        </div>
      </div>
    </section>
  );
};
