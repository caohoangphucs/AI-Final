from __future__ import annotations

import heapq
import json
import math
from collections import deque
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field


ROOT_DIR = Path(__file__).resolve().parent.parent
GRAPH_PATH = ROOT_DIR / "data" / "navigation_graph.json"
EDGE_LENGTH_WEIGHT = 1.0
ASCENT_COST_WEIGHT = 4.0

AlgorithmName = Literal["astar", "bfs", "dfs"]


class SolvePathRequest(BaseModel):
    start_id: int = Field(..., ge=0)
    goal_id: int = Field(..., ge=0)
    algorithm: AlgorithmName = "astar"


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


class NavigationGraph:
    def __init__(self, graph_path: Path) -> None:
        payload = json.loads(graph_path.read_text(encoding="utf-8"))
        self.nodes = {int(node["id"]): node for node in payload["nodes"]}
        self.positions = {
            node_id: tuple(float(coord) for coord in node["position"])
            for node_id, node in self.nodes.items()
        }
        self.neighbors = {
            node_id: [int(neighbor_id) for neighbor_id in node.get("neighbors", [])]
            for node_id, node in self.nodes.items()
        }

    def ensure_node(self, node_id: int) -> None:
        if node_id not in self.nodes:
            raise KeyError(node_id)

    def heuristic(self, a: int, b: int) -> float:
        ax, ay, az = self.positions[a]
        bx, by, bz = self.positions[b]
        return math.dist((ax, ay, az), (bx, by, bz)) * EDGE_LENGTH_WEIGHT

    def traversal_cost(self, a: int, b: int) -> float:
        ax, ay, az = self.positions[a]
        bx, by, bz = self.positions[b]
        edge_length = math.dist((ax, ay, az), (bx, by, bz))
        ascent = max(0.0, by - ay)
        return edge_length * EDGE_LENGTH_WEIGHT + ascent * ASCENT_COST_WEIGHT

    def solve(self, start_id: int, goal_id: int, algorithm: AlgorithmName) -> SolvePathResponse:
        self.ensure_node(start_id)
        self.ensure_node(goal_id)

        if start_id == goal_id:
            position = list(self.positions[start_id])
            return SolvePathResponse(
                algorithm=algorithm,
                found=True,
                start_id=start_id,
                goal_id=goal_id,
                path_node_ids=[start_id],
                path_positions=[position],
                path_cost=0.0,
                visited_vertices=1,
                visited_edges=0,
                discovered_vertices=1,
            )

        if algorithm == "astar":
            return self._solve_astar(start_id, goal_id)
        if algorithm == "bfs":
            return self._solve_bfs(start_id, goal_id)
        if algorithm == "dfs":
            return self._solve_dfs(start_id, goal_id)
        raise ValueError(f"Unsupported algorithm: {algorithm}")

    def _solve_astar(self, start_id: int, goal_id: int) -> SolvePathResponse:
        frontier: list[tuple[float, int]] = [(self.heuristic(start_id, goal_id), start_id)]
        frontier_membership = {start_id}
        closed: set[int] = set()
        came_from: dict[int, int] = {}
        g_score = {start_id: 0.0}
        discovered_vertices = 1
        visited_vertices = 0
        visited_edges = 0

        while frontier:
            _, current_id = heapq.heappop(frontier)
            if current_id in closed:
                continue
            frontier_membership.discard(current_id)
            closed.add(current_id)
            visited_vertices += 1

            if current_id == goal_id:
                return self._build_response(
                    algorithm="astar",
                    start_id=start_id,
                    goal_id=goal_id,
                    came_from=came_from,
                    g_score=g_score,
                    visited_vertices=visited_vertices,
                    visited_edges=visited_edges,
                    discovered_vertices=discovered_vertices,
                )

            for neighbor_id in self.neighbors.get(current_id, []):
                visited_edges += 1
                if neighbor_id in closed:
                    continue
                tentative_g = g_score[current_id] + self.traversal_cost(current_id, neighbor_id)
                if tentative_g < g_score.get(neighbor_id, math.inf):
                    came_from[neighbor_id] = current_id
                    g_score[neighbor_id] = tentative_g
                    heapq.heappush(
                        frontier,
                        (tentative_g + self.heuristic(neighbor_id, goal_id), neighbor_id),
                    )
                    if neighbor_id not in frontier_membership:
                        frontier_membership.add(neighbor_id)
                        discovered_vertices += 1

        return self._build_not_found(
            algorithm="astar",
            start_id=start_id,
            goal_id=goal_id,
            visited_vertices=visited_vertices,
            visited_edges=visited_edges,
            discovered_vertices=discovered_vertices,
        )

    def _solve_bfs(self, start_id: int, goal_id: int) -> SolvePathResponse:
        return self._solve_unweighted(start_id, goal_id, algorithm="bfs")

    def _solve_dfs(self, start_id: int, goal_id: int) -> SolvePathResponse:
        return self._solve_unweighted(start_id, goal_id, algorithm="dfs")

    def _solve_unweighted(self, start_id: int, goal_id: int, algorithm: Literal["bfs", "dfs"]) -> SolvePathResponse:
        frontier = deque([start_id])
        frontier_membership = {start_id}
        closed: set[int] = set()
        came_from: dict[int, int] = {}
        g_score = {start_id: 0.0}
        discovered_vertices = 1
        visited_vertices = 0
        visited_edges = 0

        while frontier:
            current_id = frontier.popleft() if algorithm == "bfs" else frontier.pop()
            frontier_membership.discard(current_id)
            if current_id in closed:
                continue
            closed.add(current_id)
            visited_vertices += 1

            if current_id == goal_id:
                return self._build_response(
                    algorithm=algorithm,
                    start_id=start_id,
                    goal_id=goal_id,
                    came_from=came_from,
                    g_score=g_score,
                    visited_vertices=visited_vertices,
                    visited_edges=visited_edges,
                    discovered_vertices=discovered_vertices,
                )

            for neighbor_id in self.neighbors.get(current_id, []):
                visited_edges += 1
                if neighbor_id in closed:
                    continue
                if neighbor_id in frontier_membership or neighbor_id == start_id or neighbor_id in came_from:
                    continue
                came_from[neighbor_id] = current_id
                g_score[neighbor_id] = g_score[current_id] + self.traversal_cost(current_id, neighbor_id)
                frontier.append(neighbor_id)
                frontier_membership.add(neighbor_id)
                discovered_vertices += 1

        return self._build_not_found(
            algorithm=algorithm,
            start_id=start_id,
            goal_id=goal_id,
            visited_vertices=visited_vertices,
            visited_edges=visited_edges,
            discovered_vertices=discovered_vertices,
        )

    def _build_response(
        self,
        algorithm: AlgorithmName,
        start_id: int,
        goal_id: int,
        came_from: dict[int, int],
        g_score: dict[int, float],
        visited_vertices: int,
        visited_edges: int,
        discovered_vertices: int,
    ) -> SolvePathResponse:
        path_node_ids = self._reconstruct_path(goal_id, came_from)
        path_positions = [list(self.positions[node_id]) for node_id in path_node_ids]
        return SolvePathResponse(
            algorithm=algorithm,
            found=True,
            start_id=start_id,
            goal_id=goal_id,
            path_node_ids=path_node_ids,
            path_positions=path_positions,
            path_cost=float(g_score.get(goal_id, 0.0)),
            visited_vertices=visited_vertices,
            visited_edges=visited_edges,
            discovered_vertices=discovered_vertices,
        )

    def _build_not_found(
        self,
        algorithm: AlgorithmName,
        start_id: int,
        goal_id: int,
        visited_vertices: int,
        visited_edges: int,
        discovered_vertices: int,
    ) -> SolvePathResponse:
        return SolvePathResponse(
            algorithm=algorithm,
            found=False,
            start_id=start_id,
            goal_id=goal_id,
            path_node_ids=[],
            path_positions=[],
            path_cost=0.0,
            visited_vertices=visited_vertices,
            visited_edges=visited_edges,
            discovered_vertices=discovered_vertices,
        )

    @staticmethod
    def _reconstruct_path(goal_id: int, came_from: dict[int, int]) -> list[int]:
        path = [goal_id]
        current = goal_id
        while current in came_from:
            current = came_from[current]
            path.insert(0, current)
        return path


graph = NavigationGraph(GRAPH_PATH)
app = FastAPI(title="Campus Navigation Service", version="1.0.0")


@app.get("/health")
def health() -> dict[str, object]:
    return {
        "status": "ok",
        "graph_path": str(GRAPH_PATH),
        "node_count": len(graph.nodes),
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
        return graph.solve(request.start_id, request.goal_id, request.algorithm)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"Unknown node id: {exc.args[0]}") from exc
