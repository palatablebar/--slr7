export function CycleWarning({ cycles }: { cycles: { nodes: any[]; sample_path: any[] }[] }) {
  if (!cycles || cycles.length === 0) return null;
  return (
    <div className="notice warn" style={{ marginTop: 10 }}>
      <strong>检测到 {cycles.length} 个血缘环</strong>
      <span className="muted">（环边在图中以虚线 + 橙色标记，已写入 report_json.cycles）</span>
      <div className="mono small" style={{ marginTop: 6 }}>
        {cycles[0].sample_path
          .map((node: any) => `${node.asset_name}.${node.column}`)
          .join(' → ')}
      </div>
    </div>
  );
}
