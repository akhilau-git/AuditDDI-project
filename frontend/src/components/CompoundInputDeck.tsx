import React, { useState, useEffect } from 'react';
import { Search, RefreshCw, Sparkles, ChevronDown, ChevronUp, FileCode, Beaker } from 'lucide-react';

interface CompoundInputDeckProps {
  onAnalyze: (lead: string, coMed: string, isSmiles?: boolean) => void;
  loading: boolean;
  activeLeadName: string;
  activeCoMedName: string;
  activeLeadSmiles?: string;
  activeCoMedSmiles?: string;
}

const PRESET_PAIRS = [
  {
    lead: 'Amiodarone',
    coMed: 'Warfarin',
    label: 'Amiodarone + Warfarin',
    smilesA: 'CCCCCCC(=O)C1=CC(=C(C=C1)OCCN(CC)CC)I',
    smilesB: 'CC(=O)CC(C1=CC=CC=C1)C2=C(C3=CC=CC=C3OC2=O)O',
  },
  {
    lead: 'Simvastatin',
    coMed: 'Clarithromycin',
    label: 'Simvastatin + Clarithromycin',
    smilesA: 'CCC(C)(C)C(=O)OC1CC(C=C2C1C(C(C=C2)C)CCC3CC(CC(=O)O3)O)C',
    smilesB: 'CCC1C(C(C(C(=O)C(CC(C(C(C(C(=O)O1)C)OC2CC(C(C(O2)C)O)(C)OC)C)OC3C(C(CC(O3)C)N(C)C)O)(C)O)C)C)O)(C)OC',
  },
  {
    lead: 'Paclitaxel',
    coMed: 'Ketoconazole',
    label: 'Paclitaxel + Ketoconazole',
    smilesA: 'CC1=C2C(C(=O)C3(C(CC4C(C3C(C(C2(C)C)(CC1OC(=O)C(C(C5=CC=CC=C5)NC(=O)C6=CC=CC=C6)O)O)OC(=O)C7=CC=CC=C7)(CO4)OC(=O)C)O)C)OC(=O)C',
    smilesB: 'CC(=O)N1CCN(CC1)C2=CC=C(C=C2)OCC3COC(O3)(CN4C=CN=C4)C5=C(C=C(C=C5)Cl)Cl',
  },
  {
    lead: 'Terfenadine',
    coMed: 'Ketoconazole',
    label: 'Terfenadine + Ketoconazole',
    smilesA: 'CC(C)(C)C1=CC=C(C=C1)C(O)CCCN2CCC(CC2)C(C3=CC=CC=C3)(C4=CC=CC=C4)O',
    smilesB: 'CC(=O)N1CCN(CC1)C2=CC=C(C=C2)OCC3COC(O3)(CN4C=CN=C4)C5=C(C=C(C=C5)Cl)Cl',
  },
];

export const CompoundInputDeck: React.FC<CompoundInputDeckProps> = ({
  onAnalyze,
  loading,
  activeLeadName,
  activeCoMedName,
  activeLeadSmiles,
  activeCoMedSmiles,
}) => {
  const [inputMode, setInputMode] = useState<'name' | 'smiles'>('name');
  const [isExpanded, setIsExpanded] = useState<boolean>(true);

  // Name Mode Inputs
  const [leadName, setLeadName] = useState(activeLeadName);
  const [coMedName, setCoMedName] = useState(activeCoMedName);

  // SMILES Mode Inputs
  const [leadSmiles, setLeadSmiles] = useState(
    activeLeadSmiles || 'CCCCCCC(=O)C1=CC(=C(C=C1)OCCN(CC)CC)I'
  );
  const [coMedSmiles, setCoMedSmiles] = useState(
    activeCoMedSmiles || 'CC(=O)CC(C1=CC=CC=C1)C2=C(C3=CC=CC=C3OC2=O)O'
  );

  const [leadSuggestions, setLeadSuggestions] = useState<string[]>([]);
  const [coMedSuggestions, setCoMedSuggestions] = useState<string[]>([]);

  // Autocomplete fetch for Drug A
  useEffect(() => {
    if (inputMode !== 'name' || leadName.length < 2) {
      setLeadSuggestions([]);
      return;
    }
    const timer = setTimeout(async () => {
      try {
        const res = await fetch(`/api/suggest?q=${encodeURIComponent(leadName)}`);
        if (res.ok) {
          const json = await res.json();
          setLeadSuggestions((json.suggestions || []).slice(0, 5));
        }
      } catch {
        // quiet
      }
    }, 250);
    return () => clearTimeout(timer);
  }, [leadName, inputMode]);

  // Autocomplete fetch for Drug B
  useEffect(() => {
    if (inputMode !== 'name' || coMedName.length < 2) {
      setCoMedSuggestions([]);
      return;
    }
    const timer = setTimeout(async () => {
      try {
        const res = await fetch(`/api/suggest?q=${encodeURIComponent(coMedName)}`);
        if (res.ok) {
          const json = await res.json();
          setCoMedSuggestions((json.suggestions || []).slice(0, 5));
        }
      } catch {
        // quiet
      }
    }, 250);
    return () => clearTimeout(timer);
  }, [coMedName, inputMode]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (inputMode === 'name') {
      if (!leadName.trim() || !coMedName.trim()) return;
      onAnalyze(leadName.trim(), coMedName.trim(), false);
    } else {
      if (!leadSmiles.trim() || !coMedSmiles.trim()) return;
      onAnalyze(leadSmiles.trim(), coMedSmiles.trim(), true);
    }
  };

  const handleSelectPreset = (p: typeof PRESET_PAIRS[0]) => {
    setLeadName(p.lead);
    setCoMedName(p.coMed);
    setLeadSmiles(p.smilesA);
    setCoMedSmiles(p.smilesB);
    setLeadSuggestions([]);
    setCoMedSuggestions([]);
    if (inputMode === 'name') {
      onAnalyze(p.lead, p.coMed, false);
    } else {
      onAnalyze(p.smilesA, p.smilesB, true);
    }
  };

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 shadow-sm mb-6 transition-all">
      {/* Top Bar of Input Deck */}
      <div className="flex flex-wrap items-center justify-between gap-3 pb-2 border-b border-slate-800/80">
        <div className="flex items-center gap-3">
          <div className="flex items-center bg-slate-950 p-0.5 rounded-lg border border-slate-800 text-xs font-mono">
            <button
              onClick={() => setInputMode('name')}
              className={`flex items-center gap-1.5 px-3 py-1 rounded transition ${
                inputMode === 'name'
                  ? 'bg-cyan-950 text-cyan-300 font-semibold border border-cyan-800'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              <Beaker className="w-3.5 h-3.5" />
              <span>Drug Name / Generic</span>
            </button>
            <button
              onClick={() => setInputMode('smiles')}
              className={`flex items-center gap-1.5 px-3 py-1 rounded transition ${
                inputMode === 'smiles'
                  ? 'bg-cyan-950 text-cyan-300 font-semibold border border-cyan-800'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              <FileCode className="w-3.5 h-3.5" />
              <span>SMILES Structure Format</span>
            </button>
          </div>

          <span className="text-[11px] font-mono text-slate-400 hidden sm:inline">
            Active: <strong className="text-cyan-400">{activeLeadName}</strong> +{' '}
            <strong className="text-purple-400">{activeCoMedName}</strong>
          </span>
        </div>

        <button
          onClick={() => setIsExpanded(!isExpanded)}
          className="flex items-center gap-1 text-xs text-slate-400 hover:text-white font-mono"
        >
          <span>{isExpanded ? 'Hide Inputs' : 'Modify Compounds'}</span>
          {isExpanded ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
        </button>
      </div>

      {isExpanded && (
        <div className="pt-3 space-y-3">
          {/* Preset Buttons */}
          <div className="flex flex-wrap items-center gap-1.5">
            <span className="text-[11px] font-mono text-slate-400 flex items-center gap-1 mr-1">
              <Sparkles className="w-3 h-3 text-cyan-400" /> Presets:
            </span>
            {PRESET_PAIRS.map((p, idx) => (
              <button
                key={idx}
                onClick={() => handleSelectPreset(p)}
                className="px-2 py-0.5 rounded text-[11px] font-mono bg-slate-950 hover:bg-slate-800 text-slate-300 border border-slate-800 hover:border-slate-700 transition"
              >
                {p.label}
              </button>
            ))}
          </div>

          <form onSubmit={handleSubmit} className="space-y-3">
            {inputMode === 'name' ? (
              /* Drug Name Mode */
              <div className="grid grid-cols-1 sm:grid-cols-12 gap-3 items-end">
                <div className="sm:col-span-5 relative">
                  <label className="text-[11px] font-mono uppercase text-slate-400 block mb-1">
                    Compound A / Candidate NCE (Generic Name)
                  </label>
                  <input
                    type="text"
                    value={leadName}
                    onChange={(e) => setLeadName(e.target.value)}
                    placeholder="e.g. Amiodarone, Simvastatin..."
                    className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-xs font-mono text-white placeholder-slate-500 focus:outline-none focus:border-cyan-500"
                  />
                  {leadSuggestions.length > 0 && (
                    <div className="absolute top-full left-0 right-0 mt-1 bg-slate-900 border border-slate-700 rounded-lg shadow-xl z-30 overflow-hidden text-xs font-mono">
                      {leadSuggestions.map((sug, i) => (
                        <button
                          key={i}
                          type="button"
                          onClick={() => {
                            setLeadName(sug);
                            setLeadSuggestions([]);
                          }}
                          className="w-full text-left px-3 py-1.5 hover:bg-slate-800 text-slate-200 transition"
                        >
                          {sug}
                        </button>
                      ))}
                    </div>
                  )}
                </div>

                <div className="sm:col-span-5 relative">
                  <label className="text-[11px] font-mono uppercase text-slate-400 block mb-1">
                    Compound B / Standard of Care (Generic Name)
                  </label>
                  <input
                    type="text"
                    value={coMedName}
                    onChange={(e) => setCoMedName(e.target.value)}
                    placeholder="e.g. Warfarin, Clarithromycin..."
                    className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-xs font-mono text-white placeholder-slate-500 focus:outline-none focus:border-cyan-500"
                  />
                  {coMedSuggestions.length > 0 && (
                    <div className="absolute top-full left-0 right-0 mt-1 bg-slate-900 border border-slate-700 rounded-lg shadow-xl z-30 overflow-hidden text-xs font-mono">
                      {coMedSuggestions.map((sug, i) => (
                        <button
                          key={i}
                          type="button"
                          onClick={() => {
                            setCoMedName(sug);
                            setCoMedSuggestions([]);
                          }}
                          className="w-full text-left px-3 py-1.5 hover:bg-slate-800 text-slate-200 transition"
                        >
                          {sug}
                        </button>
                      ))}
                    </div>
                  )}
                </div>

                <div className="sm:col-span-2">
                  <button
                    type="submit"
                    disabled={loading}
                    className="w-full py-2 px-3 bg-cyan-600 hover:bg-cyan-500 disabled:opacity-50 text-white text-xs font-semibold uppercase tracking-wider rounded-lg transition flex items-center justify-center gap-1.5 shadow-sm"
                  >
                    {loading ? (
                      <>
                        <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                        <span>Predicting...</span>
                      </>
                    ) : (
                      <>
                        <Search className="w-3.5 h-3.5" />
                        <span>Run Audit</span>
                      </>
                    )}
                  </button>
                </div>
              </div>
            ) : (
              /* SMILES Input Mode */
              <div className="space-y-3">
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  <div>
                    <label className="text-[11px] font-mono uppercase text-slate-400 block mb-1 flex items-center justify-between">
                      <span>Compound A SMILES String</span>
                      <span className="text-[10px] text-cyan-400">Canonical Chemical Format</span>
                    </label>
                    <textarea
                      rows={2}
                      value={leadSmiles}
                      onChange={(e) => setLeadSmiles(e.target.value)}
                      placeholder="e.g. CCCCCCC(=O)C1=CC(=C(C=C1)OCCN(CC)CC)I"
                      className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-xs font-mono text-cyan-300 placeholder-slate-600 focus:outline-none focus:border-cyan-500 resize-none"
                    />
                  </div>

                  <div>
                    <label className="text-[11px] font-mono uppercase text-slate-400 block mb-1 flex items-center justify-between">
                      <span>Compound B SMILES String</span>
                      <span className="text-[10px] text-purple-400">Canonical Chemical Format</span>
                    </label>
                    <textarea
                      rows={2}
                      value={coMedSmiles}
                      onChange={(e) => setCoMedSmiles(e.target.value)}
                      placeholder="e.g. CC(=O)CC(C1=CC=CC=C1)C2=C(C3=CC=CC=C3OC2=O)O"
                      className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-xs font-mono text-purple-300 placeholder-slate-600 focus:outline-none focus:border-cyan-500 resize-none"
                    />
                  </div>
                </div>

                <div className="flex justify-end">
                  <button
                    type="submit"
                    disabled={loading}
                    className="py-2 px-5 bg-cyan-600 hover:bg-cyan-500 disabled:opacity-50 text-white text-xs font-semibold uppercase tracking-wider rounded-lg transition flex items-center gap-2 shadow-sm font-mono"
                  >
                    {loading ? (
                      <>
                        <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                        <span>Resolving SMILES & Running Prediction...</span>
                      </>
                    ) : (
                      <>
                        <Search className="w-3.5 h-3.5" />
                        <span>Analyze SMILES Pair</span>
                      </>
                    )}
                  </button>
                </div>
              </div>
            )}
          </form>
        </div>
      )}
    </div>
  );
};
