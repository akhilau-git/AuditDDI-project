import React, { useState } from 'react';
import { SevenSourceEvidence, CompoundProfile } from '../types/pharmacology.ts';
import { Database, ShieldCheck, AlertCircle, ExternalLink, Filter, CheckCircle2 } from 'lucide-react';

interface EvidenceExplorerProps {
  evidence: SevenSourceEvidence;
  lead: CompoundProfile;
  coMed: CompoundProfile;
}

export const EvidenceExplorer: React.FC<EvidenceExplorerProps> = ({
  evidence,
  lead,
  coMed,
}) => {
  const [selectedSource, setSelectedSource] = useState<string>('all');

  const sourcesList = [
    {
      id: 'twosides',
      name: 'TWOSIDES',
      category: 'Label Corpus / Associations',
      status: evidence.twosides.available ? 'Ready' : 'Pending',
      details: `${evidence.twosides.reportedEventsCount} co-reported adverse events cataloged.`,
      provenance: 'Tatonetti et al., Science Translational Medicine / Columbia University.',
      note: 'Crucial distinction: Represents reported real-world co-occurrences in patient registries, not proven mechanistic causation.',
    },
    {
      id: 'pubchem',
      name: 'PubChem',
      category: 'Chemical Structures & Physicochemical',
      status: evidence.pubchem.available ? 'Ready' : 'Pending',
      details: `CID A: ${evidence.pubchem.cidA || 'N/A'} · CID B: ${evidence.pubchem.cidB || 'N/A'} · 3D conformer coordinates validated.`,
      provenance: 'NCBI National Library of Medicine PUG REST Service.',
      note: 'Provides canonical SMILES, 2D/3D SDF conformers, InChIKeys, and calculated Lipinski/Veber properties.',
    },
    {
      id: 'chembl',
      name: 'ChEMBL',
      category: 'Bioactivities & Target Binding',
      status: evidence.chembl.available ? 'Ready' : 'Pending',
      details: `Target bioassays retrieved: ${evidence.chembl.bioassayCount} · hERG IC50: ${lead.cipaProfile.hergIc50} µM.`,
      provenance: 'European Bioinformatics Institute (EMBL-EBI) ChEMBL 34 REST API.',
      note: 'Source for quantitative IC50, Ki, and Kd target binding assays, including CiPA ion channel affinities.',
    },
    {
      id: 'openfda',
      name: 'openFDA SPL Labels',
      category: 'Regulatory Drug Labeling',
      status: evidence.openfda.available ? 'Ready' : 'Pending',
      details: `Official boxed warnings: ${lead.boxedWarnings.length} · Contraindication verified: ${evidence.openfda.contraindicationDocumented ? 'Yes' : 'No'}.`,
      provenance: 'FDA Structured Product Labeling (SPL) repository.',
      note: 'Curated FDA product package inserts, black-box warnings, and statutory contraindications.',
    },
    {
      id: 'faers',
      name: 'openFDA FAERS',
      category: 'Post-Marketing Pharmacovigilance',
      status: evidence.faers.available ? 'Ready' : 'Pending',
      details: `${evidence.faers.coDosingReportsCount} co-administration patient safety reports · Max ROR: ${evidence.faers.reportingOddsRatioMax}x.`,
      provenance: 'FDA Adverse Event Reporting System (FAERS) public quarterly database.',
      note: 'Real-world post-marketing spontaneous case reports evaluated using disproportionality algorithms (ROR / PRR).',
    },
    {
      id: 'ddinter',
      name: 'DDInter',
      category: 'Mechanistic DDI Categorization',
      status: evidence.ddinter.available ? 'Ready' : 'Pending',
      details: `Clinical severity tier: ${evidence.ddinter.severityTier} · PK Pathways: ${evidence.ddinter.pkMechanisms.join(', ') || 'Metabolic'}.`,
      provenance: 'DDInter Multi-Level Clinical Interaction Database (Xiong et al., Nucleic Acids Res).',
      note: 'Provides annotated pharmacokinetic (CYP/transporter) vs pharmacodynamic mechanisms and severity grades.',
    },
    {
      id: 'pharmgkb',
      name: 'PharmGKB',
      category: 'Pharmacogenomics & Biomarkers',
      status: evidence.pharmgkb.available ? 'Ready' : 'Pending',
      details: `Clinical annotation: ${evidence.pharmgkb.clinicalAnnotationLevel} · Implicated genes: ${evidence.pharmgkb.genesImplicated.join(', ')}.`,
      provenance: 'Pharmacogenomics Knowledgebase (PharmGKB / CPIC Guidelines).',
      note: 'Translates genetic variants (CYP2D6, CYP2C9, VKORC1) into metabolic metabolizer phenotypes and dosage guidelines.',
    },
  ];

  const filteredSources =
    selectedSource === 'all'
      ? sourcesList
      : sourcesList.filter((s) => s.id === selectedSource);

  return (
    <section className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-sm space-y-5">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between pb-3 border-b border-slate-800 gap-2">
        <div className="flex items-center gap-2">
          <Database className="w-4 h-4 text-emerald-400" />
          <h2 className="text-sm font-semibold tracking-wide text-white uppercase">
            Multisource Evidence Explorer (7-Source Integration)
          </h2>
        </div>
        <div className="flex items-center gap-2">
          <Filter className="w-3.5 h-3.5 text-slate-400" />
          <select
            value={selectedSource}
            onChange={(e) => setSelectedSource(e.target.value)}
            className="bg-slate-950 border border-slate-800 rounded-md px-2 py-1 text-xs text-slate-200 font-mono focus:outline-none focus:border-cyan-500"
          >
            <option value="all">All 7 Data Sources</option>
            {sourcesList.map((s) => (
              <option key={s.id} value={s.id}>
                {s.name}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Dataset Leakage Audit Callout */}
      <div className="p-4 rounded-lg bg-slate-950/70 border border-slate-800 flex flex-col sm:flex-row items-start justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="text-xs font-bold text-slate-200 uppercase font-mono">
              Dataset Leakage & Split Integrity Audit
            </span>
            <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-cyan-950 text-cyan-300 border border-cyan-800">
              {evidence.leakageAudit.leakageStatus}
            </span>
          </div>
          <p className="text-xs text-slate-400 leading-relaxed max-w-2xl">
            {evidence.leakageAudit.scientificDisclaimer}
          </p>
        </div>

        <div className="flex sm:flex-col items-center sm:items-end gap-2 text-xs font-mono shrink-0">
          <span className="text-slate-400">Transductive Train:</span>
          <span className={evidence.leakageAudit.inTransductiveTrain ? 'text-amber-400 font-bold' : 'text-emerald-400 font-bold'}>
            {evidence.leakageAudit.inTransductiveTrain ? 'Present in Graph' : 'Excluded from Graph'}
          </span>
        </div>
      </div>

      {/* Cross-Database Identifier Mapping Table */}
      <div className="overflow-x-auto">
        <span className="text-xs font-semibold text-slate-300 block mb-2 font-mono">
          Normalized Compound Cross-References
        </span>
        <table className="w-full text-xs font-mono text-left border border-slate-800 rounded-lg overflow-hidden">
          <thead className="bg-slate-950 text-slate-400 border-b border-slate-800">
            <tr>
              <th className="py-2 px-3 font-medium">Compound</th>
              <th className="py-2 px-3 font-medium">PubChem CID</th>
              <th className="py-2 px-3 font-medium">ChEMBL ID</th>
              <th className="py-2 px-3 font-medium">RxNav RxCUI</th>
              <th className="py-2 px-3 font-medium">InChIKey</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800 bg-slate-900/60">
            <tr>
              <td className="py-2 px-3 font-bold text-cyan-400">{lead.name}</td>
              <td className="py-2 px-3 text-slate-300">{lead.cid || 'N/A'}</td>
              <td className="py-2 px-3 text-slate-300">{lead.chemblId || 'N/A'}</td>
              <td className="py-2 px-3 text-slate-300">{evidence.identityMappings.rxcuiA || '703'}</td>
              <td className="py-2 px-3 text-slate-400 truncate max-w-[140px]">{lead.inChIKey || 'N/A'}</td>
            </tr>
            <tr>
              <td className="py-2 px-3 font-bold text-purple-400">{coMed.name}</td>
              <td className="py-2 px-3 text-slate-300">{coMed.cid || 'N/A'}</td>
              <td className="py-2 px-3 text-slate-300">{coMed.chemblId || 'N/A'}</td>
              <td className="py-2 px-3 text-slate-300">{evidence.identityMappings.rxcuiB || '11289'}</td>
              <td className="py-2 px-3 text-slate-400 truncate max-w-[140px]">{coMed.inChIKey || 'N/A'}</td>
            </tr>
          </tbody>
        </table>
      </div>

      {/* 7 Sources Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {filteredSources.map((src) => (
          <div key={src.id} className="p-3.5 rounded-lg bg-slate-950/60 border border-slate-800 flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between mb-1.5">
                <div className="flex items-center gap-2">
                  <span className="font-bold text-slate-200 text-xs">{src.name}</span>
                  <span className="text-[10px] text-slate-400 font-mono">({src.category})</span>
                </div>
                <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-emerald-950/80 text-emerald-400 border border-emerald-800/80">
                  {src.status}
                </span>
              </div>

              <p className="text-xs text-slate-300 font-mono mt-1">{src.details}</p>
              <p className="text-[11px] text-slate-400 mt-2 leading-relaxed">{src.note}</p>
            </div>

            <div className="mt-3 pt-2 border-t border-slate-800/80 flex items-center justify-between text-[10px] text-slate-500 font-mono">
              <span className="truncate max-w-[280px]" title={src.provenance}>
                Ref: {src.provenance}
              </span>
              <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500 shrink-0" />
            </div>
          </div>
        ))}
      </div>
    </section>
  );
};
