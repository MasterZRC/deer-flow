
### __init__.py  (62 lines)

### cancellation.py  (63 lines)
     11  async def wait_for_task_until(  # noqa: UP047
     29  async def _drain_context_exit(awaitable: Awaitable[bool | None]) -> bool | None:
     51  async def drained_async_context[T](

### checkpoint_cache\__init__.py  (19 lines)

### checkpoint_cache\base.py  (80 lines)
     26  def make_history_key(
     43  def thread_key_stem(key_prefix: str, thread_id: str) -> str:
     49  class CheckpointCacheStats:
     64  class CheckpointHistoryCache(Protocol):
     74  class SyncCheckpointHistoryCache(Protocol):

### checkpoint_cache\memory.py  (79 lines)
     11  def _copy_entry(entry: dict[str, Any]) -> dict[str, Any]:
     19  class MemoryCheckpointHistoryCache:

### checkpoint_cache\provider.py  (102 lines)
     22  def _resolve_redis_url(config: Any) -> str:
     26  def _stable_postgres_identity(postgres_url: str) -> str:
     45  def checkpoint_cache_db_hash(db_config: Any) -> str:
     57  def checkpoint_cache_key_prefix(app_config: AppConfig) -> str:
     65  async def make_checkpoint_cache(

### checkpoint_cache\redis.py  (116 lines)
     26  def _create_client(redis_url: str, *, max_connections: int | None) -> Any:
     37  def _redis_error() -> type[Exception]:
     46  class RedisCheckpointHistoryCache:

### checkpoint_mode.py  (146 lines)
     22  class CheckpointModeMismatchError(RuntimeError):
     26  class CheckpointModeReconfigurationError(RuntimeError):
     34  def frozen_checkpoint_channel_mode() -> CheckpointChannelMode | None:
     39  def freeze_checkpoint_channel_mode(mode: CheckpointChannelMode) -> CheckpointChannelMode:
     48  def frozen_checkpoint_snapshot_frequency() -> int | None:
     53  def freeze_checkpoint_snapshot_frequency(snapshot_frequency: int) -> int:
     72  def resolve_checkpoint_snapshot_frequency(snapshot_frequency: int | None = None) -> int:
     81  def inject_checkpoint_mode(config: dict[str, Any], mode: CheckpointChannelMode) -> None:
     91  def checkpoint_metadata_uses_delta(metadata: Any) -> bool:
    101  def checkpoint_tuple_uses_delta(checkpoint_tuple: Any) -> bool:
    107  def state_snapshot_uses_delta(snapshot: Any) -> bool:
    114  def raise_if_snapshot_incompatible(snapshot: Any, mode: CheckpointChannelMode) -> None:
    126  def raise_if_checkpoint_tuple_incompatible(checkpoint_tuple: Any, mode: CheckpointChannelMode) -> None:
    132  def ensure_checkpoint_mode_compatible(checkpointer: Any, config: dict[str, Any], mode: CheckpointChannelMode) -> None:
    143  async def aensure_checkpoint_mode_compatible(checkpointer: Any, config: dict[str, Any], mode: CheckpointChannelMode) -> None:

### checkpoint_state.py  (209 lines)
     33  def _finish_state_mutation(_state: dict[str, Any]) -> dict[str, Any]:
     37  def build_state_mutation_graph(
     70  def graph_state_schema(graph: Any) -> Any | None:
     83  def graph_writable_channels(graph: Any) -> frozenset[str] | None:
     96  def graph_reducer_channels(graph: Any) -> frozenset[str] | None:
    113  class CheckpointStateAccessor:

### checkpointer\__init__.py  (9 lines)

### checkpointer\async_provider.py  (257 lines)
     40  def _prepare_sqlite_checkpointer_path(raw: str) -> str:
     46  def _prepare_database_sqlite_checkpointer_path(db_config) -> str:
     52  def _build_postgres_pool(conn_string: str, schema: str = ""):
     80  async def _ensure_postgres_schema_with_pool(pool, schema: str) -> None:
     92  def _ensure_postgres_imports():
    113  async def _async_checkpointer(config) -> AsyncIterator[Checkpointer]:
    155  async def _async_checkpointer_from_database(db_config) -> AsyncIterator[Checkpointer]:
    192  async def _select_inner_checkpointer(app_config: AppConfig) -> AsyncIterator[Checkpointer]:
    220  async def make_checkpointer(app_config: AppConfig | None = None) -> AsyncIterator[Checkpointer]:

### checkpointer\cached_saver.py  (328 lines)
     39  def _checkpoint_ref(tup: CheckpointTuple) -> tuple[str, str, str]:
     48  def _channel_writes(tup: CheckpointTuple, channel: str) -> list[PendingWrite]:
     53  class CachedHistorySaver(BaseCheckpointSaver):

### checkpointer\provider.py  (284 lines)
     48  def _ensure_postgres_schema(conn_string: str, schema: str) -> None:
     58  def _resolve_checkpointer_config(app_config: AppConfig) -> CheckpointerConfig:
     82  def _get_checkpointer_config() -> CheckpointerConfig:
    103  def _sync_checkpointer_cm(config: CheckpointerConfig) -> Iterator[Checkpointer]:
    163  def _wrap_sync_if_delta(saver: Checkpointer, app_config: AppConfig) -> Checkpointer:
    195  def get_checkpointer() -> Checkpointer:
    242  def reset_checkpointer() -> None:
    267  def checkpointer_context() -> Iterator[Checkpointer]:

### context_compaction.py  (224 lines)
     23  def _checkpoint_agent_binding(metadata: object) -> tuple[bool, str | None]:
     41  class ContextCompactionDisabled(RuntimeError):
     45  class ContextCompactionFailed(RuntimeError):
     50  class ThreadCompactionResult:
     63  def _create_compaction_middleware(
     81  def _safe_load_agent_config(agent_name: str, user_id: str | None):
    100  async def _aresolve_thread_model_name(
    132  async def compact_thread_context(

### context_keys.py  (33 lines)
     22  def checkpoint_agent_binding_metadata(metadata: object) -> dict[str, str]:

### converters.py  (136 lines)
     21  def langchain_to_openai_message(message: Any) -> dict:
     74  def _infer_finish_reason(message: Any) -> str:
     91  def langchain_to_openai_completion(message: Any) -> dict:
    134  def langchain_messages_to_openai(messages: list) -> list[dict]:

### events\__init__.py  (4 lines)

### events\catalog.py  (119 lines)
     20  def _validate_category(category: str) -> None:
     28  class RunEventDefinition:
     41  class RunEventPattern:

### events\message_identity.py  (59 lines)
     31  def message_identity(message: Mapping[str, Any]) -> str | None:
     52  def attach_message_seq(message: Mapping[str, Any], seq: int) -> dict[str, Any]:

### events\message_seq.py  (52 lines)
     29  async def stamp_messages_with_seq(store: Any, thread_id: str, messages: Sequence[Any]) -> list[Any]:

### events\store\__init__.py  (26 lines)
      5  def make_run_event_store(config=None) -> RunEventStore:

### events\store\base.py  (298 lines)
     23  class IncompleteMessageRunLookupError(RuntimeError):
     27  def normalize_message_ids(message_ids: set[str]) -> set[str]:
     32  def match_ai_message_run_id(event: object, message_ids: set[str]) -> tuple[str, str] | None:
     46  class RunEventStore(abc.ABC):

### events\store\db.py  (566 lines)
     29  class DbRunEventStore(RunEventStore):

### events\store\jsonl.py  (483 lines)
     49  class JsonlRunEventStore(RunEventStore):

### events\store\memory.py  (241 lines)
     17  class MemoryRunEventStore(RunEventStore):

### goal.py  (721 lines)
     67  class GoalWriteConflict(RuntimeError):
     71  def goal_thread_lock(thread_id: str) -> AbstractAsyncContextManager[None]:
     76  class GoalCommand(NamedTuple):
     83  def parse_goal_command(args: str) -> GoalCommand:
     99  def normalize_goal_objective(objective: str) -> str:
    109  def build_goal_state(
    132  def parse_goal_evaluation_response(text: str) -> GoalEvaluation:
    159  def _normalize_evaluation_text(value: object, *, max_chars: int) -> str:
    165  def _normalize_goal_blocker(value: object, *, satisfied: bool) -> GoalBlocker:
    173  def _message_type(message: Any) -> str | None:
    184  def _additional_kwargs(message: Any) -> dict[str, Any]:
    191  def _is_visible_message(message: Any) -> bool:
    197  def has_visible_assistant_evidence(messages: list[Any]) -> bool:
    202  def visible_conversation_signature(messages: list[Any]) -> str:
    217  def _truncate(text: str, limit: int) -> str:
    223  def _shorten_tool_value(value: Any, depth: int = 0) -> Any:
    235  def _tool_calls(message: Any) -> list[dict[str, Any]]:
    242  def _message_field(message: Any, name: str) -> Any:
    249  def _json_inline(value: Any) -> str:
    255  def _one_line(value: Any) -> str:
    260  def _format_tool_call(call: dict[str, Any]) -> str:
    265  def _format_tool_result(message: Any, call_name: str | None) -> str:
    276  def _cap_evidence(lines: list[str]) -> str:
    326  def format_visible_conversation(messages: list[Any]) -> str:
    372  def create_goal_evaluator_model(
    396  def _resolve_environment() -> str | None:
    400  async def evaluate_goal_completion(
    481  def should_continue_goal(goal: GoalState, evaluation: GoalEvaluation, *, no_progress_count: int | None = None) -> bool:
    494  def latest_visible_assistant_signature(messages: list[Any]) -> str:
    513  def compute_goal_progress_key(evaluation: GoalEvaluation, *, evidence_signature: str = "") -> str:
    531  def compute_no_progress_count(goal: GoalState, evaluation: GoalEvaluation, *, evidence_signature: str = "") -> int:
    542  def make_goal_continuation_message(goal: GoalState, evaluation: GoalEvaluation) -> HumanMessage:
    562  async def _call_checkpointer_method(checkpointer: Any, async_name: str, sync_name: str, *args: Any, **kwargs: Any) -> Any:
    579  def _next_channel_version(checkpointer: Any, current_version: Any) -> Any:
    588  async def ensure_thread_checkpoint(checkpointer: Any, thread_id: str) -> None:
    604  def _checkpoint_id_from_tuple(checkpoint_tuple: Any) -> str | None:
    616  async def read_thread_goal(checkpointer: Any, thread_id: str) -> GoalState | None:
    628  async def write_thread_goal(
    693  def attach_goal_evaluation(

### journal.py  (1386 lines)
     63  class _PendingLlmResponse:
     70  def _should_persist_human_input_message(message: BaseMessage) -> bool:
     81  def _coerce_seed_message(message: Any) -> Any:
    104  def _build_history_seed_events(
    182  def build_branch_history_seed_events(
    201  def build_checkpoint_history_seed_events(
    221  class RunJournal(BaseCallbackHandler):

### keyed_lock.py  (147 lines)
     19  class _Entry:
     24  class AsyncKeyedLockTable[KeyT: Hashable]:
     96  class _ThreadEntry:
    101  class KeyedLockTable[KeyT: Hashable]:

### runs\__init__.py  (20 lines)

### runs\manager.py  (2424 lines)
     61  def _generate_worker_id() -> str:
     66  def _resolve_record_user_id(user_id: str | None) -> str | None:
     81  def _cursor_part(value: str | None) -> str | None:
     89  def _is_unique_violation(exc: BaseException) -> bool:
    144  def _is_retryable_persistence_error(exc: BaseException) -> bool:
    175  class PersistenceRetryPolicy:
    185  class RunRecord:
    234  class RunStartOutcome(StrEnum):
    241  class RunStartupError(RuntimeError):
    248  class RunManager:
   2407  class CancelOutcome(StrEnum):
   2419  class ConflictError(Exception):
   2423  class UnsupportedStrategyError(Exception):

### runs\naming.py  (16 lines)
      9  def resolve_root_run_name(config: Mapping[str, Any], assistant_id: str | None) -> str:

### runs\schemas.py  (32 lines)
      6  class ThreadOperationKind(StrEnum):
     17  class RunStatus(StrEnum):
     28  class DisconnectMode(StrEnum):

### runs\store\__init__.py  (4 lines)

### runs\store\base.py  (491 lines)
     22  class EditReplayVisibility:
     28  class LeaseRenewal:
     40  class StatusFinalization:
     47  class RunIdempotencyConflict(RuntimeError):
     55  def normalize_run_created_at_iso(value: str) -> str:
     70  def format_run_cursor_created_at(value: str) -> str:
     80  def parse_run_created_at(value: object) -> datetime:
     94  def run_sort_key(created_at: object, run_id: str) -> tuple[datetime, str]:
     99  def run_is_before_cursor(
    112  class RunStore(abc.ABC):

### runs\store\memory.py  (581 lines)
     21  class MemoryRunStore(RunStore):

### runs\stream_cleanup.py  (111 lines)
      9  class AgentStreamCloseCancelledError(RuntimeError):
     13  def _stream_close_cancelled(exc: asyncio.CancelledError) -> AgentStreamCloseCancelledError:
     19  async def close_agent_stream(stream: Any) -> None:

### runs\worker.py  (3230 lines)
    109  def _log_cancelled_stream_close_failure(
    142  def _create_contextless_task(coro: Coroutine[Any, Any, Any]) -> asyncio.Task[Any]:
    147  def _schedule_terminal_cycle_collection() -> None:
    198  def _remove_callback(config: dict[str, Any], handler: Any) -> None:
    211  def _release_run_scoped_references(
    257  def _checkpoint_thread_lock(thread_id: str) -> AbstractAsyncContextManager[None]:
    266  def _project_background_tasks(task_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    279  async def _persist_delivery_receipt(
    331  def _empty_delivery_content() -> dict[str, Any]:
    335  def _presented_path_covers_output(presented_path: str, produced_path: str) -> bool:
    340  def _delivery_content_with_outputs(
    365  def _delivery_error(content: dict[str, Any]) -> str | None:
    372  def _workspace_excluded_dir_names(app_config: AppConfig | None) -> frozenset[str]:
    390  async def _produced_output_paths(
    414  class _LargeFileToolChunkBatcher:
    559  def _build_runtime_context(
    612  def _pin_admission_project_context(config: dict, runtime_context: dict[str, Any]) -> None:
    630  class RunContext:
    655  def _install_runtime_context(config: dict, runtime_context: dict[str, Any]) -> None:
    681  def _compute_agent_factory_supports_app_config(agent_factory: Any) -> bool:
    689  def _cached_agent_factory_supports_app_config(agent_factory: Any) -> bool:
    693  def _agent_factory_supports_app_config(agent_factory: Any) -> bool:
    701  def _agent_graph(agent_result: Any) -> Any:
    712  def _assembled_model_name(agent_result: Any) -> str | None:
    723  class _SubagentEventBuffer:
    812  def _bind_trace_id(config: dict[str, Any], runtime_ctx: dict[str, Any]) -> str:
    838  def _defer_finalization_interrupt(
    851  async def _await_task_stop_after_host_cancellation(
    868  async def run_agent(
   1872  class _GoalCompletionCandidate:
   1877  async def _clear_completed_goal(
   1938  def _checkpoint_id(checkpoint_tuple: Any) -> str | None:
   1950  def _goal_instance_matches(left: GoalState | None, right: GoalState | None) -> bool:
   1959  async def _materialized_checkpoint_messages(accessor: CheckpointStateAccessor, thread_id: str) -> list[Any]:
   1972  def _read_checkpoint_goal(checkpoint_tuple: Any) -> GoalState | None:
   1979  def _has_durable_goal_turn_receipt(checkpoint_tuple: Any, messages: list[Any]) -> bool:
   1999  def _ends_on_human_input_request(messages: list[Any]) -> bool:
   2017  def _stand_down_reason(goal: GoalState, evaluation: GoalEvaluation, no_progress_count: int) -> str | None:
   2031  async def _persist_goal_evaluation(
   2089  async def _reread_goal_and_checkpoint(checkpointer: Any, thread_id: str) -> tuple[GoalState | None, Any]:
   2101  async def _prepare_goal_continuation_input(
   2310  def _is_edit_replay_run(record: RunRecord) -> bool:
   2315  async def _ensure_finalizing_before_edit_failure(run_manager: RunManager, record: RunRecord) -> None:
   2320  async def _publish_restored_checkpoint_values(
   2336  class RollbackPoint:
   2352  async def _capture_rollback_point(
   2386  def _complete_state_replacement_values(
   2416  async def _linearize_delta_checkpoint_resume(
   2506  async def _rollback_to_pre_run_checkpoint(
   2618  def _new_checkpoint_marker() -> dict[str, str]:
   2623  def _bump_channel_version(checkpointer: Any, current_version: Any) -> Any:
   2663  def _checkpoint_identity(ckpt_tuple: Any | None, checkpoint: dict[str, Any]) -> str | None:
   2674  def _checkpoint_namespace(ckpt_tuple: Any | None) -> str:
   2681  def _graph_input_messages(graph_input: Any | None) -> list[Any]:
   2692  def _title_generation_state(channel_values: dict[str, Any], graph_input: Any | None) -> dict[str, Any]:
   2702  def valid_duration_entry(run_id: Any, duration_seconds: Any) -> bool:
   2710  def valid_run_message_id_entry(message_id: Any, run_id: Any) -> bool:
   2715  async def persist_run_history_metadata(
   2802  async def persist_run_durations(
   2816  async def _persist_run_duration(
   2831  async def _ensure_interrupted_title(*, checkpointer: Any, thread_id: str, app_config: AppConfig | None, graph_input: Any | None = None) -> str | None:
   2916  def _lg_mode_to_sse_event(mode: str) -> str:
   2928  def _error_fallback_message_from_metadata(metadata: dict[str, Any], content: Any) -> str:
   2940  def _message_id(obj: Any) -> str | None:
   2952  def _try_extract_from_message(obj: Any, pre_existing_ids: set[str] | None = None) -> str | None:
   2978  def _extract_llm_error_fallback_message(value: Any, pre_existing_ids: set[str] | None = None) -> str | None:
   3037  def _collect_pre_existing_message_ids(values: Any) -> set[str]:
   3047  def _unpack_stream_item(
   3080  def _compose_sse_event(sse_event: str, namespace: tuple[str, ...]) -> str:
   3098  def _NO_FEED_WRITES() -> int:  # noqa: N802 鈥?a callable constant, not a class
   3103  class _MessageSeqStamper:
   3178  def _build_seq_stamper(event_store: Any, thread_id: str, journal: Any) -> _MessageSeqStamper:
   3193  async def _publish_stream_item(

### secret_context.py  (243 lines)
     39  class LegacyRunMetadataSecretError(ValueError):
     43  def validate_run_metadata_secrets(metadata: Any) -> None:
     49  def redact_metadata_secrets(metadata: Any) -> Any:
     56  def _string_pairs(raw: Any) -> dict[str, str]:
     62  def extract_request_secrets(context: Any) -> dict[str, str]:
     73  def read_active_secrets(context: Any) -> dict[str, str]:
     81  def write_slash_skill_source_path(context: Any, path: str, *, owner_token: str) -> None:
     92  def read_slash_skill_source_path(context: Any, *, owner_token: str) -> str | None:
    106  def write_slash_skill_source_paths(context: Any, paths: tuple[str, ...], *, owner_token: str) -> None:
    114  def read_slash_skill_source_paths(context: Any, *, owner_token: str) -> tuple[str, ...]:
    139  def write_skill_entry_decisions(context: Any, decisions: dict[str, bool], *, owner_token: str) -> None:
    145  def read_skill_entry_decisions(context: Any, *, owner_token: str) -> dict[str, bool] | None:
    199  def redact_secret_context_keys(context: Any) -> Any:
    212  def redact_config_secrets(config: Any) -> Any:

### serialization.py  (148 lines)
     16  def serialize_lc_object(obj: Any) -> Any:
     59  def serialize_channel_values(channel_values: dict[str, Any]) -> dict[str, Any]:
     74  def strip_data_url_image_blocks(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    112  def serialize_channel_values_for_api(channel_values: dict[str, Any]) -> dict[str, Any]:
    126  def serialize_messages_tuple(obj: Any) -> Any:
    134  def serialize(obj: Any, *, mode: str = "") -> Any:

### store\__init__.py  (31 lines)

### store\_sqlite_utils.py  (36 lines)
     10  def resolve_sqlite_conn_str(raw: str) -> str:
     30  def ensure_sqlite_parent_dir(conn_str: str) -> None:

### store\async_provider.py  (125 lines)
     42  async def _ensure_postgres_schema(conn_string: str, schema: str) -> None:
     53  async def _async_store(config) -> AsyncIterator[BaseStore]:
    107  async def make_store(app_config: AppConfig | None = None) -> AsyncIterator[BaseStore]:

### store\provider.py  (224 lines)
     49  def _ensure_postgres_schema(conn_string: str, schema: str) -> None:
     54  def _resolve_store_config(app_config: AppConfig) -> CheckpointerConfig:
     78  def _get_store_config() -> CheckpointerConfig:
     99  def _sync_store_cm(config) -> Iterator[BaseStore]:
    156  def get_store() -> BaseStore:
    186  def reset_store() -> None:
    209  def store_context() -> Iterator[BaseStore]:

### stream_bridge\__init__.py  (31 lines)

### stream_bridge\async_provider.py  (102 lines)
     32  def _resolve_config(app_config: AppConfig | None) -> StreamBridgeConfig | None:
     45  def _resolve_redis_url(config: StreamBridgeConfig) -> str:
     50  async def make_stream_bridge(app_config: AppConfig | None = None) -> AsyncIterator[StreamBridge]:

### stream_bridge\base.py  (115 lines)
     20  class StreamEvent:
     37  class StreamGap:
     57  class StreamBridge(abc.ABC):

### stream_bridge\memory.py  (192 lines)
     20  class _RunStream:
     27  class MemoryStreamBridge(StreamBridge):

### stream_bridge\redis.py  (384 lines)
     51  class RedisStreamBridge(StreamBridge):

### stream_modes.py  (47 lines)
     20  class UnsupportedStreamModeError(ValueError):
     28  def normalize_stream_modes(raw: list[str] | str | None) -> list[str]:
     43  def to_langgraph_stream_modes(raw: list[str] | str | None) -> list[str]:

### user_context.py  (295 lines)
     43  class CurrentUser(Protocol):
     56  def set_current_user(user: CurrentUser) -> Token[CurrentUser | None]:
     66  def reset_current_user(token: Token[CurrentUser | None]) -> None:
     71  def get_current_user() -> CurrentUser | None:
     80  def require_current_user() -> CurrentUser:
    101  def get_effective_user_id() -> str:
    113  def _storage_user_id_from_auth_identity(identity: object | None) -> str | None:
    127  def _user_id_from_auth_user(user: object | None) -> str | None:
    135  def _user_id_from_langgraph_config(config: object | None) -> str | None:
    148  def resolve_config_user_id(config: object | None) -> str:
    178  def resolve_runtime_user_id(runtime: object | None) -> str:
    221  def _user_id_from_langgraph_auth() -> str | None:
    249  class _AutoSentinel:
    266  def resolve_user_id(
