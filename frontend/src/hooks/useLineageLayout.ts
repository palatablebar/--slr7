import { useMemo } from 'react';
import type { GraphEdge, GraphNode } from '../types/lineageEdge';
import { layoutGraph } from '../utils/graphLayout';

/** 布局缓存：节点 id 集合 + 边 id 集合变化时才重算坐标。 */
export function useLineageLayout(nodes: GraphNode[], edges: GraphEdge[]) {
  const cacheKey = useMemo(
    () =>
      nodes.map((n) => n.id).sort().join('|') + '#' + edges.map((e) => `${e.source}->${e.target}`).sort().join('|'),
    [nodes, edges],
  );
  const layout = useMemo(() => layoutGraph(nodes, edges), [cacheKey]);
  return { layout, cacheKey };
}
