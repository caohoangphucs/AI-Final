from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class OnlineGraph:
    adjacency: dict[str, list[str]]
    goal: str


@dataclass
class OnlineDFSAgent:
    graph: OnlineGraph
    untried: dict[str, list[str]] = field(default_factory=dict)
    unbacktracked: dict[str, list[str]] = field(default_factory=dict)
    result: dict[tuple[str, str], str] = field(default_factory=dict)
    previous_state: str | None = None
    previous_action: str | None = None

    def next_action(self, state: str) -> str | None:
        if state == self.graph.goal:
            return None

        self.untried.setdefault(state, list(self.graph.adjacency.get(state, [])))
        self.unbacktracked.setdefault(state, [])

        if self.previous_state is not None and self.previous_action is not None:
            self.result[(self.previous_state, self.previous_action)] = state
            if self.previous_state not in self.unbacktracked[state]:
                self.unbacktracked[state].append(self.previous_state)

        if self.untried[state]:
            action = self.untried[state].pop(0)
        elif self.unbacktracked[state]:
            action = self.unbacktracked[state].pop()
        else:
            return None

        self.previous_state = state
        self.previous_action = action
        return action


def run_online_dfs(graph: OnlineGraph, start: str) -> list[str]:
    agent = OnlineDFSAgent(graph)
    state = start
    trajectory = [state]

    while True:
        action = agent.next_action(state)
        if action is None:
            break
        state = action
        trajectory.append(state)
        if state == graph.goal:
            break

    return trajectory


def main() -> None:
    graph = OnlineGraph(
        adjacency={
            "S": ["A", "B"],
            "A": ["C", "D"],
            "B": ["E"],
            "C": ["G"],
            "D": [],
            "E": ["F"],
            "F": ["G"],
            "G": [],
        },
        goal="G",
    )
    trajectory = run_online_dfs(graph, "S")
    print("Online DFS trajectory:", " -> ".join(trajectory))


if __name__ == "__main__":
    main()
