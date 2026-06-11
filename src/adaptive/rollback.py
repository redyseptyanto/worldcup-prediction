"""Rollback helpers."""

from __future__ import annotations

from src.adaptive.state_machine import MatchStateMachine
from src.adaptive.snapshotter import SnapshotManager


class RollbackManager:
    """Restore match state from an earlier snapshot."""

    def __init__(self, snapshot_manager: SnapshotManager, state_machine: MatchStateMachine) -> None:
        self.snapshot_manager = snapshot_manager
        self.state_machine = state_machine

    def rollback_to(self, snapshot_id: str) -> dict[str, str]:
        state = self.snapshot_manager.read_snapshot(snapshot_id, "state.json")
        if state is None:
            raise FileNotFoundError(f"Snapshot {snapshot_id} does not exist.")
        self.state_machine.reset(snapshot_state=state)
        return {"rolled_back_to": snapshot_id}
