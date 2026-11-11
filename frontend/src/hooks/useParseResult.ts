import { useCallback, useRef, useState } from 'react';
import { transformationsApi } from '../api/transformations';
import type { ParsePreview } from '../types/parse';

/** 解析状态机：pending → parsed | partial | failed；停止输入 600ms 触发试解析。 */
export function useParseResult(transformationId: string | null) {
  const [preview, setPreview] = useState<ParsePreview | null>(null);
  const [status, setStatus] = useState<'idle' | 'pending' | 'parsed' | 'partial' | 'failed'>('idle');
  const timer = useRef<number | null>(null);

  const runPreview = useCallback(
    async (sqlText: string) => {
      if (!transformationId) return null;
      setStatus('pending');
      try {
        const result = await transformationsApi.preview(transformationId, sqlText);
        setPreview(result);
        setStatus(result.parse_status as any);
        return result;
      } catch (error: any) {
        setStatus('failed');
        setPreview({
          parse_status: 'failed',
          parse_error: error.message || '解析失败',
          error_line: null,
          error_column: null,
          warnings: [],
          unresolved: [],
          columns: [],
          report: { edge_count: 0 },
        });
        return null;
      }
    },
    [transformationId],
  );

  const schedulePreview = useCallback(
    (sqlText: string) => {
      if (timer.current) window.clearTimeout(timer.current);
      timer.current = window.setTimeout(() => {
        void runPreview(sqlText);
      }, 600);
    },
    [runPreview],
  );

  return { preview, status, runPreview, schedulePreview };
}
