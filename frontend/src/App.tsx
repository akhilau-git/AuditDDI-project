/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useState, useEffect } from 'react';
import { Sidebar, PageId } from './components/Sidebar.tsx';
import { CompoundInputDeck } from './components/CompoundInputDeck.tsx';
import { DDIPredictionStudio } from './components/DDIPredictionStudio.tsx';
import { Pillar1ADMET } from './components/Pillar1ADMET.tsx';
import { Pillar2Toxicity } from './components/Pillar2Toxicity.tsx';
import { Pillar3ICHM12 } from './components/Pillar3ICHM12.tsx';
import { Pillar4Synergy } from './components/Pillar4Synergy.tsx';
import { ADRProfileCard } from './components/ADRProfileCard.tsx';
import { MetabolicSimulator } from './components/MetabolicSimulator.tsx';
import { EvidenceExplorer } from './components/EvidenceExplorer.tsx';
import { EvaluationLab } from './components/EvaluationLab.tsx';
import { BatchScreeningLab } from './components/BatchScreeningLab.tsx';
import { ModelGovernance } from './components/ModelGovernance.tsx';
import { INDDossierModal } from './components/INDDossierModal.tsx';
import { FullAnalysisPayload } from './types/pharmacology.ts';
import {
  FileText,
  AlertTriangle,
  RefreshCw,
} from 'lucide-react';

export default function App() {
  const [activePage, setActivePage] = useState<PageId>('ddi');
  const [leadInput, setLeadInput] = useState('Amiodarone');
  const [coMedInput, setCoMedInput] = useState('Warfarin');

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [data, setData] = useState<FullAnalysisPayload | null>(null);
  const [isDossierOpen, setIsDossierOpen] = useState(false);

  const executeAnalysis = async (lead = leadInput, coMed = coMedInput, isSmiles = false) => {
    if (!lead || !coMed) return;
    setLoading(true);
    setError(null);
    try {
      const res = await fetch('/api/analyze', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ lead: lead.trim(), coMed: coMed.trim(), isSmiles }),
      });
      const body = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(body.error || body.detail || `Server returned HTTP ${res.status}`);
      const json: FullAnalysisPayload = body;
      setData(json);
      setLeadInput(json.leadCompound.name);
      setCoMedInput(json.coMedication.name);
    } catch (err) {
      console.error(err);
      setError(err instanceof Error ? err.message : 'Analysis request failed.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    executeAnalysis('Amiodarone', 'Warfarin', false);
  }, []);

  const handleLoadPairFromBatch = (drugA: string, drugB: string) => {
    setLeadInput(drugA);
    setCoMedInput(drugB);
    setActivePage('ddi');
    executeAnalysis(drugA, drugB, false);
  };

  const hasCriticalRisk =
    data?.cypConflicts.some((c) => c.severity === 'Contraindicated') ||
    data?.ichM12.requiresClinicalTrial ||
    (data?.leadCompound.cipaProfile.hergIc50 ?? 10) < 1.0;

  const PAGE_TITLES: Record<PageId, { title: string; subtitle: string }> = {
    ddi: { title: 'DDI Prediction Analysis', subtitle: 'Calibrated P(DDI), Uncertainty & Conformal Coverage' },
    admet: { title: 'ADMET Property Checking & 3D Conformer', subtitle: 'Physicochemical Space, Lipinski Heuristics & WebGL 3D Rotation' },
    toxicity: { title: 'Toxicity Liability Evaluation & CiPA Panel', subtitle: 'hERG/Nav1.5/Cav1.2 Channels, DILI Transporters & Boxed Warnings' },
    ichm12: { title: 'ICH M12 Regulatory Compliance Engine', subtitle: 'FDA/EMA/PMDA Statutory Reversible Inhibition Cutoff Engine' },
    synergy: { title: 'Preclinical Co-Dosing Synergy & Organ Burden', subtitle: 'openFDA FAERS Signals, ROR Disproportionality & Organ Burden' },
    adrs: { title: 'Adverse Drug Reaction (ADR) Spectrum', subtitle: 'MedDRA Terms & Compounded "Double-Hit" Organ Liabilities' },
    simulator: { title: 'Pharmacokinetic Clearance Simulator', subtitle: '1-Compartment IVIVE Dynamic Clearance & Staggered Dosing' },
    evidence: { title: 'Multisource Evidence Explorer', subtitle: '7-Database Provenance (TWOSIDES, ChEMBL, PubChem, openFDA, PharmGKB)' },
    evaluation: { title: 'Model Evaluation & Reliability Lab', subtitle: 'Transductive, S1, S2 Benchmark Splits & Calibration Curves' },
    batch: { title: 'High-Throughput Batch Screening Queue', subtitle: 'Multi-Compound Screening, Pareto Ranking & CSV/JSON Export' },
    governance: { title: 'Model Governance & Research Run Registry', subtitle: 'Checkpoints, Cryptographic Hashes & Upstream Dataset Lineage' },
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex font-sans selection:bg-cyan-500 selection:text-slate-950">
      {/* Left Navigation Sidebar */}
      <Sidebar
        activePage={activePage}
        onSelectPage={setActivePage}
        apiMetadata={data?.apiSourceMetadata}
      />

      {/* Right Main Content Area */}
      <div className="flex-1 flex flex-col min-w-0 overflow-y-auto h-screen">
        {/* Top Header Bar */}
        <header className="sticky top-0 z-30 bg-slate-950/90 backdrop-blur-md border-b border-slate-800 px-6 py-3 flex items-center justify-between gap-4">
          <div className="flex items-center gap-3 truncate">
            <div>
              <h1 className="text-sm font-bold text-white font-mono truncate">
                {PAGE_TITLES[activePage].title}
              </h1>
              <p className="text-[11px] text-slate-400 font-mono hidden sm:block">
                {PAGE_TITLES[activePage].subtitle}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-3 shrink-0">
            {/* Risk Status Pill */}
            {data && (
              <div
                className={`hidden md:flex items-center gap-1.5 px-2.5 py-1 rounded text-xs font-mono font-semibold border ${
                  hasCriticalRisk
                    ? 'bg-rose-950/60 text-rose-300 border-rose-800/80'
                    : 'bg-emerald-950/60 text-emerald-300 border-emerald-800/80'
                }`}
              >
                <AlertTriangle className={`w-3.5 h-3.5 ${hasCriticalRisk ? 'text-rose-400' : 'text-emerald-400'}`} />
                <span>{hasCriticalRisk ? 'Critical Risk' : 'Cleared'}</span>
              </div>
            )}

            <button
              onClick={() => setIsDossierOpen(true)}
              className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold text-slate-100 bg-slate-900 border border-slate-700 hover:border-cyan-500 hover:text-cyan-300 rounded-lg transition whitespace-nowrap shadow-sm font-mono"
            >
              <FileText className="w-3.5 h-3.5 text-cyan-400" />
              <span>Export Dossier</span>
            </button>
          </div>
        </header>

        {/* Right Main Content Body */}
        <main className="flex-1 p-6 max-w-6xl w-full mx-auto">
          {/* Compound Input Deck (Supports both Drug Names and raw Chemical SMILES!) */}
          <CompoundInputDeck
            onAnalyze={executeAnalysis}
            loading={loading}
            activeLeadName={data?.leadCompound.name || leadInput}
            activeCoMedName={data?.coMedication.name || coMedInput}
            activeLeadSmiles={data?.leadCompound.canonicalSmiles}
            activeCoMedSmiles={data?.coMedication.canonicalSmiles}
          />

          {error && (
            <div className="mb-4 p-3 rounded-lg bg-rose-950/40 border border-rose-900/60 text-xs text-rose-300 flex items-center gap-2 font-mono">
              <AlertTriangle className="w-4 h-4 text-rose-400 shrink-0" />
              <span>{error}</span>
            </div>
          )}

          {/* Render ONLY the single selected page/module on the right */}
          {loading && !data ? (
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-12 text-center text-xs font-mono text-slate-400">
              <RefreshCw className="w-6 h-6 text-cyan-400 animate-spin mx-auto mb-3" />
              <span>Querying Live PubChem, ChEMBL, openFDA, and Running Calibrated Models...</span>
            </div>
          ) : (
            <div>
              {/* DDI Prediction Analysis */}
              {activePage === 'ddi' && data && (
                <DDIPredictionStudio
                  prediction={data.ddiModelPrediction}
                />
              )}

              {/* ADMET Property Checking (with 2D & 3D Rotatable Conformer) */}
              {activePage === 'admet' && data && (
                <Pillar1ADMET lead={data.leadCompound} coMed={data.coMedication} />
              )}

              {/* Toxicity Liability Evaluation & CiPA Panel */}
              {activePage === 'toxicity' && data && (
                <Pillar2Toxicity lead={data.leadCompound} coMed={data.coMedication} />
              )}

              {/* ICH M12 Regulatory Compliance Engine */}
              {activePage === 'ichm12' && data && (
                <Pillar3ICHM12 ichM12={data.ichM12} cypConflicts={data.cypConflicts} />
              )}

              {/* Preclinical Co-Dosing Synergy */}
              {activePage === 'synergy' && data && (
                <Pillar4Synergy
                  leadName={data.leadCompound.name}
                  coMedName={data.coMedication.name}
                  synergySignals={data.synergySignals}
                  organStressList={data.organStressList}
                />
              )}

              {/* Page 6: Adverse Drug Reaction (ADR) Spectrum */}
              {activePage === 'adrs' && data && (
                <ADRProfileCard
                  lead={data.leadCompound}
                  coMed={data.coMedication}
                  doubleHitADRs={data.doubleHitADRs}
                />
              )}

              {/* Page 7: PK Metabolic Plumbing Simulator */}
              {activePage === 'simulator' && data && (
                <MetabolicSimulator
                  leadName={data.leadCompound.name}
                  coMedName={data.coMedication.name}
                  hasInhibition={data.cypConflicts.some((c) => c.severity === 'Major' || c.severity === 'Contraindicated')}
                />
              )}

              {/* Page 8: 7-Source Evidence Explorer */}
              {activePage === 'evidence' && data && (
                <EvidenceExplorer
                  evidence={data.sevenSourceEvidence}
                  lead={data.leadCompound}
                  coMed={data.coMedication}
                />
              )}

              {/* Page 9: Model Evaluation & Reliability Lab */}
              {activePage === 'evaluation' && <EvaluationLab />}

              {/* Page 10: Batch Screening Lab */}
              {activePage === 'batch' && <BatchScreeningLab onLoadPair={handleLoadPairFromBatch} />}

              {/* Page 11: Model Governance & Run Registry */}
              {activePage === 'governance' && <ModelGovernance />}
            </div>
          )}
        </main>
      </div>

      {/* Exportable Traceable IND Dossier Modal */}
      {data && (
        <INDDossierModal
          data={data}
          isOpen={isDossierOpen}
          onClose={() => setIsDossierOpen(false)}
        />
      )}
    </div>
  );
}
