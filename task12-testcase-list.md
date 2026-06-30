# 任务12新增 UT 用例清单

## 1. 基线覆盖摘要

当前 `tests/ut/distributed/ascend_store/` 已有 208 个可收集并通过的隔离 UT。现有覆盖主要集中在基础数据结构、普通 save/load、基础 scheduler 新请求、基础 worker lookup、backend 方法包装等路径。

仍需补齐 `task12.md` 指定的关键缺口：

- `config_data`: 多层 `prepare_value_layer`、多分区 PP 边界、`ReqMeta.from_request_tracker` 组合场景。
- `kv_transfer`: 非零 `tp_rank` key 轮转、线程 `run()`、接收失败容错。
- `pool_scheduler`: `scheduled_cached_reqs` decode/chunked、preempted resumed、`LookupKeyClient` 异常。
- `pool_worker`: `register_kv_caches` 完整初始化、MLA/sparse、同步 load 细节、layerwise 生成器、`lookup_scheduler` gate。
- `ascend_store_connector`: `LookupKeyServer`、`requires_piecewise_for_cudagraph`、`kv_both`、`use_layerwise=True` 流程。
- `backend`: `MemcacheBackend.set_device`、`MmcDirect`、Mooncake fabric memory、Backend init。

## 2. `config_data` 新增用例（目标 >= 15）

目标文件：`tests/ut/distributed/ascend_store/test_config_data.py`

建议新增到现有类：

### TestChunkedTokenDatabase

1. `test_prepare_value_layer_uses_second_layer_base_addr`
   - `layer_id=1`，`group_block_len` 长度为 2。
   - 断言使用 `group_addrs[layer_id * length]` 作为基址。

2. `test_prepare_value_layer_uses_explicit_stride`
   - 设置 `group_block_stride={0: [...]}`。
   - 断言 addr 使用 stride 而非 block_len。

3. `test_prepare_value_layer_without_stride_uses_block_len`
   - 不设置 stride。
   - 断言 addr 使用 `group_block_len[i]`。

4. `test_prepare_value_layer_selects_non_first_block_id`
   - `start >= block_size`。
   - 断言 `block_ids[start // block_size]` 被选中。

5. `test_prepare_value_layer_partial_token_size_for_each_cache`
   - `end - start` 小于 block size。
   - 断言每个 size 按比例计算。

6. `test_decode_adaptor_prefill_pp_uses_group_num_layers`
   - 设置 `group_num_layers["kv"][0]`。
   - 断言 `caches_per_layer = len(addr_list) // group_num_layers`。

7. `test_decode_adaptor_prefill_pp_fallback_caches_per_layer_when_no_group_num_layers`
   - 不设置 group_num_layers。
   - 断言 fallback 为 2。

8. `test_decode_adaptor_prefill_pp_last_partition_takes_remainder`
   - addr/size 数量不能被 partitions 完整切分。
   - 断言最后一个 partition 包含剩余项。

9. `test_decode_adaptor_prefill_pp_replaces_only_first_pp_rank`
   - key 中包含两个 `@pp_rank:0`。
   - 断言只替换第一个。

10. `test_decode_adaptor_prefill_pp_multiple_keys_each_partitioned`
    - 两个 key，各自拆成多个 PP key。
    - 断言输出 key/addr/size 顺序稳定。

### TestReqMeta

11. `test_from_request_tracker_preserves_is_last_chunk_true`
    - `is_last_chunk=True`。
    - 断言 `ReqMeta.is_last_chunk is True`。

12. `test_from_request_tracker_preserves_is_last_chunk_false`
    - `is_last_chunk=False`。
    - 断言 `ReqMeta.is_last_chunk is False`。

13. `test_from_request_tracker_bytes_hashes_no_discard_partial`
    - `block_hashes=[b"..."]`，`discard_partial_chunks=False`。
    - 断言非对齐 token_len 可保存，bytes hashes 透传。

14. `test_from_request_tracker_skip_save_with_load_spec_keeps_load`
    - `skip_save=True` 且 `load_spec.can_load=True`。
    - 断言返回 `ReqMeta`，`can_save=False`，`load_spec` 保留。

15. `test_from_request_tracker_kv_cache_group_families_combination`
    - 传入多 group family。
    - 断言 `kv_cache_families_by_group` 透传。

16. `test_from_request_tracker_token_ids_are_preserved`
    - tracker 带 `token_ids`。
    - 断言 `ReqMeta.token_ids` 与 tracker 一致。

## 3. `kv_transfer` 新增用例（目标 >= 12）

目标文件：`tests/ut/distributed/ascend_store/test_kv_transfer.py`

建议复用/扩展现有 `FakeStore`、`FakeTokenDatabase`。

### TestKVTransferThread

1. `test_run_sets_ready_event_and_handles_request`
   - 使用 fake queue 或短生命周期子类。
   - 断言 `ready_event.set()` 和 `_handle_request()` 被调用。

2. `test_run_ignores_none_request_and_continues`
   - 队列返回 `None` 后再返回可控退出请求。
   - 断言不调用 `_handle_request(None)`。

3. `test_run_handles_request_exception_without_hanging`
   - `_handle_request` 抛异常后设置退出。
   - 断言线程不 hang，异常被 run 循环吞掉或按现有逻辑处理。

### TestKVCacheStoreRecvingThread

4. `test_handle_request_rotates_keys_for_nonzero_tp_rank`
   - `tp_rank=1`，至少 3 个 key。
   - 断言 `m_store.get` 收到轮转后的 key/addr/size 顺序。

5. `test_handle_request_records_partial_failed_blocks`
   - `m_store.get` 返回 `[0, 1, 0]`。
   - 断言只记录失败 block。

6. `test_handle_request_records_all_blocks_when_get_returns_none`
   - `m_store.get` 返回 `None`。
   - 断言单 group 下所有 block id 进入 `_invalid_block_ids`。

7. `test_handle_request_hybrid_failure_does_not_update_invalid_blocks`
   - `block_ids_by_group` 长度大于 1。
   - 断言失败时 `_invalid_block_ids` 不更新。

8. `test_handle_request_no_keys_marks_finished`
   - token/hash/mask 组合使 key_list 为空。
   - 断言 `set_finished_request`、`task_done()`。

### TestKVCacheStoreLayerRecvingThread

9. `test_layer_recv_rotates_keys_for_nonzero_tp_rank`
   - `tp_rank=1`，多个 layer key。
   - 断言 `m_store.get` 参数顺序轮转。

10. `test_layer_recv_records_partial_failed_blocks`
    - 返回 `[1, 0]`。
    - 断言失败 block id 被记录。

11. `test_layer_recv_records_all_blocks_when_get_returns_none`
    - 返回 `None`。
    - 断言全部 block id 被记录。

12. `test_layer_recv_sets_get_event_after_success`
    - 断言 `get_event.set()`。

13. `test_layer_recv_task_done_after_failure`
    - 模拟 get 返回失败码。
    - 断言 `request_queue.task_done()`。

### TestKVCacheStoreLayerSendingThread

14. `test_layer_send_put_exception_still_task_done`
    - `m_store.put` 抛异常。
    - 若当前代码未容错，记录为需修复点；修复后断言 `task_done()`。

## 4. `pool_scheduler` 新增用例（目标 >= 10）

目标文件：`tests/ut/distributed/ascend_store/test_pool_scheduler.py`

### TestKVPoolSchedulerBuildMeta

1. `test_build_connector_meta_cached_decode_request_updates_tracker`
   - 已有 `_request_trackers` 和 `_unfinished_requests`。
   - `scheduled_cached_reqs.new_block_ids` 非空。
   - 断言 token_len 增加、block ids 更新、metadata 生成。

2. `test_build_connector_meta_cached_chunked_request_generates_meta_at_boundary`
   - chunked 请求跨 cache_transfer_granularity。
   - 断言生成 `ReqMeta` 且 `can_save=True`。

3. `test_build_connector_meta_cached_request_skips_after_prompt_computed`
   - `num_computed_token >= len(prompt_token_ids)`。
   - 断言不新增 request metadata。

4. `test_build_connector_meta_cached_request_missing_unfinished_raises`
   - `_unfinished_requests` 缺失。
   - 断言抛 `ValueError`。

5. `test_build_connector_meta_preempted_resumed_rebuilds_tracker`
   - `_preempted_req_ids` 包含 req_id。
   - cached req 恢复。
   - 断言 `_preempted_req_ids` 清理、tracker 重建。

6. `test_build_connector_meta_preempted_resumed_consumes_load_spec`
   - resumed 请求带 `load_specs[req_id]`。
   - 断言 `load_specs` 被 pop，metadata 带 load_spec。

7. `test_build_connector_meta_cached_request_with_grouped_block_ids`
   - `new_block_ids` 为 tuple/list[list]。
   - 断言 group block ids 规范化正确。

8. `test_build_connector_meta_cached_request_last_chunk_flag`
   - token_len 达到 prompt 最后 chunk。
   - 断言 `ReqMeta.is_last_chunk=True`。

### TestLookupKeyClient

9. `test_lookup_send_multipart_timeout_raises_or_returns_zero_contract`
   - `socket.send_multipart` 抛异常。
   - 按当前/修复后契约断言。

10. `test_lookup_recv_timeout_raises_or_returns_zero_contract`
    - `socket.recv` 抛异常。
    - 按当前/修复后契约断言。

11. `test_lookup_encodes_group_ids_and_hash_frames`
    - 多 group ids、多 block hashes。
    - 断言 frame 顺序：token_len bytes、group frame、hash frames。

## 5. `pool_worker` 新增用例（目标 >= 15）

目标文件：`tests/ut/distributed/ascend_store/test_pool_worker.py`

### TestKVPoolWorkerRegisterAndTransfer

1. `test_register_kv_caches_registers_all_unique_storage_regions`
   - 多层、多 cache 共享/不同 storage。
   - 断言 `register_buffer` ptr/length 去重合并。

2. `test_register_kv_caches_sets_token_database_group_buffers`
   - 断言 `set_group_buffers` 的 base addr、block_len、stride、families、num_layers。

3. `test_register_kv_caches_mla_metadata`
   - `use_mla=True`。
   - 断言 group metadata 中 head/tp 行为符合 MLA。

4. `test_register_kv_caches_sparse_metadata`
   - `hf_text_config.index_topk` 存在。
   - 断言 sparse 分支 metadata。

5. `test_register_kv_caches_layerwise_creates_send_and_recv_threads`
   - `use_layerwise=True`，`kv_role=kv_producer`。
   - patch thread 类，断言构造参数和 `start()`。

6. `test_register_kv_caches_layerwise_consumer_creates_recv_thread_only`
   - `kv_role=kv_consumer`。
   - 断言不创建 send thread。

7. `test_register_kv_caches_non_layerwise_load_async_false_no_recv_thread`
   - `load_async=False`。
   - 断言无普通 recv thread。

8. `test_start_load_kv_sync_rotates_for_nonzero_tp_rank`
   - `tp_rank=1`。
   - 断言 backend `get` key/addr/size 顺序轮转。

9. `test_start_load_kv_sync_records_failed_blocks`
   - backend get 返回部分失败。
   - 断言 `_invalid_block_ids`。

10. `test_start_load_kv_sync_get_none_records_blocks`
    - backend get 返回 `None`。
    - 断言 block id 记录。

11. `test_start_load_kv_sync_hybrid_failure_does_not_update_invalid_blocks`
    - 多 group 请求失败。
    - 断言 invalid set 不更新。

12. `test_start_load_kv_adjusts_token_len_for_last_partial_chunk`
    - `kvpool_cached_tokens == token_len - 1` 且非 granularity 对齐。
    - 断言 get token_len 修正。

13. `test_wait_for_layer_load_final_layer_consumes_ret_mask`
    - layerwise retriever 最后一层返回 mask。
    - 断言生成器推进和 sum/item 路径。

14. `test_save_kv_layer_initializes_storers_on_first_layer`
    - `current_layer=0`。
    - 断言 event、`add_stored_request`、storer 列表初始化。

15. `test_save_kv_layer_advances_all_storers`
    - 多个 storer。
    - 断言每个 next，被 `current_layer` 递增。

16. `test_retrieve_layer_yields_each_layer_and_final_mask`
    - 有 keys。
    - 断言逐层 `kv_recv_thread.add_request`，最后 yield mask。

17. `test_retrieve_layer_without_keys_yields_num_layers_then_mask`
    - 无 keys。
    - 断言仍 yield `num_layers` 次再返回 mask。

18. `test_store_layer_yields_layer_metadata_with_hashes`
    - 有 keys。
    - 断言 `LayerMultiBlockReqMeta` 字段，包括 layer_id、starts、ends、token_ids、block_hashes。

19. `test_store_layer_without_keys_yields_num_layers`
    - 无 keys。
    - 断言按 `num_layers` yield。

20. `test_lookup_scheduler_gate_filters_non_c1_groups`
    - hybrid families 包含非 c1。
    - 断言 lookup gate group 过滤。

## 6. `ascend_store_connector` 新增用例（目标 >= 10）

目标文件：`tests/ut/distributed/ascend_store/test_ascend_store_connector.py`

### TestLookupKeyServer（新增测试类）

1. `test_lookup_key_server_starts_thread`
   - patch `threading.Thread`。
   - 断言 daemon=True、target 可调用、`start()`。

2. `test_lookup_key_server_processes_single_request`
   - fake socket 返回 multipart。
   - fake decoder 返回 group ids 和 hashes。
   - 断言调用 `pool_worker.lookup_scheduler(...)`。

3. `test_lookup_key_server_sends_big_endian_response`
   - `lookup_scheduler` 返回 int。
   - 断言 `socket.send(result.to_bytes(4, "big"))`。

4. `test_lookup_key_server_passes_use_layerwise_true`
   - `use_layerwise=True`。
   - 断言传入 worker。

5. `test_lookup_key_server_close_closes_socket`
   - 断言 `socket.close(linger=0)`。

### TestAscendStoreConnector

6. `test_requires_piecewise_for_cudagraph_true`
   - `extra_config={"use_layerwise": True}`。
   - 断言 True。

7. `test_requires_piecewise_for_cudagraph_default_false`
   - `extra_config={}`。
   - 断言 False。

8. `test_wait_for_save_kv_both_delegates_to_worker`
   - `kv_role=kv_both`。
   - 断言调用 worker `wait_for_save`。

9. `test_save_kv_layer_kv_both_layerwise_delegates`
   - `use_layerwise=True`，`kv_role=kv_both`。
   - 断言调用 worker `save_kv_layer`。

10. `test_start_load_kv_layerwise_delegates_metadata`
    - `use_layerwise=True`。
    - 断言 metadata 从 connector 传给 worker。

11. `test_wait_for_layer_load_layerwise_delegates`
    - `use_layerwise=True`。
    - 断言调用 worker `wait_for_layer_load`。

12. `test_wait_for_save_layerwise_noop`
    - `use_layerwise=True`。
    - 断言不调用 worker `wait_for_save`。

13. `test_get_finished_kv_both_returns_worker_results`
    - worker 返回 sending/recving。
    - 断言 connector 原样返回。

## 7. `backend` 新增用例（目标 >= 8）

目标文件：`tests/ut/distributed/ascend_store/test_backend.py`

### TestMemcacheBackendMethods

1. `test_set_device_uses_local_rank`
   - patch `get_world_group().local_rank=2`。
   - 断言 `torch.device("npu:2")` 和 `torch.npu.set_device`。

2. `test_mmc_direct_enum_values`
   - 断言 `COPY_L2G=0`、`COPY_G2L=1`、`COPY_G2H=2`、`COPY_H2G=3`。

3. `test_get_uses_copy_g2l_enum`
   - 断言 `batch_get_into_layers(..., MmcDirect.COPY_G2L.value)`。

4. `test_put_uses_copy_l2g_enum`
   - 断言 `batch_put_from_layers(..., MmcDirect.COPY_L2G.value)`。

5. `test_init_non_a2_lazy_init_defers_store_setup`
   - `lazy_init=True` 且非 A2。
   - 断言 store 未初始化。

6. `test_init_a2_ignores_lazy_init_and_initializes_store`
   - `get_ascend_device_type=A2`。
   - 断言 `_setup_store` 调用。

### TestMooncakeBackendMethods

7. `test_init_fabric_memory_sets_local_buffer_zero`
   - `ASCEND_ENABLE_USE_FABRIC_MEM=1`。
   - 断言 store.setup `local_buffer_size=0`。

8. `test_register_buffer_skips_transfer_engine_for_fabric_memory`
   - `_use_fabric_mem=True`。
   - 断言 `global_te.register_buffer` 不调用。

9. `test_lazy_init_fabric_memory_put_initializes_store`
   - `lazy_init=True` 且 fabric memory。
   - 断言 init 延迟到 `put()`。

10. `test_init_non_fabric_uses_transfer_engine`
    - `_use_fabric_mem=False`。
    - 断言 `global_te.get_transfer_engine` 和 `engine` 参数。

### TestYuanrongBackendMethods

11. `test_init_creates_hetero_client_and_calls_init`
    - patch `Blob`、`DeviceBlobList`、`HeteroClient`、`SetParam`、`WriteMode`、`YuanrongConfig.load_from_env`。
    - 断言 `HeteroClient(...).init()`。

12. `test_set_device_sets_helper_device_id`
    - patch current device。
    - 断言 `_helper._device_id` 设置。

## 8. Helper/Fake 需求清单

优先复用现有 helper；新增时保持最小实现。

- `FakeStore`
  - 增强 `get` 返回值配置：成功、部分失败、`None`、异常。
  - 记录 `exists/get/put/register_buffer` 调用参数。

- `FakeTokenDatabase`
  - 支持生成多 key、多 layer、多 group。
  - 支持 mask 后无 key 场景。
  - 支持 `prepare_value_layer` 记录 layer_id。

- `FakeThread`
  - 用于 connector `LookupKeyServer` 和 worker register thread 创建测试。
  - 记录 target、daemon、start 调用。

- `FakeSocket`
  - 支持 `recv_multipart`、`send`、`send_multipart`、`recv`、`close`。
  - 用 side effect 控制单次请求后退出。

- `FakeTensor` / `FakeStorage`
  - 提供 `shape`、`element_size()`、`data_ptr()`、`storage()` 等 worker register 需要字段。
  - 不依赖真实 torch tensor。

## 9. 推荐执行顺序

1. 先补 `config_data`，风险最低，用于校验新增用例风格。
2. 再补 `kv_transfer`，优先直接调用 `_handle_request`，最后处理 `run()`。
3. 补 `pool_scheduler`，重点构造 scheduler output fake。
4. 补 `pool_worker`，先完善 FakeTensor/FakeStore，再覆盖 layerwise。
5. 补 `ascend_store_connector`，优先 patch thread/socket。
6. 补 `backend`，所有 env/import 后端均用 patch 隔离。
7. 每层完成后运行对应文件，再运行：

   ```bash
   tools/run_ascend_store_ut.sh -q
   ruff check tests/ut/distributed/ascend_store
   ```
