import json
import networkx as nx
from pathlib import Path
from core.models import CodeChunk, GraphNode

GRAPH_PATH = Path(__file__).parent.parent / ".data" / "graph.json"


class GraphStore:
    def __init__(self):
        self.graph = nx.DiGraph()

    def build_from_chunks(self, chunks: list[CodeChunk]):
        """Build knowledge graph from parsed code chunks."""
        name_to_id: dict[str, str] = {}  # name → node_id mapping for edge resolution

        for chunk in chunks:
            self.graph.add_node(
                chunk.id,
                name=chunk.name,
                type=chunk.type,
                file=chunk.file,
                lineno=chunk.lineno,
            )
            # Register both short name and qualified name for flexible lookup
            name_to_id[chunk.name] = chunk.id
            short_name = chunk.name.split(".")[-1]
            if short_name not in name_to_id:
                name_to_id[short_name] = chunk.id

        for chunk in chunks:
            for callee_name in chunk.calls:
                callee_id = name_to_id.get(callee_name)
                if callee_id and callee_id != chunk.id:
                    self.graph.add_edge(chunk.id, callee_id, relation="calls")

    def save(self):
        GRAPH_PATH.parent.mkdir(parents=True, exist_ok=True)
        data = nx.node_link_data(self.graph)
        with open(GRAPH_PATH, "w") as f:
            json.dump(data, f, indent=2)

    def load(self) -> bool:
        if not GRAPH_PATH.exists():
            return False
        with open(GRAPH_PATH) as f:
            data = json.load(f)
        self.graph = nx.node_link_graph(data)
        return True

    def find_callers(self, function_name: str, depth: int = 2) -> list[GraphNode]:
        """Who calls this function? (impact analysis — reversed edges)"""
        node_id = self._resolve(function_name)
        if not node_id:
            return []

        reversed_graph = self.graph.reverse()
        affected = self._bfs(reversed_graph, node_id, depth)
        return self._to_nodes(affected)

    def find_callees(self, function_name: str, depth: int = 2) -> list[GraphNode]:
        """What does this function call? (dependency analysis)"""
        node_id = self._resolve(function_name)
        if not node_id:
            return []

        deps = self._bfs(self.graph, node_id, depth)
        return self._to_nodes(deps)

    def node_count(self) -> int:
        return self.graph.number_of_nodes()

    def edge_count(self) -> int:
        return self.graph.number_of_edges()

    def _resolve(self, name: str) -> str | None:
        """Resolve a function name to its full node ID."""
        if name in self.graph:
            return name
        for node_id, attrs in self.graph.nodes(data=True):
            if attrs.get("name") == name or attrs.get("name", "").endswith(f".{name}"):
                return node_id
        return None

    def _bfs(self, graph: nx.DiGraph, start: str, depth: int) -> list[str]:
        visited, queue, result = {start}, [(start, 0)], []
        while queue:
            node, level = queue.pop(0)
            if level > 0:
                result.append(node)
            if level < depth:
                for neighbor in graph.successors(node):
                    if neighbor not in visited:
                        visited.add(neighbor)
                        queue.append((neighbor, level + 1))
        return result

    def _to_nodes(self, node_ids: list[str]) -> list[GraphNode]:
        nodes = []
        for nid in node_ids:
            attrs = self.graph.nodes.get(nid, {})
            nodes.append(GraphNode(
                id=nid,
                name=attrs.get("name", nid),
                type=attrs.get("type", "function"),
                file=attrs.get("file", ""),
                lineno=attrs.get("lineno", 0),
            ))
        return nodes
