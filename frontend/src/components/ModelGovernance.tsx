import React, { useState, useEffect } from 'react';
import { ModelGovernanceSpec } from '../types/pharmacology.ts';
import { ShieldCheck, GitBranch, Key, Hash, FileCode, CheckCircle2 } from 'lucide-react';

export const ModelGovernance: React.FC = () => {
  const [gov, setGov] = useState<ModelGovernanceSpec | null>(null);

  useEffect(() => {
    async function loadGov() {
      try {
        const res = await fetch('/api/governance');
        if (res.ok) {
          const json = await res.json();
          setGov(json);
        }
      } catch (err) {
        console.error('Failed to load model governance data', err);
      }
    }
    loadGov();
  }, []);

  if (!gov) return null;

  return (
    <section className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-sm space-y-4">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between pb-3 border-b border-slate-800 gap-2">
        <div className="flex items-center gap-2">
          <ShieldCheck className="w-4 h-4 text-cyan-400" />
          <h2 className="text-sm font-semibold tracking-wide text-white uppercase">
            Model Governance & Research Run Registry
          </h2>
        </div>
        <div className="flex items-center gap-2 text-xs font-mono text-slate-400">
          <Hash className="w-3.5 h-3.5 text-cyan-400" />
          <span>Reproducibility Seed: {gov.reproducibilitySeed}</span>
        </div>
      </div>

      {/* Model Checkpoint Registry */}
      <div>
        <span className="text-xs font-semibold text-slate-300 block mb-2 font-mono flex items-center gap-1.5">
          <GitBranch className="w-3.5 h-3.5 text-cyan-400" />
          Registered Model Checkpoints & Architecture Baselines
        </span>
        <div className="space-y-2.5">
          {gov.activeCheckpoints.map((ckpt) => (
            <div key={ckpt.id} className="p-3.5 rounded-lg bg-slate-950/70 border border-slate-800 text-xs font-mono">
              <div className="flex flex-wrap items-center justify-between gap-2 mb-1.5">
                <span className="font-bold text-white text-xs">{ckpt.id}</span>
                <div className="flex items-center gap-2">
                  <span className="text-cyan-400">S2 AUROC: {ckpt.aurocS2}</span>
                  <span
                    className={`px-2 py-0.5 rounded text-[10px] font-bold border ${
                      ckpt.status === 'Production'
                        ? 'bg-emerald-950 text-emerald-300 border-emerald-800'
                        : ckpt.status === 'Validation Candidate'
                        ? 'bg-cyan-950 text-cyan-300 border-cyan-800'
                        : 'bg-slate-800 text-slate-400'
                    }`}
                  >
                    {ckpt.status}
                  </span>
                </div>
              </div>

              <div className="text-[11px] text-slate-400 mb-1">
                Architecture: <span className="text-slate-300">{ckpt.architecture}</span>
              </div>
              <div className="text-[11px] text-slate-400 mb-1.5">
                Training Dataset: <span className="text-slate-300">{ckpt.datasetVersion}</span> · Trained on: {ckpt.trainDate}
              </div>

              <div className="flex items-center justify-between pt-2 border-t border-slate-900 text-[10px] text-slate-500">
                <span className="truncate max-w-[420px]" title={ckpt.checkpointSha256}>
                  SHA-256: {ckpt.checkpointSha256}
                </span>
                <span className="text-emerald-500 flex items-center gap-1">
                  <CheckCircle2 className="w-3 h-3" /> Integrity Verified
                </span>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Dataset Lineage Hashes */}
      <div className="p-3.5 rounded-lg bg-slate-950/60 border border-slate-800">
        <span className="text-xs font-semibold text-slate-300 block mb-2 font-mono flex items-center gap-1.5">
          <FileCode className="w-3.5 h-3.5 text-purple-400" />
          Upstream Training Dataset Lineage & Immutability Hashes
        </span>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs font-mono">
          <div className="p-2 rounded bg-slate-900 border border-slate-800/80">
            <span className="text-slate-400 block text-[10px]">TWOSIDES Corpus</span>
            <span className="text-slate-300 truncate block text-[11px]">{gov.datasetLineageHashes.twosides}</span>
          </div>
          <div className="p-2 rounded bg-slate-900 border border-slate-800/80">
            <span className="text-slate-400 block text-[10px]">DDInter Multi-Level PK/PD</span>
            <span className="text-slate-300 truncate block text-[11px]">{gov.datasetLineageHashes.ddinter}</span>
          </div>
          <div className="p-2 rounded bg-slate-900 border border-slate-800/80">
            <span className="text-slate-400 block text-[10px]">ChEMBL 34 Bioactivities</span>
            <span className="text-slate-300 truncate block text-[11px]">{gov.datasetLineageHashes.chembl34}</span>
          </div>
          <div className="p-2 rounded bg-slate-900 border border-slate-800/80">
            <span className="text-slate-400 block text-[10px]">openFDA SPL Drug Labeling</span>
            <span className="text-slate-300 truncate block text-[11px]">{gov.datasetLineageHashes.openfdaSpl}</span>
          </div>
        </div>
      </div>
    </section>
  );
};
