from __future__ import annotations

from dataclasses import dataclass


@dataclass
class QueenState:
    placements: tuple[int, ...]

    @property
    def next_row(self) -> int:
        return len(self.placements)

    def is_goal(self, n: int) -> bool:
        return len(self.placements) == n

    def is_safe(self, col: int) -> bool:
        row = len(self.placements)
        for prev_row, prev_col in enumerate(self.placements):
            if prev_col == col:
                return False
            if abs(prev_col - col) == abs(prev_row - row):
                return False
        return True

    def successors(self, n: int) -> list["QueenState"]:
        return [
            QueenState(self.placements + (col,))
            for col in range(n)
            if self.is_safe(col)
        ]


def and_or_search_queens(n: int = 8) -> list[QueenState]:
    def or_search(state: QueenState) -> list[QueenState] | None:
        if state.is_goal(n):
            return [state]

        for successor in state.successors(n):
            plan = and_search([successor])
            if plan is not None:
                return [state] + plan
        return None

    def and_search(states: list[QueenState]) -> list[QueenState] | None:
        plan: list[QueenState] = []
        for state in states:
            subplan = or_search(state)
            if subplan is None:
                return None
            plan.extend(subplan)
        return plan

    initial = QueenState(())
    result = or_search(initial)
    if result is None:
        raise RuntimeError(f"No solution found for {n}-queens")
    return result


def render_state(state: QueenState, n: int) -> str:
    rows: list[str] = []
    for row in range(n):
        cols = []
        queen_col = state.placements[row] if row < len(state.placements) else None
        for col in range(n):
            cols.append("Q" if queen_col == col else ".")
        rows.append(" ".join(cols))
    return "\n".join(rows)


def main() -> None:
    n = 8
    plan = and_or_search_queens(n)
    for step, state in enumerate(plan):
        print(f"\nStep {step}: placed {len(state.placements)} queen(s)")
        print(render_state(state, n))


if __name__ == "__main__":
    main()
