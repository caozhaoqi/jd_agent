"use client";

import { useEffect, useRef, useState, useCallback } from 'react';

interface KnowledgeNode {
  id: string;
  label: string;
  type: 'document' | 'concept' | 'keyword' | 'category';
  importance: number;
  metadata?: Record<string, any>;
}

interface KnowledgeEdge {
  source: string;
  target: string;
  relationship: string;
  weight: number;
}

interface KnowledgeGraphData {
  nodes: KnowledgeNode[];
  edges: KnowledgeEdge[];
}

interface KnowledgeGraphProps {
  data: KnowledgeGraphData;
  className?: string;
  onNodeClick?: (node: KnowledgeNode) => void;
  width?: number;
  height?: number;
}

interface PositionedNode extends KnowledgeNode {
  x: number;
  y: number;
  vx: number;
  vy: number;
}

export default function KnowledgeGraph({
  data,
  className = "",
  onNodeClick,
  width = 800,
  height = 600
}: KnowledgeGraphProps) {
  const svgRef = useRef<SVGSVGElement>(null);
  const [nodes, setNodes] = useState<PositionedNode[]>([]);
  const [edges, setEdges] = useState<{ source: string; target: string; weight: number }[]>([]);
  const [selectedNode, setSelectedNode] = useState<string | null>(null);
  const [isSimulating, setIsSimulating] = useState<boolean>(true);
  const animationRef = useRef<number>(0);
  const simulationRef = useRef<{
    nodes: PositionedNode[];
    alpha: number;
    tick: () => void;
  } | null>(null);

  const initializeLayout = useCallback(() => {
    const centerX = width / 2;
    const centerY = height / 2;
    const radius = Math.min(width, height) / 3;

    const newNodes: PositionedNode[] = data.nodes.map((node, index) => {
      const angle = (index / data.nodes.length) * 2 * Math.PI;
      return {
        ...node,
        x: centerX + Math.cos(angle) * radius,
        y: centerY + Math.sin(angle) * radius,
        vx: 0,
        vy: 0
      };
    });

    const newEdges = data.edges.map(edge => ({
      source: edge.source,
      target: edge.target,
      weight: edge.weight
    }));

    setNodes(newNodes);
    setEdges(newEdges);

    simulationRef.current = {
      nodes: newNodes,
      alpha: 1,
      tick: () => {}
    };
  }, [data, width, height]);

  const runSimulation = useCallback(() => {
    if (!simulationRef.current || !isSimulating) return;

    const { nodes: simNodes, alpha } = simulationRef.current;
    const alphaDecay = 0.02;
    const velocityDecay = 0.4;
    const centerStrength = 0.05;
    const linkStrength = 0.1;
    const repulsionStrength = 200;

    simulationRef.current.alpha = alpha - alphaDecay;

    if (simulationRef.current.alpha <= 0) {
      setIsSimulating(false);
      return;
    }

    const nodeMap = new Map(simNodes.map((n, i) => [n.id, i]));

    for (let i = 0; i < simNodes.length; i++) {
      const node = simNodes[i];

      const dx = (width / 2) - node.x;
      const dy = (height / 2) - node.y;
      node.vx += dx * centerStrength * alpha;
      node.vy += dy * centerStrength * alpha;

      for (let j = i + 1; j < simNodes.length; j++) {
        const other = simNodes[j];
        const dx = node.x - other.x;
        const dy = node.y - other.y;
        const dist = Math.sqrt(dx * dx + dy * dy) || 1;
        const force = repulsionStrength / (dist * dist) * alpha;
        node.vx += (dx / dist) * force;
        node.vy += (dy / dist) * force;
        other.vx -= (dx / dist) * force;
        other.vy -= (dy / dist) * force;
      }
    }

    edges.forEach(edge => {
      const sourceIdx = nodeMap.get(edge.source);
      const targetIdx = nodeMap.get(edge.target);
      
      if (sourceIdx !== undefined && targetIdx !== undefined) {
        const source = simNodes[sourceIdx];
        const target = simNodes[targetIdx];
        
        const dx = target.x - source.x;
        const dy = target.y - source.y;
        const dist = Math.sqrt(dx * dx + dy * dy) || 1;
        
        const targetDist = 150;
        const force = (dist - targetDist) * linkStrength * alpha * edge.weight;
        
        const fx = (dx / dist) * force;
        const fy = (dy / dist) * force;
        
        source.vx += fx;
        source.vy += fy;
        target.vx -= fx;
        target.vy -= fy;
      }
    });

    for (const node of simNodes) {
      node.vx *= velocityDecay;
      node.vy *= velocityDecay;
      node.x += node.vx;
      node.y += node.vy;

      const padding = 50;
      node.x = Math.max(padding, Math.min(width - padding, node.x));
      node.y = Math.max(padding, Math.min(height - padding, node.y));
    }

    setNodes([...simNodes]);
  }, [edges, width, height, isSimulating]);

  useEffect(() => {
    initializeLayout();
  }, [initializeLayout]);

  useEffect(() => {
    if (!isSimulating) return;

    const animate = () => {
      runSimulation();
      animationRef.current = requestAnimationFrame(animate);
    };

    animationRef.current = requestAnimationFrame(animate);

    return () => {
      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current);
      }
    };
  }, [isSimulating, runSimulation]);

  const handleNodeClick = (node: KnowledgeNode) => {
    setSelectedNode(node.id === selectedNode ? null : node.id);
    onNodeClick?.(node);
  };

  const handleRestart = () => {
    initializeLayout();
    setIsSimulating(true);
  };

  const getNodeColor = (type: KnowledgeNode['type'], selected: boolean): string => {
    const colors: Record<KnowledgeNode['type'], string> = {
      document: '#3B82F6',
      concept: '#10B981',
      keyword: '#F59E0B',
      category: '#8B5CF6'
    };
    const baseColor = colors[type] || '#6B7280';
    return selected ? '#EF4444' : baseColor;
  };

  const getNodeRadius = (importance: number): number => {
    return 20 + importance * 30;
  };

  return (
    <div className={`bg-gray-900 rounded-xl p-4 ${className}`}>
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-white flex items-center gap-2">
          🕸️ 知识图谱可视化
        </h3>
        <div className="flex items-center gap-2">
          <button
            onClick={handleRestart}
            className="px-3 py-1 bg-blue-600 hover:bg-blue-500 text-white text-sm rounded-lg transition-colors"
          >
            重置布局
          </button>
          <div className="flex items-center gap-1 text-sm text-gray-400">
            <span className={`w-2 h-2 rounded-full ${isSimulating ? 'bg-green-400 animate-pulse' : 'bg-gray-400'}`}></span>
            {isSimulating ? '模拟中' : '已稳定'}
          </div>
        </div>
      </div>

      <div className="flex items-center gap-4 mb-4 text-xs">
        <div className="flex items-center gap-1">
          <span className="w-3 h-3 rounded-full bg-blue-500"></span>
          <span className="text-gray-400">文档</span>
        </div>
        <div className="flex items-center gap-1">
          <span className="w-3 h-3 rounded-full bg-green-500"></span>
          <span className="text-gray-400">概念</span>
        </div>
        <div className="flex items-center gap-1">
          <span className="w-3 h-3 rounded-full bg-yellow-500"></span>
          <span className="text-gray-400">关键词</span>
        </div>
        <div className="flex items-center gap-1">
          <span className="w-3 h-3 rounded-full bg-purple-500"></span>
          <span className="text-gray-400">分类</span>
        </div>
      </div>

      <svg
        ref={svgRef}
        width={width}
        height={height}
        className="bg-gray-800 rounded-lg"
        style={{ cursor: 'grab' }}
      >
        <defs>
          <filter id="glow" x="-50%" y="-50%" width="200%" height="200%">
            <feGaussianBlur stdDeviation="3" result="coloredBlur" />
            <feMerge>
              <feMergeNode in="coloredBlur" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
          <marker
            id="arrowhead"
            markerWidth="10"
            markerHeight="7"
            refX="9"
            refY="3.5"
            orient="auto"
          >
            <polygon points="0 0, 10 3.5, 0 7" fill="#6B7280" />
          </marker>
        </defs>

        {edges.map((edge, index) => {
          const sourceNode = nodes.find(n => n.id === edge.source);
          const targetNode = nodes.find(n => n.id === edge.target);
          
          if (!sourceNode || !targetNode) return null;

          return (
            <line
              key={`edge-${index}`}
              x1={sourceNode.x}
              y1={sourceNode.y}
              x2={targetNode.x}
              y2={targetNode.y}
              stroke="#4B5563"
              strokeWidth={Math.max(1, edge.weight * 3)}
              strokeOpacity={0.6}
              markerEnd="url(#arrowhead)"
            />
          );
        })}

        {nodes.map((node) => (
          <g
            key={node.id}
            onClick={() => handleNodeClick(node)}
            style={{ cursor: 'pointer' }}
            transform={`translate(${node.x}, ${node.y})`}
          >
            <circle
              r={getNodeRadius(node.importance)}
              fill={getNodeColor(node.type, selectedNode === node.id)}
              fillOpacity={0.2}
              stroke={getNodeColor(node.type, selectedNode === node.id)}
              strokeWidth={selectedNode === node.id ? 3 : 2}
              filter={selectedNode === node.id ? 'url(#glow)' : undefined}
              className="transition-all duration-300"
            />
            <circle
              r={getNodeRadius(node.importance) * 0.6}
              fill={getNodeColor(node.type, selectedNode === node.id)}
              className="transition-all duration-300"
            />
            <text
              y={getNodeRadius(node.importance) + 16}
              textAnchor="middle"
              fill="#E5E7EB"
              fontSize={11}
              fontWeight={500}
              className="select-none"
            >
              {node.label.length > 15 ? node.label.slice(0, 15) + '...' : node.label}
            </text>
          </g>
        ))}
      </svg>

      {selectedNode && (
        <div className="mt-4 p-3 bg-gray-800 rounded-lg">
          <div className="text-sm font-medium text-white mb-2">
            {data.nodes.find(n => n.id === selectedNode)?.label}
          </div>
          <div className="text-xs text-gray-400">
            类型: {data.nodes.find(n => n.id === selectedNode)?.type} | 
            重要性: {(data.nodes.find(n => n.id === selectedNode)?.importance ?? 0).toFixed(2)}
          </div>
        </div>
      )}

      <div className="mt-4 text-xs text-gray-500">
        节点数: {nodes.length} | 边数: {edges.length}
      </div>
    </div>
  );
}

export function useKnowledgeGraphData(initialData?: KnowledgeGraphData) {
  const [data, setData] = useState<KnowledgeGraphData>(
    initialData || { nodes: [], edges: [] }
  );
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchGraphData = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    
    try {
      const response = await fetch('/api/v1/knowledge/graph');
      if (!response.ok) {
        throw new Error('Failed to fetch knowledge graph data');
      }
      const graphData = await response.json();
      setData(graphData);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setIsLoading(false);
    }
  }, []);

  const updateData = useCallback((newData: KnowledgeGraphData) => {
    setData(newData);
  }, []);

  return {
    data,
    setData: updateData,
    fetchGraphData,
    isLoading,
    error
  };
}
