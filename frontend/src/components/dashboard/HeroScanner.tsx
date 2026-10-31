import React, { useEffect, useRef, useState } from 'react';
import {
  GitBranch,
  Play,
  RotateCw,
  Radio,
  Sparkles,
  Check
} from 'lucide-react';
import { DemoRepo } from '../../types';

interface HeroScannerProps {
  repoUrl: string;
  setRepoUrl: (url: string) => void;
  isScanning: boolean;
  scanProgress: number;
  scanStatus: string;
  onTriggerScan: (customUrl?: string) => void;
  demoRepos: DemoRepo[];
}

export const HeroScanner: React.FC<HeroScannerProps> = ({
  repoUrl,
  setRepoUrl,
  isScanning,
  scanProgress,
  scanStatus,
  onTriggerScan,
  demoRepos
}) => {
  const [scannedLine, setScannedLine] = useState<number>(1);
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  // Live Canvas Dynamic Red Particle & Laser Mesh
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;
    let animationFrameId: number;

    const parent = canvas.parentElement;
    let width = (canvas.width = Math.max(parent?.clientWidth || 0, 400));
    let height = (canvas.height = Math.max(parent?.clientHeight || 0, 300));

    const handleResize = () => {
      if (!canvas || !canvas.parentElement) return;
      width = canvas.width = Math.max(canvas.parentElement.clientWidth || 0, 400);
      height = canvas.height = Math.max(canvas.parentElement.clientHeight || 0, 300);
    };
    window.addEventListener('resize', handleResize);

    const particles = Array.from({ length: 36 }, () => ({
      x: Math.random() * width,
      y: Math.random() * height,
      vx: (Math.random() - 0.5) * 0.75,
      vy: (Math.random() - 0.5) * 0.75,
      radius: Math.random() * 2.5 + 1
    }));

    const render = () => {
      ctx.clearRect(0, 0, width, height);

      // Draw particle nodes
      particles.forEach((p, idx) => {
        p.x += p.vx;
        p.y += p.vy;

        if (p.x < 0 || p.x > width) p.vx *= -1;
        if (p.y < 0 || p.y > height) p.vy *= -1;

        ctx.beginPath();
        ctx.arc(p.x, p.y, p.radius, 0, Math.PI * 2);
        ctx.fillStyle = '#FF2E55';
        ctx.shadowColor = '#FF2E55';
        ctx.shadowBlur = 8;
        ctx.fill();

        // Connect nearby nodes with glowing laser links
        for (let j = idx + 1; j < particles.length; j++) {
          const p2 = particles[j];
          const dx = p.x - p2.x;
          const dy = p.y - p2.y;
          const dist = Math.sqrt(dx * dx + dy * dy);

          if (dist < 115) {
            ctx.beginPath();
            ctx.moveTo(p.x, p.y);
            ctx.lineTo(p2.x, p2.y);
            ctx.strokeStyle = `rgba(255, 46, 85, ${0.28 * (1 - dist / 115)})`;
            ctx.lineWidth = 1;
            ctx.stroke();
          }
        }
      });

      animationFrameId = requestAnimationFrame(render);
    };

    render();

    return () => {
      window.removeEventListener('resize', handleResize);
      cancelAnimationFrame(animationFrameId);
    };
  }, []);

  // Live Animated Laser Code Line Scanner Loop
  useEffect(() => {
    const interval = setInterval(() => {
      setScannedLine((prev) => (prev >= 25 ? 1 : prev + 1));
    }, 180);
    return () => clearInterval(interval);
  }, []);

  return (
    <section className="relative overflow-hidden rounded-3xl bg-white border border-red-100 shadow-2xl shadow-red-500/5 p-6 md:p-10 mb-8">
      {/* Live Background Particle Mesh Canvas */}
      <div className="absolute inset-0 pointer-events-none opacity-45">
        <canvas ref={canvasRef} className="w-full h-full" />
      </div>

      <div className="relative z-10 grid grid-cols-1 lg:grid-cols-12 gap-8 items-center">
        {/* Left Column: Heading, Value Prop, and Scanner Input */}
        <div className="lg:col-span-7 space-y-6">
          <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-red-50 border border-red-200 text-[#FF2E55] text-xs font-extrabold shadow-sm">
            <span className="flex h-2 w-2 relative">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-red-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2 w-2 bg-[#FF2E55]"></span>
            </span>
            <span>Explosive Codebase Clean-Up Engine</span>
          </div>

          <h1 className="text-3xl sm:text-5xl font-black tracking-tight text-slate-900 leading-tight">
            Don't Just Delete Code.{' '}
            <span className="bg-gradient-to-r from-[#FF2E55] via-red-600 to-rose-700 bg-clip-text text-transparent">
              Understand Impact & Risk.
            </span>
          </h1>

          <p className="text-slate-600 text-sm sm:text-base font-medium leading-relaxed max-w-xl">
            Unifies findings from <strong className="text-slate-900">Knip</strong>, <strong className="text-slate-900">jscpd</strong>, and <strong className="text-slate-900">Madge</strong> into one responsible workflow: <span className="text-[#FF2E55] font-extrabold">Findings → Evidence → Dependency Context → Verified Action</span>.
          </p>

          {/* Repo Input Box */}
          <div className="p-2 bg-slate-50 rounded-2xl border border-red-200 shadow-lg shadow-red-500/10 flex flex-col sm:flex-row items-center gap-2">
            <div className="flex items-center gap-2 px-3 w-full sm:w-auto flex-1">
              <GitBranch className="w-5 h-5 text-[#FF2E55] shrink-0" />
              <input
                type="text"
                value={repoUrl}
                onChange={(e) => setRepoUrl(e.target.value)}
                placeholder="GitHub Repo URL (e.g. facebook/react)"
                className="w-full bg-transparent text-xs sm:text-sm font-extrabold text-slate-800 placeholder-slate-400 focus:outline-none"
              />
            </div>
            <button
              onClick={() => onTriggerScan()}
              disabled={isScanning}
              className="w-full sm:w-auto px-6 py-3 rounded-xl bg-[#FF2E55] hover:bg-red-600 text-white font-black text-xs uppercase tracking-wider shadow-md shadow-red-500/30 transition-all flex items-center justify-center gap-2 shrink-0 disabled:opacity-50"
            >
              {isScanning ? (
                <>
                  <RotateCw className="w-4 h-4 animate-spin" />
                  <span>Scanning...</span>
                </>
              ) : (
                <>
                  <Play className="w-4 h-4 fill-white" />
                  <span>Scan Repository</span>
                </>
              )}
            </button>
          </div>

          {/* Preset Buttons */}
          <div className="flex flex-wrap items-center gap-2 text-xs">
            <span className="text-slate-400 font-bold uppercase text-[10px]">Presets:</span>
            {demoRepos.map((r) => {
              const isSelected = repoUrl.includes(r.name);
              return (
                <button
                  key={r.name}
                  onClick={() => {
                    setRepoUrl(`https://github.com/${r.name}`);
                    onTriggerScan(`https://github.com/${r.name}`);
                  }}
                  className={`px-2.5 py-1 rounded-lg border text-[11px] font-bold transition-all shadow-sm flex items-center gap-1 ${
                    isSelected
                      ? 'bg-red-50 border-red-300 text-[#FF2E55]'
                      : 'bg-white border-red-100 hover:border-red-300 text-slate-700 hover:text-[#FF2E55]'
                  }`}
                >
                  <span>{r.label}</span>
                  {isSelected && <Check className="w-3 h-3 text-[#FF2E55]" />}
                </button>
              );
            })}
          </div>
        </div>

        {/* Right Column: Live Laser Scanner Code Simulator */}
        <div className="lg:col-span-5">
          <div className="p-4 rounded-2xl bg-[#0F0F12] border border-red-900/60 shadow-2xl relative overflow-hidden text-slate-200 font-mono text-xs">
            {/* Laser Beam Visual Line */}
            <div
              className="absolute left-0 right-0 h-1 bg-gradient-to-r from-transparent via-[#FF2E55] to-transparent shadow-[0_0_15px_#FF2E55] z-20 pointer-events-none transition-all duration-150"
              style={{ top: `${(scannedLine / 25) * 100}%` }}
            />

            <div className="flex items-center justify-between pb-3 border-b border-slate-800 text-[10px] text-slate-400">
              <span className="flex items-center gap-1.5 font-bold text-red-400">
                <Radio className="w-3 h-3 text-[#FF2E55] animate-pulse" />
                LIVE SCANNER
              </span>
              <span>LINE {scannedLine} / 25</span>
            </div>

            <div className="py-3 space-y-1 text-[11px] leading-relaxed">
              <div className={scannedLine === 1 ? 'bg-red-950/60 text-red-400 font-bold px-1 rounded' : ''}>01: import &#123; rawData &#125; from './payload';</div>
              <div className={scannedLine === 2 ? 'bg-red-950/60 text-red-400 font-bold px-1 rounded' : ''}>02: import &#123; UserProfile &#125; from '../user/userProfile';</div>
              <div className={scannedLine === 3 ? 'bg-red-950/60 text-red-400 font-bold px-1 rounded' : ''}>03: </div>
              <div className={scannedLine === 4 ? 'bg-red-950/60 text-red-400 font-bold px-1 rounded' : ''}>04: // FLAG: Knip Unused Export</div>
              <div className={scannedLine === 5 ? 'bg-red-900/80 text-rose-300 font-bold px-1 rounded' : ''}>05: export function calculateLegacyMetrics(d) &#123;</div>
              <div className={scannedLine === 6 ? 'bg-red-950/60 text-red-400 font-bold px-1 rounded' : ''}>06:   return d.map(v =&gt; v * 1.05);</div>
              <div className={scannedLine === 7 ? 'bg-red-950/60 text-red-400 font-bold px-1 rounded' : ''}>07: &#125;</div>
              <div className={scannedLine === 8 ? 'bg-red-950/60 text-red-400 font-bold px-1 rounded' : ''}>08: </div>
              <div className={scannedLine === 9 ? 'bg-red-950/60 text-red-400 font-bold px-1 rounded' : ''}>09: // FLAG: Madge Circular Cycle</div>
              <div className={scannedLine === 10 ? 'bg-red-900/80 text-rose-300 font-bold px-1 rounded' : ''}>10: useSessionContext(UserProfile);</div>
              <div className={scannedLine === 11 ? 'bg-red-950/60 text-red-400 font-bold px-1 rounded' : ''}>11: // FLAG: jscpd 92% Duplicate Fragment</div>
              <div className={scannedLine === 12 ? 'bg-red-900/80 text-rose-300 font-bold px-1 rounded' : ''}>12: formatCurrency(payload.balance);</div>
            </div>

            {/* Live Progress Bar when scanning */}
            {isScanning && (
              <div className="pt-2 border-t border-slate-800">
                <div className="flex justify-between text-[10px] text-red-400 font-bold mb-1">
                  <span>{scanStatus}</span>
                  <span>{scanProgress}%</span>
                </div>
                <div className="w-full h-1.5 bg-slate-800 rounded-full overflow-hidden">
                  <div className="h-full bg-[#FF2E55] transition-all duration-300" style={{ width: `${scanProgress}%` }} />
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </section>
  );
};
