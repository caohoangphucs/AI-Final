from __future__ import annotations

import heapq
import json
import math
from collections import deque
from dataclasses import dataclass
from pathlib import Path
from typing import Literal


EDGE_LENGTH_WEIGHT = 1.0
ASCENT_COST_WEIGHT = 4.0

AlgorithmName = Literal["dfs", "bfs", "iddfs", "ucs", "greedy", "astar"]


@dataclass
class GraphSearchResult:
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

    def solve(self, start_id: int, goal_id: int, algorithm: AlgorithmName) -> GraphSearchResult:
        self.ensure_node(start_id)
        self.ensure_node(goal_id)

        if start_id == goal_id:
            return GraphSearchResult(
                algorithm=algorithm,
                found=True,
                start_id=start_id,
                goal_id=goal_id,
                path_node_ids=[start_id],
                path_positions=[list(self.positions[start_id])],
                path_cost=0.0,
                visited_vertices=1,
                visited_edges=0,
                discovered_vertices=1,
                closed_order=[start_id],
                came_from={},
            )

        if algorithm == "dfs":
            return self._solve_uninformed(start_id, goal_id, "dfs")
        if algorithm == "bfs":
            return self._solve_uninformed(start_id, goal_id, "bfs")
        if algorithm == "iddfs":
            return self._solve_iddfs(start_id, goal_id)
        if algorithm == "ucs":
            return self._solve_priority(start_id, goal_id, "ucs")
        if algorithm == "greedy":
            return self._solve_priority(start_id, goal_id, "greedy")
        if algorithm == "astar":
            return self._solve_priority(start_id, goal_id, "astar")
        raise ValueError(f"Unsupported algorithm: {algorithm}")

    def _solve_uninformed(self, start_id: int, goal_id: int, algorithm: Literal["dfs", "bfs"]) -> GraphSearchResult:
        frontier = deque([start_id])
        frontier_membership = {start_id}
        closed: set[int] = set()
        closed_order: list[int] = []
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
            closed_order.append(current_id)
            visited_vertices += 1

            if current_id == goal_id:
                return self._build_found_result(
                    algorithm=algorithm,
                    start_id=start_id,
                    goal_id=goal_id,
                    came_from=came_from,
                    g_score=g_score,
                    visited_vertices=visited_vertices,
                    visited_edges=visited_edges,
                    discovered_vertices=discovered_vertices,
                    closed_order=closed_order,
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

        return self._build_not_found_result(
            algorithm=algorithm,
            start_id=start_id,
            goal_id=goal_id,
            visited_vertices=visited_vertices,
            visited_edges=visited_edges,
            discovered_vertices=discovered_vertices,
            closed_order=closed_order,
        )

    def _solve_priority(self, start_id: int, goal_id: int, algorithm: Literal["ucs", "greedy", "astar"]) -> GraphSearchResult:
        frontier: list[tuple[float, int]] = [(self._priority_for(start_id, goal_id, 0.0, algorithm), start_id)]
        frontier_membership = {start_id}
        closed: set[int] = set()
        closed_order: list[int] = []
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
            closed_order.append(current_id)
            visited_vertices += 1

            if current_id == goal_id:
                return self._build_found_result(
                    algorithm=algorithm,
                    start_id=start_id,
                    goal_id=goal_id,
                    came_from=came_from,
                    g_score=g_score,
                    visited_vertices=visited_vertices,
                    visited_edges=visited_edges,
                    discovered_vertices=discovered_vertices,
                    closed_order=closed_order,
                )

            for neighbor_id in self.neighbors.get(current_id, []):
                visited_edges += 1
                if neighbor_id in closed:
                    continue

                tentative_g = g_score[current_id] + self.traversal_cost(current_id, neighbor_id)
                if tentative_g < g_score.get(neighbor_id, math.inf):
                    came_from[neighbor_id] = current_id
                    g_score[neighbor_id] = tentative_g
                    priority = self._priority_for(neighbor_id, goal_id, tentative_g, algorithm)
                    heapq.heappush(frontier, (priority, neighbor_id))
                    if neighbor_id not in frontier_membership:
                        frontier_membership.add(neighbor_id)
                        discovered_vertices += 1

        return self._build_not_found_result(
            algorithm=algorithm,
            start_id=start_id,
            goal_id=goal_id,
            visited_vertices=visited_vertices,
            visited_edges=visited_edges,
            discovered_vertices=discovered_vertices,
            closed_order=closed_order,
        )

    def _priority_for(self, node_id: int, goal_id: int, g_cost: float, algorithm: Literal["ucs", "greedy", "astar"]) -> float:
        if algorithm == "ucs":
            return g_cost
        if algorithm == "greedy":
            return self.heuristic(node_id, goal_id)
        return g_cost + self.heuristic(node_id, goal_id)

    def _solve_iddfs(self, start_id: int, goal_id: int) -> GraphSearchResult:
        max_depth = len(self.nodes)
        total_visited_vertices = 0
        total_visited_edges = 0
        total_discovered_vertices = 0
        aggregate_closed_order: list[int] = []

        for depth_limit in range(max_depth + 1):
            closed_order: list[int] = []
            came_from: dict[int, int] = {}
            g_score = {start_id: 0.0}
            path_stack = {start_id}
            counters = {
                "visited_vertices": 0,
                "visited_edges": 0,
                "discovered_vertices": 1,
            }

            found = self._depth_limited_dfs(
                current_id=start_id,
                goal_id=goal_id,
                depth_limit=depth_limit,
                current_depth=0,
                path_stack=path_stack,
                came_from=came_from,
                g_score=g_score,
                counters=counters,
                closed_order=closed_order,
            )

            visited_vertices = counters["visited_vertices"]
            visited_edges = counters["visited_edges"]
            discovered_vertices = counters["discovered_vertices"]

            total_visited_vertices += visited_vertices
            total_visited_edges += visited_edges
            total_discovered_vertices += discovered_vertices
            aggregate_closed_order.extend(closed_order)

            if found:
                return self._build_found_result(
                    algorithm="iddfs",
                    start_id=start_id,
                    goal_id=goal_id,
                    came_from=came_from,
                    g_score=g_score,
                    visited_vertices=total_visited_vertices,
                    visited_edges=total_visited_edges,
                    discovered_vertices=total_discovered_vertices,
                    closed_order=aggregate_closed_order,
                )

        return self._build_not_found_result(
            algorithm="iddfs",
            start_id=start_id,
            goal_id=goal_id,
            visited_vertices=total_visited_vertices,
            visited_edges=total_visited_edges,
            discovered_vertices=total_discovered_vertices,
            closed_order=aggregate_closed_order,
        )

    def _depth_limited_dfs(
        self,
        current_id: int,
        goal_id: int,
        depth_limit: int,
        current_depth: int,
        path_stack: set[int],
        came_from: dict[int, int],
        g_score: dict[int, float],
        counters: dict[str, int],
        closed_order: list[int],
    ) -> bool:
        counters["visited_vertices"] += 1
        closed_order.append(current_id)

        if current_id == goal_id:
            return True
        if current_depth == depth_limit:
            return False

        for neighbor_id in self.neighbors.get(current_id, []):
            counters["visited_edges"] += 1
            if neighbor_id in path_stack:
                continue
            if neighbor_id not in came_from:
                counters["discovered_vertices"] += 1
            came_from[neighbor_id] = current_id
            g_score[neighbor_id] = g_score[current_id] + self.traversal_cost(current_id, neighbor_id)
            path_stack.add(neighbor_id)
            if self._depth_limited_dfs(
                current_id=neighbor_id,
                goal_id=goal_id,
                depth_limit=depth_limit,
                current_depth=current_depth + 1,
                path_stack=path_stack,
                came_from=came_from,
                g_score=g_score,
                counters=counters,
                closed_order=closed_order,
            ):
                return True
            path_stack.remove(neighbor_id)

        return False

    def _build_found_result(
        self,
        algorithm: AlgorithmName,
        start_id: int,
        goal_id: int,
        came_from: dict[int, int],
        g_score: dict[int, float],
        visited_vertices: int,
        visited_edges: int,
        discovered_vertices: int,
        closed_order: list[int],
    ) -> GraphSearchResult:
        path_node_ids = self._reconstruct_path(goal_id, came_from)
        path_positions = [list(self.positions[node_id]) for node_id in path_node_ids]
        return GraphSearchResult(
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
            closed_order=closed_order,
            came_from={str(node_id): parent_id for node_id, parent_id in came_from.items()},
        )

    def _build_not_found_result(
        self,
        algorithm: AlgorithmName,
        start_id: int,
        goal_id: int,
        visited_vertices: int,
        visited_edges: int,
        discovered_vertices: int,
        closed_order: list[int],
    ) -> GraphSearchResult:
        return GraphSearchResult(
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
            closed_order=closed_order,
            came_from={},
        )

    @staticmethod
    def _reconstruct_path(goal_id: int, came_from: dict[int, int]) -> list[int]:
        path = [goal_id]
        current = goal_id
        while current in came_from:
            current = came_from[current]
            path.insert(0, current)
        return path
