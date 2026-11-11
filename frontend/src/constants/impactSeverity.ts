export const IMPACT_SEVERITIES = ['low', 'medium', 'high', 'critical'] as const;
export type ImpactSeverity = (typeof IMPACT_SEVERITIES)[number];
export const SEVERITY_LABELS: Record<ImpactSeverity, string> = {
  low: '低',
  medium: '中',
  high: '高',
  critical: '严重',
};
export const SEVERITY_ORDER: Record<ImpactSeverity, number> = {
  low: 0,
  medium: 1,
  high: 2,
  critical: 3,
};
