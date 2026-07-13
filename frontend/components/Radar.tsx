'use client'

type RadarState = 'idle' | 'scanning' | 'complete' | 'failed'

const STATE_LABEL: Record<RadarState, string> = {
  idle: 'STANDBY',
  scanning: 'SCANNING',
  complete: 'AREA CLEAR',
  failed: 'SIGNAL LOST',
}

const STATE_COLOR: Record<RadarState, string> = {
  idle: 'var(--mute)',
  scanning: 'var(--signal)',
  complete: 'var(--confirm)',
  failed: 'var(--alert)',
}

/**
 * The signature element: a scout scope that shows the live search radius and
 * sweeps while a run is in progress. Tied to the radius control — not decoration.
 */
export default function Radar({ radiusKm, state }: { radiusKm: number; state: RadarState }) {
  const size = 168
  const color = STATE_COLOR[state]
  return (
    <div className="flex flex-col items-center">
      <div className="radar" style={{ width: size, height: size }}>
        {/* range rings */}
        {[0.9, 0.6, 0.32].map((s, i) => (
          <span key={i} className="radar-ring"
            style={{ inset: `${((1 - s) / 2) * 100}%`, borderColor: state === 'idle' ? undefined : `rgba(210,190,150,0.12)` }} />
        ))}
        {/* crosshair */}
        <span className="radar-cross" style={{ left: '50%', top: 0, bottom: 0, width: 1, transform: 'translateX(-.5px)' }} />
        <span className="radar-cross" style={{ top: '50%', left: 0, right: 0, height: 1, transform: 'translateY(-.5px)' }} />
        {/* sweep */}
        {state !== 'idle' && state !== 'failed' && (
          <span className={`radar-sweep ${state === 'scanning' ? 'scan' : ''}`}
                style={{ background: `conic-gradient(from 0deg, ${state === 'complete' ? 'rgba(55,208,166,0.4)' : 'rgba(245,165,36,0.55)'}, transparent 65deg)` }} />
        )}
        {/* center = you */}
        <span className="radar-core" style={{ background: color, boxShadow: `0 0 10px ${color}` }} />
      </div>

      <div className="mt-3 flex items-center gap-2 font-mono text-[11px]">
        <span className="inline-flex h-1.5 w-1.5 rounded-full" style={{ background: color, boxShadow: `0 0 6px ${color}` }} />
        <span style={{ color }}>{STATE_LABEL[state]}</span>
        <span className="text-[var(--mute)]">·</span>
        <span className="text-[var(--dim)]">{radiusKm} KM RADIUS</span>
      </div>
    </div>
  )
}
