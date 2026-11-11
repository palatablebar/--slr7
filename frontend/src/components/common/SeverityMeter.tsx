import { SEVERITY_LABELS, SEVERITY_ORDER, type ImpactSeverity } from '../../constants/impactSeverity';

export function SeverityMeter({ severity }: { severity: ImpactSeverity | string }) {
  const level = SEVERITY_ORDER[severity as ImpactSeverity] ?? 0;
  return (
    <span className="row" style={{ gap: 8 }}>
      <span className={`sev ${severity}`} style={{ fontSize: '1.2rem' }}>
        {SEVERITY_LABELS[severity as ImpactSeverity] || severity}
      </span>
      <span style={{ display: 'inline-flex', gap: 3 }}>
        {[0, 1, 2, 3].map((index) => (
          <i
            key={index}
            style={{
              display: 'inline-block',
              width: 16,
              height: 5,
              background: index <= level ? 'var(--brass)' : 'var(--deep-line)',
            }}
          />
        ))}
      </span>
    </span>
  );
}
