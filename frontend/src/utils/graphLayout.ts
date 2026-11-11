import type { GraphEdge, GraphNode } from '../types/lineageEdge';

export interface LaidOutNode extends GraphNode {
  x: number;
  y: number;
  width: number;
  height: number;
}

export interface LaidOutEdge extends GraphEdge {
  path: string;
  cycle: boolean;
}

const NODE_WIDTH = 168;
const NODE_HEIGHT = 52;
const COL_GAP = 250;
const ROW_GAP = 78;

/**
 * 分层有向布局：按 depth 分层（x 轴），同层按名称排序（y 轴），
 * 环边（in_cycle）单独标记，用于虚线绘制。
 */
export function layoutGraph(nodes: GraphNode[], edges: GraphEdge[]): {
  nodes: LaidOutNode[];
  edges: LaidOutEdge[];
  cycles: GraphEdge[];
  width: number;
  height: number;
} {
  // layer：下游为正、上游为负；整体平移到 0 起，保证上游在左、下游在右
  const rawLayer = (node: GraphNode) => (node.layer !== undefined ? node.layer : node.depth ?? 0);
  const minLayer = nodes.length > 0 ? Math.min(...nodes.map(rawLayer)) : 0;
  const layers = new Map<number, GraphNode[]>();
  nodes.forEach((node) => {
    const depth = rawLayer(node) - minLayer;
    if (!layers.has(depth)) layers.set(depth, []);
    layers.get(depth)!.push(node);
  });
  const laid: LaidOutNode[] = [];
  layers.forEach((layerNodes, depth) => {
    layerNodes
      .slice()
      .sort((a, b) => (a.asset_name + (a.column || '')).localeCompare(b.asset_name + (b.column || '')))
      .forEach((node, index) => {
        laid.push({
          ...node,
          x: 40 + depth * COL_GAP,
          y: 40 + index * ROW_GAP,
          width: NODE_WIDTH,
          height: NODE_HEIGHT,
        });
      });
  });
  const byId = new Map(laid.map((node) => [node.id, node]));
  const cycleSet = new Set(
    edges.filter((edge) => edge.in_cycle).map((edge) => `${edge.source}->${edge.target}`),
  );
  const laidEdges: LaidOutEdge[] = [];
  edges.forEach((edge) => {
    const source = byId.get(edge.source);
    const target = byId.get(edge.target);
    if (!source || !target) return;
    const x1 = source.x + source.width;
    const y1 = source.y + source.height / 2;
    const x2 = target.x;
    const y2 = target.y + target.height / 2;
    const mid = (x1 + x2) / 2;
    laidEdges.push({
      ...edge,
      cycle: cycleSet.has(`${edge.source}->${edge.target}`),
      path: `M ${x1} ${y1} C ${mid} ${y1}, ${mid} ${y2}, ${x2} ${y2}`,
    });
  });
  const width = Math.max(720, ...laid.map((node) => node.x + node.width + 40));
  const height = Math.max(360, ...laid.map((node) => node.y + node.height + 40));
  return { nodes: laid, edges: laidEdges, cycles: edges.filter((edge) => edge.in_cycle), width, height };
}
