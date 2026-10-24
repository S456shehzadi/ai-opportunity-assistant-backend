"""Requirement dependency graphs and rule orchestration."""

from __future__ import annotations

from app.opportunities.eligibility.schemas import RequirementEvaluation, RequirementStatus


class DependencyNode:
    """A node in the requirement dependency tree."""

    def __init__(self, requirement_id: str, requirement_type: str, title: str):
        self.requirement_id = requirement_id
        self.requirement_type = requirement_type
        self.title = title
        self.prerequisites: list[DependencyNode] = []
        self.alternatives: list[DependencyNode] = []


class RequirementDependencyGraph:
    """Manages hierarchical requirement prerequisites and alternative pathways."""

    def __init__(self):
        self.nodes: dict[str, DependencyNode] = {}

    def add_node(self, requirement_id: str, requirement_type: str, title: str) -> DependencyNode:
        node = DependencyNode(requirement_id, requirement_type, title)
        self.nodes[requirement_id] = node
        return node

    def add_prerequisite(self, parent_id: str, prereq_id: str) -> None:
        if parent_id in self.nodes and prereq_id in self.nodes:
            self.nodes[parent_id].prerequisites.append(self.nodes[prereq_id])

    def add_alternative(self, primary_id: str, alt_id: str) -> None:
        if primary_id in self.nodes and alt_id in self.nodes:
            self.nodes[primary_id].alternatives.append(self.nodes[alt_id])

    def evaluate_dependencies(self, evaluations: dict[str, RequirementEvaluation]) -> list[str]:
        """Validates that all prerequisites for MATCH requirements are also satisfied.

        Returns:
            list of warning or inconsistency notes
        """
        notes: list[str] = []
        for req_id, node in self.nodes.items():
            ev = evaluations.get(req_id)
            if ev and ev.status == RequirementStatus.MATCH:
                for prereq in node.prerequisites:
                    prereq_ev = evaluations.get(prereq.requirement_id)
                    if prereq_ev and prereq_ev.status != RequirementStatus.MATCH:
                        notes.append(
                            f"Requirement '{node.title}' satisfied, but prerequisite "
                            f"'{prereq.title}' has status {prereq_ev.status.value}."
                        )
        return notes
