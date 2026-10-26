import React, { useEffect, useRef, useState } from 'react';
import * as $3Dmol from '3dmol';
import { RotateCw, RefreshCw, Eye, Box, Play, Pause, AlertCircle } from 'lucide-react';

interface Molecule3DViewerProps {
  cid?: number;
  name: string;
  formula?: string;
  onClose?: () => void;
}

export const Molecule3DViewer: React.FC<Molecule3DViewerProps> = ({
  cid,
  name,
  formula,
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const viewerRef = useRef<any>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [styleMode, setStyleMode] = useState<'stick' | 'sphere' | 'ballAndStick'>('ballAndStick');
  const [isSpinning, setIsSpinning] = useState<boolean>(false);

  useEffect(() => {
    let isCancelled = false;

    async function load3DStructure() {
      if (!containerRef.current) return;
      setLoading(true);
      setError(null);

      try {
        // Fetch 3D conformer SDF from PubChem PUG REST
        let sdfUrl = '';
        if (cid && cid > 0) {
          sdfUrl = `https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/cid/${cid}/SDF?record_type=3d`;
        } else {
          sdfUrl = `https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/${encodeURIComponent(name)}/SDF?record_type=3d`;
        }

        const res = await fetch(sdfUrl);
        if (!res.ok) {
          throw new Error(`PubChem 3D conformer not found for ${name}`);
        }
        const sdfText = await res.text();
        if (isCancelled || !containerRef.current) return;

        // Initialize 3Dmol viewer
        // Clean previous viewer
        containerRef.current.innerHTML = '';
        const viewer = $3Dmol.createViewer(containerRef.current, {
          backgroundColor: '#020617', // Slate 950 deep contrast
        });
        viewerRef.current = viewer;

        viewer.clear();
        viewer.addModel(sdfText, 'sdf');

        // Apply visual representation
        applyStyle(viewer, styleMode);

        viewer.zoomTo();
        viewer.render();
        setLoading(false);
      } catch (err) {
        console.warn('3D model load failed:', err);
        if (!isCancelled) {
          setError('3D Conformer coordinates currently unavailable for this compound.');
          setLoading(false);
        }
      }
    }

    load3DStructure();

    return () => {
      isCancelled = true;
      if (viewerRef.current) {
        try {
          viewerRef.current.stopAnimate();
        } catch {
          // ignore
        }
      }
    };
  }, [cid, name]);

  const applyStyle = (viewer: any, mode: 'stick' | 'sphere' | 'ballAndStick') => {
    if (!viewer) return;
    viewer.setStyle({}, {}); // clear

    if (mode === 'ballAndStick') {
      viewer.setStyle(
        {},
        {
          stick: { radius: 0.16, colorscheme: 'Jmol' },
          sphere: { scale: 0.28, colorscheme: 'Jmol' },
        }
      );
    } else if (mode === 'sphere') {
      viewer.setStyle({}, { sphere: { scale: 0.75, colorscheme: 'Jmol' } });
    } else if (mode === 'stick') {
      viewer.setStyle({}, { stick: { radius: 0.22, colorscheme: 'Jmol' } });
    }
    viewer.render();
  };

  const handleStyleChange = (mode: 'stick' | 'sphere' | 'ballAndStick') => {
    setStyleMode(mode);
    if (viewerRef.current) {
      applyStyle(viewerRef.current, mode);
    }
  };

  const handleToggleSpin = () => {
    if (!viewerRef.current) return;
    if (isSpinning) {
      viewerRef.current.stopAnimate();
      setIsSpinning(false);
    } else {
      viewerRef.current.spin('y', 1.0);
      setIsSpinning(true);
    }
  };

  const handleResetCamera = () => {
    if (!viewerRef.current) return;
    viewerRef.current.zoomTo();
    viewerRef.current.render();
  };

  return (
    <div className="relative w-full h-[280px] bg-slate-950 rounded-lg border border-slate-800 overflow-hidden flex flex-col">
      {/* 3D Canvas Viewport */}
      <div
        ref={containerRef}
        className="relative w-full flex-1 cursor-grab active:cursor-grabbing"
        title="Click and drag to rotate in 3D · Scroll to zoom · Shift+drag to pan"
      />

      {/* Loading Overlay */}
      {loading && (
        <div className="absolute inset-0 bg-slate-950/80 backdrop-blur-xs flex flex-col items-center justify-center gap-2 text-xs text-slate-300 font-mono">
          <RefreshCw className="w-5 h-5 text-cyan-400 animate-spin" />
          <span>Fetching 3D Conformer Coordinates...</span>
        </div>
      )}

      {/* Error Fallback */}
      {error && !loading && (
        <div className="absolute inset-0 bg-slate-950/90 flex flex-col items-center justify-center p-4 text-center">
          <AlertCircle className="w-6 h-6 text-amber-400 mb-2" />
          <span className="text-xs text-slate-300 font-mono mb-1">{error}</span>
          <span className="text-[10px] text-slate-500">Switch back to 2D structure depiction above.</span>
        </div>
      )}

      {/* Bottom Floating Control Bar */}
      <div className="bg-slate-900/90 backdrop-blur-sm border-t border-slate-800 px-3 py-1.5 flex flex-wrap items-center justify-between gap-2 text-[11px] font-mono z-10">
        <div className="flex items-center gap-2 text-slate-300">
          <span className="font-semibold text-cyan-400">{name}</span>
          {formula && <span className="text-slate-400">({formula})</span>}
        </div>

        <div className="flex items-center gap-1.5">
          {/* Style Selector Buttons */}
          <div className="flex items-center bg-slate-950 p-0.5 rounded border border-slate-800">
            <button
              onClick={() => handleStyleChange('ballAndStick')}
              className={`px-1.5 py-0.5 rounded text-[10px] transition ${
                styleMode === 'ballAndStick' ? 'bg-cyan-950 text-cyan-300 font-bold' : 'text-slate-400 hover:text-white'
              }`}
              title="Ball & Stick Mode"
            >
              Ball/Stick
            </button>
            <button
              onClick={() => handleStyleChange('sphere')}
              className={`px-1.5 py-0.5 rounded text-[10px] transition ${
                styleMode === 'sphere' ? 'bg-cyan-950 text-cyan-300 font-bold' : 'text-slate-400 hover:text-white'
              }`}
              title="Space-filling CPK Sphere Mode"
            >
              CPK
            </button>
            <button
              onClick={() => handleStyleChange('stick')}
              className={`px-1.5 py-0.5 rounded text-[10px] transition ${
                styleMode === 'stick' ? 'bg-cyan-950 text-cyan-300 font-bold' : 'text-slate-400 hover:text-white'
              }`}
              title="Wireframe Stick Mode"
            >
              Stick
            </button>
          </div>

          {/* Spin Button */}
          <button
            onClick={handleToggleSpin}
            className={`p-1 rounded border transition ${
              isSpinning
                ? 'bg-cyan-950 text-cyan-300 border-cyan-700'
                : 'bg-slate-950 text-slate-400 border-slate-800 hover:text-white'
            }`}
            title={isSpinning ? 'Pause auto-rotation' : 'Start 3D auto-spin'}
          >
            {isSpinning ? <Pause className="w-3.5 h-3.5" /> : <Play className="w-3.5 h-3.5" />}
          </button>

          {/* Reset Camera */}
          <button
            onClick={handleResetCamera}
            className="p-1 rounded bg-slate-950 text-slate-400 border border-slate-800 hover:text-white transition"
            title="Reset 3D camera orientation"
          >
            <RotateCw className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>
    </div>
  );
};
