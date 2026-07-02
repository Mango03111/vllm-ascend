# Task12 AscendStore UT 覆盖报告

## 1. 新增用例统计

| 层级 | 测试文件 | 任务要求新增数量 | 实际新增数量 | 是否达标 |
| --- | --- | ---: | ---: | --- |
| `config_data` | `tests/ut/distributed/ascend_store/test_config_data.py` | > 15 | 16 | 是 |
| `kv_transfer` | `tests/ut/distributed/ascend_store/test_kv_transfer.py` | > 12 | 13 | 是 |
| `pool_scheduler` | `tests/ut/distributed/ascend_store/test_pool_scheduler.py` | > 10 | 13 | 是 |
| `pool_worker` | `tests/ut/distributed/ascend_store/test_pool_worker.py` | > 15 | 18 | 是 |
| `ascend_store_connector` | `tests/ut/distributed/ascend_store/test_ascend_store_connector.py` | > 10 | 17 | 是 |
| `backend` | `tests/ut/distributed/ascend_store/test_backend.py` | > 8 | 14 | 是 |

## 2. 覆盖关键路径

### 2.1 `config_data`

- `ChunkedTokenDatabase.prepare_value_layer` 多层 KV 地址计算路径。
- `ChunkedTokenDatabase.prepare_value_layer` block stride、block length、非首 block id 和部分 token 长度计算路径。
- `ChunkedTokenDatabase.decode_adaptor_prefill_pp` 多分区 key/address/size 拆分路径。
- `ReqMeta.from_request_tracker` 的保存标记、加载标记、token ids、KV cache group family 组合构造路径。
- bytes block hashes 在 request tracker 到 `ReqMeta` 转换中的保留与分组路径。

### 2.2 `kv_transfer`

- `KVTransferThread.run()` 的 ready event、队列消费、`None` 请求跳过和异常后继续消费路径。
- `KVCacheStoreRecvingThread._handle_request` 非零 `tp_rank` key/address/size 轮转路径。
- `KVCacheStoreRecvingThread._handle_request` 失败 block 记录、`get()` 返回 `None` 和无 key 完成路径。
- `KVCacheStoreLayerRecvingThread._handle_request` layerwise 非零 `tp_rank` 轮转路径。
- `KVCacheStoreLayerRecvingThread._handle_request` layerwise 失败 block 记录、`get_event` 通知和 `task_done` 路径。

### 2.3 `pool_scheduler`

- `KVPoolScheduler.build_connector_meta` 的 `scheduled_cached_reqs` decode 请求路径。
- `KVPoolScheduler.build_connector_meta` 的 chunked 请求边界生成与边界前跳过路径。
- preempted 请求恢复为 resumed 请求后的 tracker 重建、load spec 消费和保存路径。
- cached request 已完成 prompt 后的跳过路径。
- `LookupKeyClient.lookup` 请求编码、group ids/hash frames 发送、响应解析和 close 路径。

### 2.4 `pool_worker`

- `KVPoolWorker.register_kv_caches` buffer 注册、共享 storage 合并、独立 storage 注册路径。
- `KVPoolWorker.register_kv_caches` token database group buffers、group layer 数量、sparse KV head 推导路径。
- layerwise producer 注册时发送/接收线程创建路径。
- `KVPoolWorker.start_load_kv` 同步加载、非零 TP rank 轮转、失败 block 记录和 token_len 修正路径。
- `KVPoolWorker.wait_for_layer_load`、`save_kv_layer`、`retrieve_layer`、`store_layer` 的 layerwise 迭代路径。
- `KVPoolWorker.lookup_scheduler` group gate 过滤路径。

### 2.5 `ascend_store_connector`

- `LookupKeyServer` 初始化、ZMQ socket 创建、服务线程启动和请求处理路径。
- `LookupKeyServer` response 编码、`use_layerwise` 参数透传和关闭 socket 路径。
- `AscendStoreConnector.requires_piecewise_for_cudagraph` 类方法路径。
- worker 角色下 start load、wait layer load、wait/save KV、get finished 的委托路径。
- `kv_both`、`kv_consumer + consumer_is_to_put`、`use_layerwise=True` 角色分支路径。
- worker metadata、load error block ids、KV cache events 相关委托路径。

### 2.6 `backend`

- `MemcacheBackend.set_device` 设备选择路径。
- `MmcDirect` 枚举值和 `get()`/`put()` copy 方向路径。
- `MemcacheBackend` 非 A2 lazy init、A2 立即初始化和 A2 buffer 延迟注册路径。
- `MooncakeBackend` fabric memory 初始化路径。
- `MooncakeBackend` 非 fabric transfer engine 初始化和 fabric 下 buffer 注册跳过路径。
- `MooncakeBackend` lazy init 由 `put()` 触发和 lazy exists 缺失返回路径。
- `YuanrongBackend` HeteroClient 初始化和设备设置路径。

## 3. 覆盖边界场景

### 3.1 `config_data`

- `prepare_value_layer` 覆盖 `layer_id > 0` 的第二层 base address 选择。
- 显式 stride 与缺省 stride 两种地址计算方式。
- 非首 block id 与部分 token 片段的地址/size 计算。
- prefill pipeline 多分区中最后一个 partition 接收 remainder。
- key 中只替换首个 `pp_rank` 标记，避免误替换其他字段。
- bytes hashes、`is_last_chunk=True/False`、`discard_partial_chunks=False` 的组合构造。
- skip-save 与已有 load spec 共存时的字段保留。

### 3.2 `kv_transfer`

- `run()` 遇到 `None` 请求时仍继续消费后续请求。
- `_handle_request` 抛异常后线程循环继续处理下一条请求。
- 非零 `tp_rank` 后失败码映射到轮转后的 block id。
- backend `get()` 返回 `None` 时将涉及 block 标记为失败。
- hybrid 多 group 失败时不写入单 group invalid block 集合。
- 无 key 场景直接标记请求完成。
- layerwise 接收失败后仍完成队列通知并触发 `get_event`。

### 3.3 `pool_scheduler`

- cached decode 请求更新 unfinished tracker。
- cached chunked 请求在达到边界时生成 connector metadata。
- cached chunked 请求在边界前不生成 metadata。
- cached request 已完成 prompt 计算后跳过。
- cached request 缺少 unfinished tracker 时抛出异常。
- preempted 请求恢复后清理 preempted 标记。
- resumed 请求带 load spec 与无 load spec 两种恢复路径。
- `LookupKeyClient` send timeout 与 recv timeout。

### 3.4 `pool_worker`

- 同一 storage 的 KV cache 区间合并注册。
- 不同 storage 的 KV cache 独立注册。
- 多层 KV cache group num layers 计算。
- sparse 模式下 KV head 与 TP size 推导。
- layerwise producer 同时创建 send/recv thread。
- `load_async=False` 时不创建非 layerwise recv thread。
- 同步 load 中非零 TP rank 轮转 key/address/size。
- `get()` 失败码、`get()` 返回 `None`、hybrid 失败与尾块 token_len 修正。
- final layer load 消费返回 mask。
- layerwise storer 初始化、已有 storer 推进、retrieve/store generator metadata 生成。
- lookup gate 只使用符合条件的 c1 group。

### 3.5 `ascend_store_connector`

- `LookupKeyServer` thread target 可调用且以 daemon 方式启动。
- 单次 lookup 请求解析 token length、group ids、hashes 并调用 worker。
- lookup 响应按 big-endian bytes 返回。
- `use_layerwise=True` 透传到 worker lookup。
- server close 使用 `linger=0`。
- piecewise 判断覆盖 true、default false、explicit false。
- `kv_both` save/load finished 行为委托。
- `kv_consumer + consumer_is_to_put` 允许 wait_for_save 委托。
- layerwise wait/save 分支与 non-layerwise noop 分支。

### 3.6 `backend`

- `MemcacheBackend.set_device` 使用 local rank 构造 NPU device。
- `MmcDirect` 四个方向枚举值保持稳定。
- `MemcacheBackend.get()` 使用 `COPY_G2L`，`put()` 使用 `COPY_L2G`。
- 非 A2 lazy init 不立即 setup store。
- A2 场景忽略 lazy init 并立即 setup store。
- A2 buffer 在 store 未初始化时暂存，初始化后注册。
- `ASCEND_ENABLE_USE_FABRIC_MEM=1` 时 Mooncake setup 使用 `local_buffer_size=0`。
- fabric memory 下 register buffer 跳过 transfer engine。
- 非 fabric memory 下使用 transfer engine 并传入 engine。
- Yuanrong init 创建 HeteroClient 并调用 `init()`。
- Yuanrong set_device 将 current device 写入 helper。

## 4. 分层用例明细

### 4.1 `config_data`

- `test_prepare_value_layer_uses_second_layer_base_addr`：覆盖 `layer_id=1` 使用第二层 KV base address。
- `test_prepare_value_layer_uses_explicit_stride`：覆盖显式 stride 参与地址计算。
- `test_prepare_value_layer_without_stride_uses_block_len`：覆盖缺省 stride 使用 block length。
- `test_prepare_value_layer_selects_non_first_block_id`：覆盖非首 block id 的地址选择。
- `test_prepare_value_layer_partial_token_size_for_each_cache`：覆盖部分 token 范围的 size 计算。
- `test_decode_adaptor_prefill_pp_uses_group_num_layers`：覆盖 group layer 数参与分区拆分。
- `test_decode_adaptor_prefill_pp_fallback_caches_per_layer_when_no_group_num_layers`：覆盖缺少 group layer 数时的 fallback。
- `test_decode_adaptor_prefill_pp_last_partition_takes_remainder`：覆盖最后分区接收 remainder。
- `test_decode_adaptor_prefill_pp_replaces_only_first_pp_rank`：覆盖只替换首个 pipeline rank 标记。
- `test_decode_adaptor_prefill_pp_multiple_keys_each_partitioned`：覆盖多个 key 均按分区拆分。
- `test_from_request_tracker_preserves_is_last_chunk_true`：覆盖 `is_last_chunk=True`。
- `test_from_request_tracker_preserves_is_last_chunk_false`：覆盖 `is_last_chunk=False`。
- `test_from_request_tracker_bytes_hashes_no_discard_partial`：覆盖 bytes hashes 与 `discard_partial_chunks=False`。
- `test_from_request_tracker_skip_save_with_load_spec_keeps_load`：覆盖 skip-save 与 load spec 共存。
- `test_from_request_tracker_kv_cache_group_families_combination`：覆盖 KV cache family 组合字段。
- `test_from_request_tracker_token_ids_are_preserved`：覆盖 token ids 保留。

### 4.2 `kv_transfer`

- `test_run_sets_ready_event_and_handles_request`：覆盖 run 启动 ready event 和请求处理。
- `test_run_ignores_none_request_and_continues`：覆盖 `None` 请求跳过。
- `test_run_continues_after_handle_request_exception`：覆盖请求处理异常后继续循环。
- `test_handle_request_rotates_keys_for_nonzero_tp_rank`：覆盖 async recv 非零 TP rank 轮转。
- `test_handle_request_records_partial_failed_blocks`：覆盖部分失败 block 记录。
- `test_handle_request_records_failed_blocks_after_tp_rotation`：覆盖轮转后失败 block id 映射。
- `test_handle_request_records_all_blocks_when_get_returns_none`：覆盖 backend get 返回 `None`。
- `test_handle_request_hybrid_failure_does_not_update_invalid_blocks`：覆盖 hybrid 失败不写 invalid blocks。
- `test_handle_request_no_keys_marks_finished`：覆盖无 key 请求直接完成。
- `test_layer_recv_rotates_keys_for_nonzero_tp_rank`：覆盖 layerwise recv 非零 TP rank 轮转。
- `test_layer_recv_records_partial_failed_blocks`：覆盖 layerwise 部分失败 block 记录。
- `test_layer_recv_records_all_blocks_when_get_returns_none`：覆盖 layerwise get 返回 `None`。
- `test_layer_recv_task_done_and_sets_get_event_after_failure`：覆盖 layerwise 失败后的队列和事件通知。

### 4.3 `pool_scheduler`

- `test_build_connector_meta_cached_decode_request_updates_tracker`：覆盖 cached decode 请求 tracker 更新。
- `test_build_connector_meta_cached_chunked_request_generates_meta_at_boundary`：覆盖 chunked 边界生成 metadata。
- `test_build_connector_meta_cached_chunked_request_skips_before_boundary`：覆盖 chunked 边界前跳过。
- `test_build_connector_meta_cached_request_skips_after_prompt_computed`：覆盖 prompt 已完成后跳过。
- `test_build_connector_meta_cached_request_missing_unfinished_raises`：覆盖缺少 unfinished tracker 异常。
- `test_build_connector_meta_preempted_resumed_rebuilds_tracker`：覆盖 preempted 恢复 tracker。
- `test_build_connector_meta_preempted_resumed_consumes_load_spec`：覆盖 resumed 消费 load spec。
- `test_build_connector_meta_preempted_resumed_without_load_spec_saves`：覆盖 resumed 无 load spec 保存路径。
- `test_lookup`：覆盖 lookup 基础请求响应路径。
- `test_lookup_encodes_group_ids_and_hash_frames`：覆盖 group ids 和 hash frames 编码。
- `test_lookup_send_multipart_timeout_raises`：覆盖发送超时。
- `test_lookup_recv_timeout_raises`：覆盖接收超时。
- `test_close`：覆盖 client close。

### 4.4 `pool_worker`

- `test_register_kv_caches_registers_merged_storage_regions`：覆盖同 storage 区间合并注册。
- `test_register_kv_caches_registers_distinct_storage_regions`：覆盖不同 storage 独立注册。
- `test_register_kv_caches_sets_token_database_group_buffers`：覆盖 token database group buffers 设置。
- `test_register_kv_caches_sets_group_num_layers`：覆盖 group layer 数计算。
- `test_sparse_metadata_uses_single_kv_head`：覆盖 sparse 模式 KV head 推导。
- `test_register_kv_caches_layerwise_producer_creates_send_and_recv_threads`：覆盖 layerwise producer thread 创建。
- `test_register_kv_caches_non_layerwise_load_async_false_no_recv_thread`：覆盖 `load_async=False` 不创建 recv thread。
- `test_start_load_kv_sync_rotates_for_nonzero_tp_rank`：覆盖同步 load 非零 TP rank 轮转。
- `test_start_load_kv_sync_records_failed_blocks`：覆盖同步 load 部分失败 block 记录。
- `test_start_load_kv_sync_get_none_records_blocks`：覆盖同步 load get 返回 `None`。
- `test_start_load_kv_sync_hybrid_failure_does_not_update_invalid_blocks`：覆盖 hybrid 失败处理。
- `test_start_load_kv_adjusts_token_len_for_last_partial_chunk`：覆盖尾块 token_len 修正。
- `test_wait_for_layer_load_final_layer_consumes_ret_mask`：覆盖 final layer load ret mask 消费。
- `test_save_kv_layer_initializes_storers_on_first_layer`：覆盖首层 storer 初始化。
- `test_save_kv_layer_advances_all_storers`：覆盖已有 storer 推进。
- `test_retrieve_layer_yields_each_layer_and_final_mask`：覆盖 retrieve generator 逐层 yield。
- `test_store_layer_yields_layer_metadata_with_hashes`：覆盖 store generator metadata 字段。
- `test_lookup_scheduler_gate_filters_non_c1_groups`：覆盖 scheduler lookup group gate 过滤。

### 4.5 `ascend_store_connector`

- `test_lookup_key_server_starts_thread`：覆盖 lookup server thread 启动。
- `test_lookup_key_server_processes_single_request`：覆盖单次 lookup 请求处理。
- `test_lookup_key_server_sends_big_endian_response`：覆盖响应 big-endian 编码。
- `test_lookup_key_server_passes_use_layerwise_true`：覆盖 `use_layerwise=True` 透传。
- `test_lookup_key_server_close_closes_socket`：覆盖 socket close。
- `test_requires_piecewise_for_cudagraph_true`：覆盖 piecewise true。
- `test_requires_piecewise_for_cudagraph_default_false`：覆盖 piecewise 默认 false。
- `test_requires_piecewise_for_cudagraph_explicit_false`：覆盖 piecewise 显式 false。
- `test_start_load_kv_layerwise_delegates_metadata`：覆盖 layerwise start load metadata 委托。
- `test_wait_for_layer_load_layerwise_delegates`：覆盖 layerwise wait load 委托。
- `test_wait_for_save_kv_both_delegates_to_worker`：覆盖 `kv_both` wait save 委托。
- `test_wait_for_save_consumer_to_put_delegates_to_worker`：覆盖 consumer-to-put wait save 委托。
- `test_wait_for_save_layerwise_noop`：覆盖 layerwise wait save noop。
- `test_save_kv_layer_kv_both_layerwise_delegates`：覆盖 `kv_both` layerwise save 委托。
- `test_get_finished_kv_both_returns_worker_results`：覆盖 `kv_both` finished 返回。
- `test_get_block_ids_with_load_errors_delegates`：覆盖 load error block ids 委托。
- `test_build_connector_worker_meta_delegates`：覆盖 worker metadata 委托。

### 4.6 `backend`

- `test_init_fabric_memory_sets_local_buffer_zero`：覆盖 Mooncake fabric memory setup。
- `test_register_buffer_skips_transfer_engine_for_fabric_memory`：覆盖 fabric memory 下跳过 transfer engine。
- `test_lazy_init_fabric_memory_put_initializes_store`：覆盖 Mooncake lazy init 由 put 触发。
- `test_init_non_fabric_uses_transfer_engine`：覆盖非 fabric transfer engine setup。
- `test_exists_lazy_uninitialized_returns_missing`：覆盖 lazy 未初始化 exists 返回 missing。
- `test_init_creates_hetero_client_and_calls_init`：覆盖 Yuanrong HeteroClient 初始化。
- `test_set_device_sets_helper_device_id`：覆盖 Yuanrong set_device 写入 helper。
- `test_set_device_uses_local_rank`：覆盖 Memcache set_device 使用 local rank。
- `test_mmc_direct_enum_values`：覆盖 `MmcDirect` 枚举值。
- `test_get_uses_copy_g2l_enum`：覆盖 Memcache get copy 方向。
- `test_put_uses_copy_l2g_enum`：覆盖 Memcache put copy 方向。
- `test_init_non_a2_lazy_init_defers_store_setup`：覆盖非 A2 lazy 延迟初始化。
- `test_init_a2_ignores_lazy_init_and_initializes_store`：覆盖 A2 立即初始化。
- `test_register_buffer_waits_for_a2_lazy_store_initialization`：覆盖 A2 buffer 延迟注册。
