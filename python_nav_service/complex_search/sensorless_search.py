from __future__ import annotations

from collections import deque
from dataclasses import dataclass


DIRECTIONS = {
    "N": (-1, 0),
    "S": (1, 0),
    "W": (0, -1),
    "E": (0, 1),
}


@dataclass(frozen=True)
class GridWorld:
    cells: tuple[str, ...]

    @property
    def height(self) -> int:
        return len(self.cells)

    @property
    def width(self) -> int:
        return len(self.cells[0])

    def is_open(self, row: int, col: int) -> bool:
        return 0 <= row < self.height and 0 <= col < self.width and self.cells[row][col] != "#"

    def all_open_positions(self) -> frozenset[tuple[int, int]]:
        return frozenset(
            (row, col)
            for row in range(self.height)
            for col in range(self.width)
            if self.is_open(row, col)
        )

    def move(self, pos: tuple[int, int], action: str) -> tuple[int, int]:
        dr, dc = DIRECTIONS[action]
        nr, nc = pos[0] + dr, pos[1] + dc
        return (nr, nc) if self.is_open(nr, nc) else pos

    def observation(self, pos: tuple[int, int]) -> tuple[bool, bool, bool, bool]:
        return tuple(self.is_open(pos[0] + dr, pos[1] + dc) for dr, dc in DIRECTIONS.values())


def sensorless_bfs(world: GridWorld, goal: tuple[int, int]) -> tuple[list[str], list[frozenset[tuple[int, int]]]]:
    start_belief = world.all_open_positions()
    frontier = deque([(start_belief, [])])
    visited = {start_belief}

    while frontier:
        belief, path = frontier.popleft()
        if belief and all(position == goal for position in belief):
            return path, [start_belief]

        for action in DIRECTIONS:
            next_belief = frozenset(world.move(position, action) for position in belief)
            if next_belief not in visited:
                visited.add(next_belief)
                frontier.append((next_belief, path + [action]))

    raise RuntimeError("No sensorless solution found")


def belief_update_with_observation(
    world: GridWorld,
    belief: frozenset[tuple[int, int]],
    action: str,
    observed_signature: tuple[bool, bool, bool, bool],
) -> frozenset[tuple[int, int]]:
    predicted = {world.move(position, action) for position in belief}
    return frozenset(pos for pos in predicted if world.observation(pos) == observed_signature)


def main() -> None:
    world = GridWorld(
        (
            "....#.",
            ".#....",
            "...#..",
            "......",
        )
    )
    goal = (3, 5)
    actions, _ = sensorless_bfs(world, goal)
    print("Sensorless action sequence:", actions)

    belief = world.all_open_positions()
    for step, action in enumerate(actions, start=1):
        observed = world.observation(goal)
        belief = belief_update_with_observation(world, belief, action, observed)
        print(f"Step {step}: action={action}, belief_size={len(belief)}, belief={sorted(belief)}")


if __name__ == "__main__":
    main()
