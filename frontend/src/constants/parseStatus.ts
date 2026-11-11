export const PARSE_STATUSES = ['pending', 'parsed', 'partial', 'failed'] as const;
export type ParseStatus = (typeof PARSE_STATUSES)[number];
export const PARSE_STATUS_LABELS: Record<ParseStatus, string> = {
  pending: '待解析',
  parsed: '解析完成',
  partial: '部分解析',
  failed: '解析失败',
};
