import React, { useState } from 'react';
import { CompoundProfile } from '../types/pharmacology.ts';
import { Molecule3DViewer } from './Molecule3DViewer.tsx';
import { Activity, Copy, Check, ExternalLink, ShieldCheck, ShieldAlert, Box, Image as ImageIcon } from 'lucide-react';

interface Pillar1Props {
  lead: CompoundProfile;
  coMed: CompoundProfile;
}

export const Pillar1ADMET: React.FC<Pillar1Props> = ({ lead, coMed }) => {
  const [copiedSmiles, setCopiedSmiles] = useState(false);
  const [activeView, setActiveView] = useState<'lead' | 'coMed' | 'compare'>('lead');
  const [structureDim, setStructureDim] = useState<'2D' | '3D'>('3D');

  const current = activeView === 'coMed' ? coMed : lead;

  const copySmiles = () => {
    navigator.clipboard.writeText(current.canonicalSmiles);
    setCopiedSmiles(true);
    setTimeout(() => setCopiedSmiles(false), 2000);
  };

  // SVG Radar Chart Math for 6 parameters:
  // Normalized 0 to 1 scales:
  // 1. MW (0-800 Da, cutoff 500)
  // 2. LogP (-1 to 7, cutoff 5)
  // 3. TPSA (0-200 A^2, cutoff 140)
  // 4. HBD (0-8, cutoff 5)
  // 5. HBA (0-15, cutoff 10)
  // 6. RotB (0-15, cutoff 10)
  const norm = (val: number, min: number, max: number) =>
    Math.min(1, Math.max(0, (val - min) / (max - min)));

  const leadNorm = [
    norm(lead.molecularWeight, 100, 800),
    norm(lead.logP, -1, 7),
    norm(lead.tpsa, 10, 200),
    norm(lead.hbd, 0, 8),
    norm(lead.hba, 0, 15),
    norm(lead.rotatableBonds, 0, 15),
  ];

  const coMedNorm = [
    norm(coMed.molecularWeight, 100, 800),
    norm(coMed.logP, -1, 7),
    norm(coMed.tpsa, 10, 200),
    norm(coMed.hbd, 0, 8),
    norm(coMed.hba, 0, 15),
    norm(coMed.rotatableBonds, 0, 15),
  ];

  const labels = ['MW', 'cLogP', 'TPSA', 'HBD', 'HBA', 'RotB'];
  const centerX = 120;
  const centerY = 110;
  const radius = 75;

  const getPolygonPoints = (vals: number[]) => {
    return vals
      .map((v, i) => {
        const angle = (Math.PI * 2 * i) / 6 - Math.PI / 2;
        const r = v * radius;
        const x = centerX + r * Math.cos(angle);
        const y = centerY + r * Math.sin(angle);
        return `${x.toFixed(1)},${y.toFixed(1)}`;
      })
      .join(' ');
  };

  return (
    <section id="admet" className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-sm">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between pb-4 border-b border-slate-800 gap-2">
        <div className="flex items-center gap-2">
          <Activity className="w-4 h-4 text-cyan-400" />
          <h2 className="text-sm font-semibold tracking-wide text-white uppercase">
            ADMET Property Checking & 3D Conformer
          </h2>
        </div>

        <div className="flex items-center gap-1 bg-slate-950 p-1 rounded-lg border border-slate-800">
          <button
            onClick={() => setActiveView('lead')}
            className={`px-2.5 py-1 text-xs rounded font-medium transition-colors ${
              activeView === 'lead' ? 'bg-cyan-950 text-cyan-300 border border-cyan-700/50' : 'text-slate-400 hover:text-white'
            }`}
          >
            {lead.name}
          </button>
          <button
            onClick={() => setActiveView('coMed')}
            className={`px-2.5 py-1 text-xs rounded font-medium transition-colors ${
              activeView === 'coMed' ? 'bg-cyan-950 text-cyan-300 border border-cyan-700/50' : 'text-slate-400 hover:text-white'
            }`}
          >
            {coMed.name}
          </button>
          <button
            onClick={() => setActiveView('compare')}
            className={`px-2.5 py-1 text-xs rounded font-medium transition-colors ${
              activeView === 'compare' ? 'bg-cyan-950 text-cyan-300 border border-cyan-700/50' : 'text-slate-400 hover:text-white'
            }`}
          >
            Radar Overlay
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-5 mt-4">
        {/* Left Column: 2D & 3D Interactive Chemical Structure */}
        <div className="lg:col-span-4 flex flex-col justify-between bg-slate-950/60 rounded-lg border border-slate-800/80 p-4">
          <div>
            <div className="flex items-center justify-between text-xs text-slate-400 mb-2.5">
              <span className="font-semibold text-slate-200">{current.name}</span>

              {/* 2D vs 3D Dimension Switcher */}
              <div className="flex items-center bg-slate-900 p-0.5 rounded-md border border-slate-700">
                <button
                  onClick={() => setStructureDim('2D')}
                  className={`flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-mono transition ${
                    structureDim === '2D'
                      ? 'bg-cyan-950 text-cyan-300 border border-cyan-700 font-bold'
                      : 'text-slate-400 hover:text-white'
                  }`}
                  title="2D Chemical Drawing"
                >
                  <ImageIcon className="w-3 h-3" /> 2D
                </button>
                <button
                  onClick={() => setStructureDim('3D')}
                  className={`flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-mono transition ${
                    structureDim === '3D'
                      ? 'bg-cyan-950 text-cyan-300 border border-cyan-700 font-bold'
                      : 'text-slate-400 hover:text-white'
                  }`}
                  title="Interactive 3D Rotatable Conformer"
                >
                  <Box className="w-3 h-3" /> 3D Rotate
                </button>
              </div>
            </div>

            {/* Structure Viewport (3D or 2D) */}
            {structureDim === '3D' ? (
              <div className="w-full">
                <Molecule3DViewer
                  cid={current.cid}
                  name={current.name}
                  formula={current.formula}
                />
                <div className="flex items-center justify-between text-[10px] text-slate-400 font-mono mt-1.5 px-1">
                  <span>Drag mouse/finger to rotate freely</span>
                  <span>Scroll to zoom</span>
                </div>
              </div>
            ) : (
              <div>
                <div className="relative aspect-square w-full max-w-[240px] mx-auto bg-white rounded-lg p-2 border border-slate-700 flex items-center justify-center overflow-hidden">
                  {current.structureImageUrl ? (
                    <img
                      src={current.structureImageUrl}
                      alt={`2D chemical structure of ${current.name}`}
                      className="max-h-full max-w-full object-contain"
                      referrerPolicy="no-referrer"
                      loading="lazy"
                    />
                  ) : (
                    <div className="text-center p-3 text-slate-700 text-xs font-mono">
                      SMILES Render
                      <br />
                      <span className="text-[10px] break-all">{current.canonicalSmiles.slice(0, 30)}...</span>
                    </div>
                  )}
                </div>
                <div className="mt-2 text-center">
                  <span className="text-xs font-mono text-slate-300 font-semibold">{current.formula}</span>
                </div>
              </div>
            )}
          </div>

          {/* SMILES Drawer & Actions */}
          <div className="mt-3 pt-3 border-t border-slate-800">
            <div className="flex items-center justify-between text-[11px] text-slate-400 mb-1">
              <span>Canonical SMILES</span>
              <button
                onClick={copySmiles}
                className="flex items-center gap-1 text-cyan-400 hover:text-cyan-300"
                title="Copy SMILES to clipboard"
              >
                {copiedSmiles ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
                <span>{copiedSmiles ? 'Copied' : 'Copy'}</span>
              </button>
            </div>
            <p className="text-[10px] font-mono text-slate-400 break-all bg-slate-900 p-2 rounded border border-slate-800 max-h-16 overflow-y-auto">
              {current.canonicalSmiles}
            </p>

            {current.cid ? (
              <a
                href={`https://pubchem.ncbi.nlm.nih.gov/compound/${current.cid}`}
                target="_blank"
                rel="noreferrer"
                className="inline-flex items-center gap-1 text-[11px] text-slate-400 hover:text-slate-200 mt-2"
              >
                View on PubChem <ExternalLink className="w-3 h-3" />
              </a>
            ) : null}
          </div>
        </div>

        {/* Middle Column: Physicochemical Metrics Grid */}
        <div className="lg:col-span-4 flex flex-col justify-between space-y-3">
          <div className="grid grid-cols-2 gap-2.5">
            <div className="bg-slate-950/60 p-3 rounded-lg border border-slate-800/80">
              <span className="text-[11px] text-slate-400">Lipophilicity (cLogP)</span>
              <p className="text-lg font-mono font-bold text-white mt-0.5 tabular-nums">{current.logP}</p>
              <span className="text-[10px] text-slate-400 font-mono">Cutoff: ≤ 5.0</span>
            </div>

            <div className="bg-slate-950/60 p-3 rounded-lg border border-slate-800/80">
              <span className="text-[11px] text-slate-400">Polar Area (TPSA)</span>
              <p className="text-lg font-mono font-bold text-white mt-0.5 tabular-nums">{current.tpsa} Å²</p>
              <span className="text-[10px] text-slate-400 font-mono">Cutoff: ≤ 140 Å²</span>
            </div>

            <div className="bg-slate-950/60 p-3 rounded-lg border border-slate-800/80">
              <span className="text-[11px] text-slate-400">Molecular Mass</span>
              <p className="text-lg font-mono font-bold text-white mt-0.5 tabular-nums">{current.molecularWeight} Da</p>
              <span className="text-[10px] text-slate-400 font-mono">Cutoff: ≤ 500 Da</span>
            </div>

            <div className="bg-slate-950/60 p-3 rounded-lg border border-slate-800/80">
              <span className="text-[11px] text-slate-400">H-Bond Donors / Acc</span>
              <p className="text-lg font-mono font-bold text-white mt-0.5 tabular-nums">
                {current.hbd} / {current.hba}
              </p>
              <span className="text-[10px] text-slate-400 font-mono">Cutoffs: ≤ 5 / ≤ 10</span>
            </div>

            <div className="bg-slate-950/60 p-3 rounded-lg border border-slate-800/80">
              <span className="text-[11px] text-slate-400">Rotatable Bonds</span>
              <p className="text-lg font-mono font-bold text-white mt-0.5 tabular-nums">{current.rotatableBonds}</p>
              <span className="text-[10px] text-slate-400 font-mono">Veber Cutoff: ≤ 10</span>
            </div>

            <div className="bg-slate-950/60 p-3 rounded-lg border border-slate-800/80">
              <span className="text-[11px] text-slate-400">Drug-likeness (QED)</span>
              <p className="text-lg font-mono font-bold text-white mt-0.5 tabular-nums">{current.qedScore}</p>
              <span className="text-[10px] text-slate-400 font-mono">Bickerton et al. [0-1]</span>
            </div>
          </div>

          {/* Rule of 5 Concordance Box */}
          <div className="p-3 rounded-lg bg-slate-950/70 border border-slate-800 text-xs">
            <div className="flex items-center justify-between">
              <span className="text-slate-400">Lipinski Concordance</span>
              {current.ro5Violations === 0 ? (
                <span className="text-emerald-400 font-semibold flex items-center gap-1">
                  <ShieldCheck className="w-3.5 h-3.5" /> 0 Violations (Lead-like)
                </span>
              ) : (
                <span className="text-amber-400 font-semibold flex items-center gap-1">
                  <ShieldAlert className="w-3.5 h-3.5" /> {current.ro5Violations} Violation(s)
                </span>
              )}
            </div>
            <p className="text-[11px] text-slate-400 mt-1">
              Veber oral bioavailability criteria:{' '}
              <strong className="text-slate-300">
                {current.veberViolations === 0 ? 'Compliant' : `${current.veberViolations} Violation`}
              </strong>
            </p>
          </div>
        </div>

        {/* Right Column: Comparative Radar Spider Chart */}
        <div className="lg:col-span-4 bg-slate-950/60 rounded-lg border border-slate-800/80 p-4 flex flex-col items-center justify-between">
          <div className="w-full flex items-center justify-between text-xs text-slate-400 mb-1">
            <span className="font-medium text-slate-300">Physicochemical Space</span>
            <div className="flex items-center gap-3 text-[10px]">
              <span className="flex items-center gap-1 text-cyan-400">
                <span className="w-2 h-2 rounded-full bg-cyan-400" /> {lead.name}
              </span>
              <span className="flex items-center gap-1 text-purple-400">
                <span className="w-2 h-2 rounded-full bg-purple-400" /> {coMed.name}
              </span>
            </div>
          </div>

          <svg viewBox="0 0 240 220" className="w-full max-w-[240px] overflow-visible my-1">
            {/* Concentric reference rings */}
            {[0.25, 0.5, 0.75, 1.0].map((ring, idx) => (
              <polygon
                key={idx}
                points={getPolygonPoints([ring, ring, ring, ring, ring, ring])}
                fill="none"
                stroke="#334155"
                strokeWidth={ring === 1.0 ? '1.5' : '0.8'}
                strokeDasharray={ring === 1.0 ? 'none' : '2,2'}
              />
            ))}

            {/* Axis spokes */}
            {[0, 1, 2, 3, 4, 5].map((i) => {
              const angle = (Math.PI * 2 * i) / 6 - Math.PI / 2;
              const x2 = centerX + radius * Math.cos(angle);
              const y2 = centerY + radius * Math.sin(angle);
              return <line key={i} x1={centerX} y1={centerY} x2={x2} y2={y2} stroke="#334155" strokeWidth="0.8" />;
            })}

            {/* CoMed Radar Polygon */}
            {(activeView === 'coMed' || activeView === 'compare') && (
              <polygon
                points={getPolygonPoints(coMedNorm)}
                fill="rgba(168, 85, 247, 0.25)"
                stroke="#a855f7"
                strokeWidth="1.8"
              />
            )}

            {/* Lead Radar Polygon */}
            {(activeView === 'lead' || activeView === 'compare') && (
              <polygon
                points={getPolygonPoints(leadNorm)}
                fill="rgba(6, 182, 212, 0.3)"
                stroke="#06b6d4"
                strokeWidth="2"
              />
            )}

            {/* Axis Labels */}
            {labels.map((lbl, i) => {
              const angle = (Math.PI * 2 * i) / 6 - Math.PI / 2;
              const textR = radius + 16;
              const x = centerX + textR * Math.cos(angle);
              const y = centerY + textR * Math.sin(angle) + 4;
              return (
                <text
                  key={lbl}
                  x={x}
                  y={y}
                  textAnchor="middle"
                  fill="#94a3b8"
                  fontSize="10"
                  fontFamily="monospace"
                >
                  {lbl}
                </text>
              );
            })}
          </svg>

          <p className="text-[10px] text-slate-400 text-center font-mono mt-1">
            Outer boundary = Maximum recommended drug-like threshold.
          </p>
        </div>
      </div>
    </section>
  );
};
