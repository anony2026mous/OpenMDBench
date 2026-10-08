"""RF-05 deterministic command queue and lifecycle authority."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from openmdbench.core.rng import configuration_hash
from openmdbench.schemas.platform import (
    ActionBatch,
    ActionReceipt,
    CommandResult,
    CommandStatus,
    DiscreteAction,
    PersistentCommand,
    ReceiptStatus,
    StableErrorCode,
)


class CommandRejectedError(ValueError):
    def __init__(self, error_code: StableErrorCode, message: str) -> None:
        self.error_code = error_code
        super().__init__(f"{error_code.value}: {message}")


class CommandConflictError(CommandRejectedError):
    def __init__(self, message: str = "command_id was reused with different content") -> None:
        super().__init__(StableErrorCode.ACTION_DUPLICATE, message)


@dataclass(frozen=True, slots=True)
class TickActions:
    tick: int
    persistent_commands: tuple[PersistentCommand, ...]
    discrete_actions: tuple[DiscreteAction, ...]
    fallbacks: tuple[tuple[str, Literal["safe_hold", "return_to_base"]], ...] = ()


@dataclass(slots=True)
class _PendingBatch:
    batch: ActionBatch
    scheduled_tick: int


class CommandQueue:
    """Validate on receipt and apply commands only at deterministic tick boundaries."""

    def __init__(
        self,
        session_id: str,
        *,
        entity_sides: dict[str, str],
        fallback: Literal["safe_hold", "return_to_base"] = "safe_hold",
    ) -> None:
        self.session_id = session_id
        self._entity_sides = dict(entity_sides)
        self._fallback = fallback
        self._pending: list[_PendingBatch] = []
        self._active: dict[tuple[str, str], PersistentCommand] = {}
        self._receipts: dict[str, ActionReceipt] = {}
        self._batch_hashes: dict[str, str] = {}
        self._results: dict[str, CommandResult] = {}
        self._consumed_actions: set[str] = set()

    @property
    def pending_count(self) -> int:
        return len(self._pending)

    def submit(self, batch: ActionBatch, current_tick: int, *, actor_side: str) -> ActionReceipt:
        owned_batch = ActionBatch.model_validate(batch.model_dump(mode="json"))
        digest = configuration_hash(owned_batch.model_dump(mode="json"))
        if batch.command_id in self._batch_hashes:
            if self._batch_hashes[batch.command_id] != digest:
                raise CommandConflictError()
            return self._receipts[batch.command_id]
        if owned_batch.session_id != self.session_id:
            raise CommandRejectedError(
                StableErrorCode.ACTION_INVALID, "batch belongs to another session"
            )
        if (
            owned_batch.based_on_tick > current_tick
            or owned_batch.valid_until_tick < current_tick + 1
        ):
            raise CommandRejectedError(StableErrorCode.ACTION_STALE, "batch tick is stale")
        children = (*owned_batch.persistent_commands, *owned_batch.discrete_actions)
        for item in children:
            side = self._entity_sides.get(item.entity_id)
            if side is None:
                raise CommandRejectedError(
                    StableErrorCode.COMMAND_REJECTED,
                    f"unknown entity: {item.entity_id}",
                )
            if side != actor_side:
                raise CommandRejectedError(
                    StableErrorCode.ACTION_UNAUTHORIZED,
                    f"entity is not controlled by {actor_side}",
                )
        scheduled_tick = current_tick + 1
        receipt = ActionReceipt(
            schema_version="1.0",
            session_id=self.session_id,
            command_id=owned_batch.command_id,
            status=ReceiptStatus.QUEUED,
            received_at_tick=current_tick,
            scheduled_for_tick=scheduled_tick,
        )
        self._batch_hashes[owned_batch.command_id] = digest
        self._receipts[owned_batch.command_id] = receipt
        self._pending.append(_PendingBatch(owned_batch, scheduled_tick))
        self._pending.sort(key=lambda item: (item.scheduled_tick, item.batch.command_id))
        identifiers = tuple(item.command_id for item in owned_batch.persistent_commands) + tuple(
            item.action_id for item in owned_batch.discrete_actions
        )
        for identifier in identifiers:
            self._results[identifier] = self._result(identifier, CommandStatus.QUEUED)
        return receipt

    def apply_tick(
        self,
        tick: int,
        *,
        available_entities: frozenset[str] | None = None,
        connected_entities: frozenset[str] | None = None,
    ) -> TickActions:
        available = (
            frozenset(self._entity_sides) if available_entities is None else available_entities
        )
        connected = (
            frozenset(self._entity_sides) if connected_entities is None else connected_entities
        )
        fallbacks: list[tuple[str, Literal["safe_hold", "return_to_base"]]] = []
        for key, command in tuple(self._active.items()):
            if command.entity_id not in available:
                self._results[command.command_id] = self._result(
                    command.command_id,
                    CommandStatus.FAILED,
                    completed_tick=tick,
                    error_code=StableErrorCode.COMMAND_REJECTED,
                )
                del self._active[key]
                fallbacks.append((command.entity_id, self._fallback))
            elif tick > command.valid_until_tick:
                self._results[command.command_id] = self._result(
                    command.command_id,
                    CommandStatus.EXPIRED,
                    completed_tick=tick,
                    error_code=StableErrorCode.COMMAND_EXPIRED,
                )
                del self._active[key]

        ready = [item for item in self._pending if item.scheduled_tick <= tick]
        self._pending = [item for item in self._pending if item.scheduled_tick > tick]
        deferred: list[_PendingBatch] = []
        discrete: list[DiscreteAction] = []
        for pending in ready:
            batch = pending.batch
            for command in sorted(
                batch.persistent_commands,
                key=lambda item: (item.entity_id, item.command_type, item.command_id),
            ):
                if tick > command.valid_until_tick:
                    self._expire(command.command_id, tick)
                    continue
                if command.entity_id not in available:
                    self._reject(command.command_id, tick)
                    fallbacks.append((command.entity_id, self._fallback))
                    continue
                if command.entity_id not in connected:
                    deferred.append(
                        _PendingBatch(
                            batch.model_copy(
                                update={"persistent_commands": (command,), "discrete_actions": ()}
                            ),
                            tick + 1,
                        )
                    )
                    continue
                key = (command.entity_id, command.command_type)
                previous = self._active.get(key)
                if previous is not None and previous.command_id != command.command_id:
                    self._results[previous.command_id] = self._result(
                        previous.command_id, CommandStatus.REPLACED, completed_tick=tick
                    )
                self._active[key] = command
                self._results[command.command_id] = self._result(
                    command.command_id, CommandStatus.ACTIVE, applied_tick=tick
                )
            for action in sorted(batch.discrete_actions, key=lambda item: item.action_id):
                if action.action_id in self._consumed_actions:
                    continue
                if tick > action.valid_until_tick:
                    self._expire(action.action_id, tick)
                    continue
                if action.entity_id not in available:
                    self._reject(action.action_id, tick)
                    continue
                if action.entity_id not in connected:
                    deferred.append(
                        _PendingBatch(
                            batch.model_copy(
                                update={"persistent_commands": (), "discrete_actions": (action,)}
                            ),
                            tick + 1,
                        )
                    )
                    continue
                self._consumed_actions.add(action.action_id)
                discrete.append(action)
                self._results[action.action_id] = self._result(
                    action.action_id,
                    CommandStatus.APPLIED,
                    applied_tick=tick,
                )
        self._pending.extend(deferred)
        self._pending.sort(key=lambda item: (item.scheduled_tick, item.batch.command_id))
        active = tuple(
            item.model_copy(deep=True)
            for item in sorted(
                (command for command in self._active.values() if command.entity_id in connected),
                key=lambda item: (item.entity_id, item.command_type, item.command_id),
            )
        )
        return TickActions(
            tick,
            active,
            tuple(discrete),
            tuple(sorted(set(fallbacks))),
        )

    def cancel(self, command_id: str, tick: int) -> CommandResult:
        for key, command in tuple(self._active.items()):
            if command.command_id == command_id:
                del self._active[key]
                self._results[command_id] = self._result(
                    command_id, CommandStatus.CANCELLED, completed_tick=tick
                )
                return self._results[command_id]
        raise KeyError("command not found or not active")

    def complete_action(
        self, action_id: str, tick: int, *, executed: bool, details: dict[str, object] | None = None
    ) -> CommandResult:
        current = self.result(action_id)
        if current.status is not CommandStatus.APPLIED:
            raise ValueError("discrete action is not awaiting a business result")
        status = CommandStatus.EXECUTED if executed else CommandStatus.REJECTED
        self._results[action_id] = CommandResult(
            schema_version="1.0",
            session_id=self.session_id,
            command_id=action_id,
            status=status,
            applied_tick=current.applied_tick,
            completed_tick=tick,
            error_code=None if executed else StableErrorCode.COMMAND_REJECTED,
            details=details or {},
        )
        return self._results[action_id]

    def result(self, command_id: str) -> CommandResult:
        try:
            return self._results[command_id].model_copy(deep=True)
        except KeyError as error:
            raise KeyError("command not found") from error

    def _expire(self, identifier: str, tick: int) -> None:
        self._results[identifier] = self._result(
            identifier,
            CommandStatus.EXPIRED,
            completed_tick=tick,
            error_code=StableErrorCode.COMMAND_EXPIRED,
        )

    def _reject(self, identifier: str, tick: int) -> None:
        self._results[identifier] = self._result(
            identifier,
            CommandStatus.REJECTED,
            completed_tick=tick,
            error_code=StableErrorCode.COMMAND_REJECTED,
        )

    def _result(
        self,
        identifier: str,
        status: CommandStatus,
        *,
        applied_tick: int | None = None,
        completed_tick: int | None = None,
        error_code: StableErrorCode | None = None,
    ) -> CommandResult:
        return CommandResult(
            schema_version="1.0",
            session_id=self.session_id,
            command_id=identifier,
            status=status,
            applied_tick=applied_tick,
            completed_tick=completed_tick,
            error_code=error_code,
        )
