import React from 'react';
import { FullAnalysisPayload } from '../types/pharmacology.ts';
import { Printer, X, ShieldAlert, CheckCircle, FileText } from 'lucide-react';

interface DossierModalProps {
  data: FullAnalysisPayload;
  isOpen: boolean;
  onClose: () => void;
}

export const INDDossierModal: React.FC<DossierModalProps> = ({ data, isOpen, onClose }) => {
  if (!isOpen) return null;

  const lead = data.leadCompound;
  const coMed = data.coMedication;
  const ich = data.ichM12;

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto bg-black/80 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="relative bg-slate-950 border border-slate-700 rounded-xl max-w-4xl w-full max-h-[90vh] overflow-y-auto shadow-2xl text-slate-100 p-6 sm:p-8 print:p-0 print:border-none print:shadow-none print:max-h-none print:bg-white print:text-black">
        {/* Modal Controls (Hidden during print) */}
        <div className="flex items-center justify-between pb-4 border-b border-slate-800 print:hidden">
          <div className="flex items-center gap-2">
            <FileText className="w-5 h-5 text-cyan-400" />
            <h2 className="text-base font-bold text-white uppercase tracking-wider">
              Preclinical Regulatory Safety Dossier (FDA IND / ICH M12)
            </h2>
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={() => window.print()}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-cyan-600 hover:bg-cyan-500 text-white text-xs font-semibold shadow-sm transition"
            >
              <Printer className="w-3.5 h-3.5" /> Print / Save as PDF
            </button>
            <button
              onClick={onClose}
              className="p-1 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Printable Document Content */}
        <div className="mt-6 space-y-6 print:mt-0 font-sans">
          {/* Document Header */}
          <div className="border-b-2 border-slate-700 pb-4 print:border-black">
            <div className="flex justify-between items-start">
              <div>
                <span className="text-[11px] font-mono uppercase tracking-widest text-slate-400 print:text-slate-600 block">
                  Regulatory Submission Briefing Package
                </span>
                <h1 className="text-2xl font-bold tracking-tight text-white print:text-black mt-0.5">
                  Preclinical Safety & Polypharmacology Evaluation
                </h1>
                <p className="text-xs text-slate-400 print:text-slate-600 font-mono mt-1">
                  Compound Pair: {lead.name} (Candidate NCE) + {coMed.name} (Standard of Care)
                </p>
              </div>
              <div className="text-right font-mono text-xs text-slate-400 print:text-slate-600">
                <div>Document ID: IND-AUD-{lead.cid || '001'}</div>
                <div>Generated: {new Date().toLocaleDateString()}</div>
                <div>Platform: AuditDDI Workbench</div>
              </div>
            </div>
          </div>

          {/* Executive Summary & Regulatory Verdict */}
          <div className="p-4 rounded-lg bg-slate-900 border border-slate-800 print:bg-slate-50 print:border-slate-300">
            <h3 className="text-xs font-bold uppercase tracking-wider text-cyan-400 print:text-cyan-800 font-mono mb-2">
              Executive Regulatory Verdict (ICH M12 Compliance)
            </h3>
            <div className="flex items-start gap-3">
              {ich.requiresClinicalTrial ? (
                <ShieldAlert className="w-6 h-6 text-rose-500 shrink-0 mt-0.5" />
              ) : (
                <CheckCircle className="w-6 h-6 text-emerald-500 shrink-0 mt-0.5" />
              )}
              <div className="text-xs leading-relaxed">
                <p className="font-semibold text-slate-100 print:text-black mb-1">
                  Reversible Inhibition Ratio (R₁) = {ich.r1Value} (Regulatory Threshold: 1.02)
                </p>
                <p className="text-slate-300 print:text-slate-700">{ich.statutoryGuideline}</p>
              </div>
            </div>
          </div>

          {/* ADMET & Physicochemical Profile */}
          <div>
            <h3 className="text-xs font-bold uppercase tracking-wider text-slate-300 print:text-black font-mono border-b border-slate-800 pb-1 mb-3">
              Section 1: Physicochemical & Structural Specification
            </h3>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
              <div className="p-2.5 rounded bg-slate-900 print:bg-slate-100 border border-slate-800 print:border-slate-300">
                <span className="text-[10px] text-slate-400 font-mono block">Molecular Formula</span>
                <span className="font-mono font-bold text-white print:text-black">{lead.formula}</span>
              </div>
              <div className="p-2.5 rounded bg-slate-900 print:bg-slate-100 border border-slate-800 print:border-slate-300">
                <span className="text-[10px] text-slate-400 font-mono block">Molecular Weight</span>
                <span className="font-mono font-bold text-white print:text-black">{lead.molecularWeight} Da</span>
              </div>
              <div className="p-2.5 rounded bg-slate-900 print:bg-slate-100 border border-slate-800 print:border-slate-300">
                <span className="text-[10px] text-slate-400 font-mono block">Lipophilicity (cLogP)</span>
                <span className="font-mono font-bold text-white print:text-black">{lead.logP}</span>
              </div>
              <div className="p-2.5 rounded bg-slate-900 print:bg-slate-100 border border-slate-800 print:border-slate-300">
                <span className="text-[10px] text-slate-400 font-mono block">Polar Area (TPSA)</span>
                <span className="font-mono font-bold text-white print:text-black">{lead.tpsa} Å²</span>
              </div>
            </div>
            <div className="mt-2 text-[11px] font-mono text-slate-400 print:text-slate-700 bg-slate-900/60 print:bg-slate-100 p-2 rounded">
              SMILES: {lead.canonicalSmiles}
            </div>
          </div>

          {/* Preclinical CiPA & DILI Liabilities */}
          <div>
            <h3 className="text-xs font-bold uppercase tracking-wider text-slate-300 print:text-black font-mono border-b border-slate-800 pb-1 mb-3">
              Section 2: In Vitro Cardiac & Hepatic Liabilities
            </h3>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
              <div className="p-3 rounded bg-slate-900 print:bg-slate-100 border border-slate-800 print:border-slate-300">
                <span className="font-bold text-slate-200 print:text-black block mb-1">CiPA Cardiotoxicity Panel</span>
                <p className="text-slate-400 print:text-slate-700">
                  hERG IC50: <strong className="text-white print:text-black">{lead.cipaProfile.hergIc50} µM</strong> · Arrhythmia Risk: <strong className="text-white print:text-black">{lead.cipaProfile.netArrhythmiaRisk}</strong>
                </p>
                <p className="text-[11px] text-slate-400 mt-1">{lead.cipaProfile.qtProlongationLikelihood}</p>
              </div>

              <div className="p-3 rounded bg-slate-900 print:bg-slate-100 border border-slate-800 print:border-slate-300">
                <span className="font-bold text-slate-200 print:text-black block mb-1">DILI & Mechanistic Toxicology</span>
                <p className="text-slate-400 print:text-slate-700">
                  BSEP Canalicular Inhibition:{' '}
                  <strong className="text-white print:text-black">
                    {lead.diliProfile.bsepInhibition ? 'Positive (Cholestasis)' : 'Negative'}
                  </strong>
                </p>
                <p className="text-[11px] text-slate-400 mt-1">
                  Overall DILI Concern Score: {lead.diliProfile.diliConcernScore} · Ames Mutagenicity: {lead.ichM7AmesMutagenicity}
                </p>
              </div>
            </div>
          </div>

          {/* CYP Interferences */}
          <div>
            <h3 className="text-xs font-bold uppercase tracking-wider text-slate-300 print:text-black font-mono border-b border-slate-800 pb-1 mb-3">
              Section 3: Cytochrome P450 Metabolic Interferences
            </h3>
            <div className="space-y-2 text-xs">
              {data.cypConflicts.map((c, i) => (
                <div key={i} className="p-2.5 rounded bg-slate-900 print:bg-slate-100 border border-slate-800 print:border-slate-300">
                  <div className="flex justify-between font-mono mb-1">
                    <strong className="text-cyan-300 print:text-cyan-800">
                      {c.enzyme} ({c.mechanism})
                    </strong>
                    <span className="font-bold text-rose-400 print:text-rose-700">{c.severity}</span>
                  </div>
                  <p className="text-slate-300 print:text-slate-700 text-[11px]">{c.description}</p>
                </div>
              ))}
            </div>
          </div>

          {/* Synergy & Double Hit Adverse Events */}
          <div>
            <h3 className="text-xs font-bold uppercase tracking-wider text-slate-300 print:text-black font-mono border-b border-slate-800 pb-1 mb-3">
              Section 4: Co-Administration Adverse Reaction Signals (openFDA FAERS)
            </h3>
            <div className="space-y-1.5 text-xs">
              {data.synergySignals.slice(0, 4).map((s, i) => (
                <div key={i} className="flex justify-between p-2 rounded bg-slate-900/60 print:bg-slate-100 border border-slate-800 print:border-slate-300">
                  <span className="font-medium text-slate-200 print:text-black">{s.reaction}</span>
                  <span className="font-mono text-purple-300 print:text-purple-800">
                    Co-dosing Count: {s.coAdminCount} (ROR: {s.rorScore}x)
                  </span>
                </div>
              ))}
            </div>
          </div>

          {/* Regulatory Attestation */}
          <div className="pt-4 border-t border-slate-800 print:border-slate-400 text-[10px] text-slate-400 print:text-slate-600 font-mono flex justify-between items-center">
            <span>FDA 21 CFR § 312.23 (Preclinical Safety IND Compliance)</span>
            <span>Data Sources: PubChem · ChEMBL · openFDA FAERS</span>
          </div>
        </div>
      </div>
    </div>
  );
};
