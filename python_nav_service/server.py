from __future__ import annotations

from pathlib import Path
from time import perf_counter

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from python_nav_service.graph_search import AlgorithmName, GraphSearchResult, NavigationGraph


ROOT_DIR = Path(__file__).resolve().parent.parent
GRAPH_PATH = ROOT_DIR / "data" / "navigation_graph.json"


class SolvePathRequest(BaseModel):
    start_id: int = Field(..., ge=0)
    goal_id: int = Field(..., ge=0)
    algorithm: AlgorithmName = "astar"


class BenchmarkPathRequest(BaseModel):
    start_id: int = Field(..., ge=0)
    goal_id: int = Field(..., ge=0)
    algorithms: list[AlgorithmName] | None = None


class NodeSummary(BaseModel):
    id: int
    position: list[float]
    neighbors: list[int]


class SolvePathResponse(BaseModel):
    algorithm: AlgorithmName
    found: bool
    start_id: int
    goal_id: int
    path_node_ids: list[int]
    path_positions: list[list[float]]
    path_cost: float
    visited_vertices: int
    visited_edges: int
    discovered_vertices: int
    closed_order: list[int]
    came_from: dict[str, int]

    @classmethod
    def from_result(cls, result: GraphSearchResult) -> "SolvePathResponse":
        return cls(**result.__dict__)


class BenchmarkRow(BaseModel):
    algorithm: AlgorithmName
    found: bool
    elapsed_ms: float
    path_cost: float
    path_nodes: int
    visited_vertices: int
    visited_edges: int
    discovered_vertices: int


class BenchmarkPathResponse(BaseModel):
    start_id: int
    goal_id: int
    graph_node_count: int
    graph_edge_count: int
    rows: list[BenchmarkRow]


graph = NavigationGraph(GRAPH_PATH)
app = FastAPI(title="Campus Navigation Service", version="2.0.0")
DEFAULT_BENCHMARK_ALGORITHMS: list[AlgorithmName] = ["dfs", "bfs", "iddfs", "ucs", "greedy", "astar"]


@app.get("/health")
def health() -> dict[str, object]:
    return {
        "status": "ok",
        "graph_path": str(GRAPH_PATH),
        "node_count": len(graph.nodes),
        "algorithms": ["dfs", "bfs", "iddfs", "ucs", "greedy", "astar"],
    }


@app.get("/nodes/{node_id}", response_model=NodeSummary)
def get_node(node_id: int) -> NodeSummary:
    try:
        graph.ensure_node(node_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"Unknown node id: {node_id}") from exc

    node = graph.nodes[node_id]
    return NodeSummary(
        id=node_id,
        position=list(graph.positions[node_id]),
        neighbors=graph.neighbors[node_id],
    )


@app.post("/solve-path", response_model=SolvePathResponse)
def solve_path(request: SolvePathRequest) -> SolvePathResponse:
    try:
        result = graph.solve(request.start_id, request.goal_id, request.algorithm)
        return SolvePathResponse.from_result(result)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"Unknown node id: {exc.args[0]}") from exc


@app.post("/benchmark-path", response_model=BenchmarkPathResponse)
def benchmark_path(request: BenchmarkPathRequest) -> BenchmarkPathResponse:
    try:
        graph.ensure_node(request.start_id)
        graph.ensure_node(request.goal_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"Unknown node id: {exc.args[0]}") from exc

    algorithms = request.algorithms or DEFAULT_BENCHMARK_ALGORITHMS
    rows: list[BenchmarkRow] = []
    for algorithm in algorithms:
        started = perf_counter()
        result = graph.solve(request.start_id, request.goal_id, algorithm)
        elapsed_ms = (perf_counter() - started) * 1000.0
        rows.append(
            BenchmarkRow(
                algorithm=algorithm,
                found=result.found,
                elapsed_ms=elapsed_ms,
                path_cost=result.path_cost,
                path_nodes=len(result.path_node_ids),
                visited_vertices=result.visited_vertices,
                visited_edges=result.visited_edges,
                discovered_vertices=result.discovered_vertices,
            )
        )

    edge_count = sum(len(neighbors) for neighbors in graph.neighbors.values())
    return BenchmarkPathResponse(
        start_id=request.start_id,
        goal_id=request.goal_id,
        graph_node_count=len(graph.nodes),
        graph_edge_count=edge_count,
        rows=rows,
    )
