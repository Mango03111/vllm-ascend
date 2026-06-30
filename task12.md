## 📚 任务 #12：AscendStore 池化模块 UT 测试补充

https://github.com/vllm-project/vllm-ascend/issues/10659

### 任务描述
该任务拆分自 #9079，任务 ID：#12。

AscendStore 是 vllm-ascend 池化场景的核心模块，负责 KV Cache 的分布式存储与传输。该模块分为 6 个子层：数据结构层（config_data）、传输线程层（kv_transfer）、调度层（pool_scheduler）、工作层（pool_worker）、连接器层（ascend_store_connector）、后端抽象层（backend）。当前已有 UT 测试覆盖率约 50%~70%，存在大量未覆盖的关键路径和边界场景。

本任务需要针对 6 个子层补充 UT 测试，重点覆盖：

1. 数据结构层中 `ChunkedTokenDatabase` 的多层 `prepare_value_layer`、`decode_adaptor_prefill_pp` 边界条件、`ReqMeta.from_request_tracker` 的 `is_last_chunk` 与 bytes hashes 组合。
2. 传输线程层中 `KVCacheStoreRecvingThread`/`KVCacheStoreLayerRecvingThread` 非零 `tp_rank` 的 key 轮转逻辑、线程 `run()` 实际执行流程、store 操作异常容错。
3. 调度层中 `build_connector_meta` 的 `scheduled_cached_reqs`（decode/chunked 请求）路径、preempted→resumed 恢复流程、`LookupKeyClient` 异常处理。
4. 工作层中 `register_kv_caches` 完整初始化、`start_load_kv` 同步路径、`wait_for_layer_load`/`save_kv_layer`/`wait_for_save`、`retrieve_layer`/`store_layer` 生成器迭代逻辑、`lookup_scheduler`。
5. 连接器层中 `LookupKeyServer` ZMQ 服务线程、`requires_piecewise_for_cudagraph` 类方法、`kv_both` 角色行为、`use_layerwise=True` 完整流程。
6. 后端抽象层中 `MemcacheBackend.set_device`、`MmcDirect` 枚举值验证、`MooncakeBackend` fabric memory 路径、各 Backend init 正常初始化 mock 验证。

### 验收标准
1. 补充 config_data 层 UT，覆盖 `ChunkedTokenDatabase.prepare_value_layer` 多层（`layer_id>0`）场景、`decode_adaptor_prefill_pp` 多分区边界、`ReqMeta.from_request_tracker` 的 `is_last_chunk`/bytes hashes/`discard_partial_chunks=False` 等组合场景，新增用例不少于 15 个。
2. 补充 kv_transfer 层 UT，覆盖 `KVCacheStoreRecvingThread` 和 `KVCacheStoreLayerRecvingThread` 非零 `tp_rank` 的 key 轮转、线程 `run()` 方法实际执行（含 None 请求和异常处理）、store.put/get 异常容错，新增用例不少于 12 个。
3. 补充 pool_scheduler 层 UT，覆盖 `build_connector_meta` 的 `scheduled_cached_reqs` 路径（decode 请求和 chunked 请求）、preempted→resumed 恢复流程、`LookupKeyClient` 超时/异常场景，新增用例不少于 10 个。
4. 补充 pool_worker 层 UT，覆盖 `register_kv_caches` 完整初始化（含 MLA/sparse 模式）、`start_load_kv` 同步路径、`wait_for_layer_load`/`save_kv_layer`/`wait_for_save`、`retrieve_layer`/`store_layer` 生成器迭代逻辑、`lookup_scheduler`，新增用例不少于 15 个。
5. 补充 ascend_store_connector 层 UT，覆盖 `LookupKeyServer` ZMQ 服务线程启动与请求处理、`requires_piecewise_for_cudagraph` 类方法、`kv_both` 角色行为、`use_layerwise=True` 完整 save/load 流程，新增用例不少于 10 个。
6. 补充 backend 层 UT，覆盖 `MemcacheBackend.set_device`、`MmcDirect` 枚举值验证、`MooncakeBackend` fabric memory 路径（`ASCEND_ENABLE_USE_FABRIC_MEM=1`）、各 Backend init 正常初始化 mock 验证，新增用例不少于 8 个。
7. 所有新增测试通过 CI 流水线（smart-ut），无 lint 错误。
8. 输出测试覆盖报告，记录每层新增用例数、覆盖的关键路径和边界场景。

### 本地 UT 隔离方案改动

为支持任务12在无真实 NPU、无真实外部 KV 后端、且本地 vLLM 版本可能不匹配的环境下开发 AscendStore UT，已补充本地隔离方案。

1. 更新 `tests/ut/distributed/ascend_store/_mock_deps.py`
   - 强制 mock `torch`、`torch_npu`、`vllm`、ZMQ、Mooncake、Memcache、Yuanrong 等重依赖。
   - 补齐 AscendStore 源码 import 所需的轻量符号，例如 `BlockHashList`、`UniformTypeKVCacheSpecs`、`ForwardContext`、`split_host_port`、`SupportsHMA`、`MsgpackEncoder/Decoder` 等。
   - 覆盖已提前进入 `sys.modules` 的真实模块，避免真实 vLLM/torch-npu 泄漏进 AscendStore UT。

2. 新增 `tests/ut/distributed/ascend_store/conftest.py`
   - 在 AscendStore 测试目录收集阶段优先导入 `_mock_deps.py`。
   - 配合 `--confcutdir=tests/ut/distributed/ascend_store` 截断父级 `tests/ut/conftest.py`，避免加载真实全局 UT 初始化逻辑。

3. 新增 `tools/run_ascend_store_ut.sh`
   - 封装本地隔离运行参数：

     ```bash
     export PYTEST_DISABLE_PLUGIN_AUTOLOAD=1
     export TORCH_DEVICE_BACKEND_AUTOLOAD=0
     export VLLM_PLUGINS=
     pytest --confcutdir=tests/ut/distributed/ascend_store "$@" tests/ut/distributed/ascend_store
     ```
