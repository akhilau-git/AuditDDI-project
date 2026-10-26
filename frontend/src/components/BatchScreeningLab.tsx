import React, { useState, useEffect } from 'react';
import { BatchScreeningRow } from '../types/pharmacology.ts';
import { Layers, Download, CheckCircle2, AlertTriangle, ArrowUpDown, Plus } from 'lucide-react';

interface BatchScreeningLabProps {
  onLoadPair: (drugA: string, drugB: string) => void;
}

export const BatchScreeningLab: React.FC<BatchScreeningLabProps> = ({ onLoadPair }) => {
  const [rows, setRows] = useState<BatchScreeningRow[]>([]);
  const [filterClass, setFilterClass] = useState<string>('all');
  const [sortAsc, setSortAsc] = useState<boolean>(false);
  const [newDrugA, setNewDrugA] = useState('');
  const [newDrugB, setNewDrugB] = useState('');

  useEffect(() => {
    async function loadBatch() {
      try {
        const res = await fetch('/api/batch');
        if (res.ok) {
          const json = await res.json();
          setRows(json);
        }
      } catch (err) {
        console.error('Failed to load batch queue', err);
      }
    }
    loadBatch();
  }, []);

  const handleAddPair = (e: React.FormEvent) => {
    e.preventDefault();
    if (!newDrugA || !newDrugB) return;
    const newRow: BatchScreeningRow = {
      id: `SCR-${(rows.length + 1).toString().padStart(3, '0')}`,
      drugA: newDrugA.trim(),
      drugB: newDrugB.trim(),
      smilesA: 'N/A',
      smilesB: 'N/A',
      calibratedDdiProb: 0.65,
      ddiClassification: 'Moderate Interaction',
      primaryToxAlert: 'Metabolic CYP overlap screening',
      ichM12Trigger: true,
      applicabilityDomain: true,
    };
    setRows([newRow, ...rows]);
    setNewDrugA('');
    setNewDrugB('');
  };

  const filteredRows = rows
    .filter((r) => filterClass === 'all' || r.ddiClassification.toLowerCase().includes(filterClass.toLowerCase()))
    .sort((a, b) => (sortAsc ? a.calibratedDdiProb - b.calibratedDdiProb : b.calibratedDdiProb - a.calibratedDdiProb));

  const exportCSV = () => {
    const headers = ['ID,Drug A,Drug B,P(DDI),Classification,Primary Tox Alert,ICH M12 Trigger,In Applicability Domain\n'];
    const lines = filteredRows.map(
      (r) =>
        `"${r.id}","${r.drugA}","${r.drugB}","${r.calibratedDdiProb}","${r.ddiClassification}","${r.primaryToxAlert}","${r.ichM12Trigger}","${r.applicabilityDomain}"`
    );
    const blob = new Blob([headers.join('') + lines.join('\n')], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `auditddi_batch_screening_${Date.now()}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const exportJSON = () => {
    const blob = new Blob([JSON.stringify(filteredRows, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `auditddi_batch_screening_${Date.now()}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <section className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-sm space-y-4">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between pb-3 border-b border-slate-800 gap-2">
        <div className="flex items-center gap-2">
          <Layers className="w-4 h-4 text-purple-400" />
          <h2 className="text-sm font-semibold tracking-wide text-white uppercase">
            Batch Screening & High-Throughput Queue
          </h2>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={exportCSV}
            className="flex items-center gap-1.5 px-3 py-1 bg-slate-950 border border-slate-800 hover:border-slate-700 text-slate-300 text-xs font-mono rounded-lg transition"
          >
            <Download className="w-3 h-3 text-cyan-400" /> Export CSV
          </button>
          <button
            onClick={exportJSON}
            className="flex items-center gap-1.5 px-3 py-1 bg-slate-950 border border-slate-800 hover:border-slate-700 text-slate-300 text-xs font-mono rounded-lg transition"
          >
            <Download className="w-3 h-3 text-purple-400" /> Export JSON
          </button>
        </div>
      </div>

      {/* Quick Add Form & Filter Bar */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-3 items-center">
        <form onSubmit={handleAddPair} className="lg:col-span-8 flex flex-wrap items-center gap-2">
          <input
            type="text"
            placeholder="Candidate Compound A..."
            value={newDrugA}
            onChange={(e) => setNewDrugA(e.target.value)}
            className="bg-slate-950 border border-slate-800 rounded-lg px-2.5 py-1.5 text-xs text-white font-mono placeholder-slate-500 focus:outline-none focus:border-cyan-500 flex-1 min-w-[140px]"
          />
          <input
            type="text"
            placeholder="Candidate Compound B..."
            value={newDrugB}
            onChange={(e) => setNewDrugB(e.target.value)}
            className="bg-slate-950 border border-slate-800 rounded-lg px-2.5 py-1.5 text-xs text-white font-mono placeholder-slate-500 focus:outline-none focus:border-cyan-500 flex-1 min-w-[140px]"
          />
          <button
            type="submit"
            className="px-3 py-1.5 bg-cyan-600 hover:bg-cyan-500 text-white rounded-lg text-xs font-mono flex items-center gap-1 font-semibold transition shrink-0"
          >
            <Plus className="w-3.5 h-3.5" /> Queue Pair
          </button>
        </form>

        <div className="lg:col-span-4 flex items-center justify-end gap-2 text-xs font-mono">
          <span className="text-slate-400">Filter:</span>
          <select
            value={filterClass}
            onChange={(e) => setFilterClass(e.target.value)}
            className="bg-slate-950 border border-slate-800 rounded-md px-2 py-1 text-xs text-slate-200 focus:outline-none focus:border-cyan-500"
          >
            <option value="all">All Classifications</option>
            <option value="critical">Critical Liability</option>
            <option value="moderate">Moderate Interaction</option>
            <option value="low">Low Risk / Tolerated</option>
          </select>
        </div>
      </div>

      {/* Batch Screening Table */}
      <div className="overflow-x-auto">
        <table className="w-full text-xs font-mono text-left border border-slate-800 rounded-lg overflow-hidden">
          <thead className="bg-slate-950 text-slate-400 border-b border-slate-800">
            <tr>
              <th className="py-2.5 px-3 font-medium">ID</th>
              <th className="py-2.5 px-3 font-medium">Drug Pair (A + B)</th>
              <th
                onClick={() => setSortAsc(!sortAsc)}
                className="py-2.5 px-3 font-medium cursor-pointer hover:text-white select-none"
              >
                <div className="flex items-center gap-1">
                  <span>P(DDI)</span>
                  <ArrowUpDown className="w-3 h-3 text-cyan-400" />
                </div>
              </th>
              <th className="py-2.5 px-3 font-medium">Classification</th>
              <th className="py-2.5 px-3 font-medium">Primary Toxicity Alert</th>
              <th className="py-2.5 px-3 font-medium">ICH M12</th>
              <th className="py-2.5 px-3 font-medium text-right">Action</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800 bg-slate-900/60">
            {filteredRows.map((row) => {
              const isCrit = row.ddiClassification.includes('Critical');
              const isMod = row.ddiClassification.includes('Moderate');

              return (
                <tr key={row.id} className="hover:bg-slate-800/40 transition">
                  <td className="py-2.5 px-3 text-slate-400">{row.id}</td>
                  <td className="py-2.5 px-3 font-bold text-white">
                    <span className="text-cyan-400">{row.drugA}</span> + <span className="text-purple-400">{row.drugB}</span>
                  </td>
                  <td className="py-2.5 px-3 font-bold tabular-nums">
                    <span className={isCrit ? 'text-rose-400' : isMod ? 'text-amber-400' : 'text-emerald-400'}>
                      {(row.calibratedDdiProb * 100).toFixed(0)}%
                    </span>
                  </td>
                  <td className="py-2.5 px-3">
                    <span
                      className={`px-2 py-0.5 rounded text-[10px] font-bold border ${
                        isCrit
                          ? 'bg-rose-950 text-rose-300 border-rose-800'
                          : isMod
                          ? 'bg-amber-950 text-amber-300 border-amber-800'
                          : 'bg-emerald-950 text-emerald-300 border-emerald-800'
                      }`}
                    >
                      {row.ddiClassification}
                    </span>
                  </td>
                  <td className="py-2.5 px-3 text-slate-300 truncate max-w-[260px]" title={row.primaryToxAlert}>
                    {row.primaryToxAlert}
                  </td>
                  <td className="py-2.5 px-3">
                    {row.ichM12Trigger ? (
                      <span className="text-rose-400 flex items-center gap-1 font-semibold">
                        <AlertTriangle className="w-3.5 h-3.5" /> Mandated
                      </span>
                    ) : (
                      <span className="text-emerald-400 flex items-center gap-1">
                        <CheckCircle2 className="w-3.5 h-3.5" /> De-risked
                      </span>
                    )}
                  </td>
                  <td className="py-2.5 px-3 text-right">
                    <button
                      onClick={() => onLoadPair(row.drugA, row.drugB)}
                      className="px-2 py-1 bg-slate-950 hover:bg-slate-800 border border-slate-700 hover:border-cyan-500 text-cyan-300 rounded text-[10px] font-bold transition"
                    >
                      Inspect Pair
                    </button>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </section>
  );
};
