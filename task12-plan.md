# 任务12执行规划：AscendStore 池化模块 UT 测试补充

## 0. 本地 UT 隔离方案使用指导

为支持任务12在当前本地环境中开发 AscendStore UT，已补充本地隔离方案。该方案用于绕开真实 NPU、真实外部 KV 后端以及本地 vLLM 版本不匹配问题，只作为开发阶段快速验证入口，不改变任务12的最终交付要求。

### 已实现内容

1. `tests/ut/distributed/ascend_store/_mock_deps.py` （修改）
   - 强制 mock `torch`、`torch_npu`、`vllm`、ZMQ、Mooncake、Memcache、Yuanrong 等重依赖。
   - 补齐 AscendStore 源码 import 所需的轻量符号，例如 `BlockHashList`、`UniformTypeKVCacheSpecs`、`ForwardContext`、`split_host_port`、`SupportsHMA`、`MsgpackEncoder/Decoder`。
   - 覆盖已提前进入 `sys.modules` 的真实模块，避免真实 vLLM/torch-npu 泄漏进 AscendStore UT。

2. `tests/ut/distributed/ascend_store/conftest.py` （新增）
   - 在 AscendStore 测试目录收集阶段优先导入 `_mock_deps.py`。
   - 配合 `--confcutdir=tests/ut/distributed/ascend_store` 截断父级 `tests/ut/conftest.py`，避免加载真实全局 UT 初始化逻辑。

3. `tools/run_ascend_store_ut.sh` （新增）
   - 封装本地隔离运行参数：

     ```bash
     export PYTEST_DISABLE_PLUGIN_AUTOLOAD=1
     export TORCH_DEVICE_BACKEND_AUTOLOAD=0
     export VLLM_PLUGINS=
     pytest --confcutdir=tests/ut/distributed/ascend_store "$@" tests/ut/distributed/ascend_store
     ```

### 使用方式

开发任务12时，优先使用本地隔离脚本运行 AscendStore UT：

```bash
tools/run_ascend_store_ut.sh -q
```

运行单个文件或单个用例：

```bash
tools/run_ascend_store_ut.sh -sv tests/ut/distributed/ascend_store/test_config_data.py
tools/run_ascend_store_ut.sh -sv tests/ut/distributed/ascend_store/test_config_data.py::TestReqMeta::test_from_request_tracker_no_discard
```

生成覆盖率报告：

```bash
tools/run_ascend_store_ut.sh --cov=vllm_ascend.distributed.kv_transfer.kv_pool.ascend_store --cov-report=term-missing
```

### 交付一致性注意点

- 本地隔离脚本是开发辅助工具，不等价替代 CI smart-ut。
- 任务12的交付仍是补充 `tests/ut/distributed/ascend_store/` 下六层 UT，并满足新增用例数量、覆盖场景和覆盖报告要求。
- 新增 UT 可以使用 `_mock_deps.py`，但断言必须面向真实 AscendStore 源码行为，不能只验证 mock 本身。
- 不要为了适配本地 fake 修改生产代码；如测试暴露真实 bug，只记录复现和影响并反馈给用户，不在任务12中修复生产代码。
- 新增 UT 不应依赖真实 NPU、真实 Mooncake/Memcache/Yuanrong 服务或真实 ZMQ 端口。
- PR/交付说明中应区分本地隔离验证命令和 CI/smart-ut 结果。

## 1. 任务目标与交付标准

任务12要求补充 AscendStore 池化模块六层 UT，总新增用例不少于 70 个。

| 层级 | 源码文件 | 测试文件 | 新增用例要求 |
| --- | --- | --- | ---: |
| config_data | `config_data.py` | `test_config_data.py` | >= 15 |
| kv_transfer | `kv_transfer.py` | `test_kv_transfer.py` | >= 12 |
| pool_scheduler | `pool_scheduler.py` | `test_pool_scheduler.py` | >= 10 |
| pool_worker | `pool_worker.py` | `test_pool_worker.py` | >= 15 |
| ascend_store_connector | `ascend_store_connector.py` | `test_ascend_store_connector.py` | >= 10 |
| backend | `backend/*.py` | `test_backend.py` | >= 8 |

最终交付内容：

- 六层新增 UT，覆盖 `task12.md` 指定关键路径和边界场景。
- 本地隔离验证命令可运行。
- CI smart-ut 通过。
- lint 无新增错误。
- 覆盖报告记录每层新增用例数、覆盖路径和剩余风险。

## 2. 开发约束

- 优先扩展现有六个测试文件，不新增无必要测试目录。
- 沿用当前 `unittest.TestCase` 风格和 `_mock_deps.py` mock 机制。
- 使用 `MagicMock`、`patch.object`、`patch.dict`、轻量 fake class 构造输入。
- 线程相关测试必须可控，避免启动不可退出的后台线程；涉及 `run()` 时使用 timeout、sentinel 或 side effect 控制退出。
- 对 key 轮转、metadata 字段、invalid block 集合、backend 参数等关键行为做精确断言。
- 环境变量只在测试作用域内用 `patch.dict(os.environ, ...)` 设置，避免污染其他用例。
- 不新增生产环境变量，不引入新的全局可变状态。
- 除测试文件、测试辅助文件和任务文档外，不修改生产代码；如新增 UT 暴露生产 bug，先记录复现路径、影响范围和建议 issue 标题，由用户决定是否发 issue 或另起修复任务。

## 3. 贴合 CI Smart-UT 的开发准则

当前本地隔离脚本用于解决本地依赖不匹配问题，但本地通过不代表 CI smart-ut 必然通过。开发新增 UT 时需要遵守以下准则，降低本地与 CI 行为偏差。

1. 测试目标必须是 AscendStore 源码行为
   - 断言重点放在 `config_data.py`、`kv_transfer.py`、`pool_scheduler.py`、`pool_worker.py`、`ascend_store_connector.py`、`backend/*.py` 的输出、副作用和调用参数。
   - 不编写只验证 `_mock_deps.py`、fake socket、fake tensor 自身行为的测试。

2. mock 只用于隔离输入和外部依赖
   - 可以 mock vLLM 对象、torch tensor、ZMQ socket、Mooncake/Memcache/Yuanrong 后端。
   - 不让测试依赖本地脚本独有的 mock 实现细节，例如 fake codec 的内部返回方式。
   - fake class 只实现被测路径需要的最小字段和方法，避免模拟出生产环境不存在的行为。

3. 保持 pytest 常规收集兼容
   - 新增测试放在 `tests/ut/distributed/ascend_store/` 现有测试文件中。
   - 测试模块顶部继续导入 `_mock_deps.py`，保持与现有 AscendStore UT 风格一致。
   - 不新增只服务本地脚本的临时测试入口或特殊目录。

4. 避免真实资源依赖
   - 不连接真实 ZMQ 端口。
   - 不启动真实 Mooncake/Memcache/Yuanrong 服务。
   - 不依赖真实 NPU、真实 `torch_npu` runtime 或真实 device tensor。
   - 线程测试必须使用 fake thread、受控 queue、timeout 或同步执行 target。

5. 隔离全局状态
   - 环境变量使用 `patch.dict(os.environ, ...)`。
   - `sys.modules`、logger、全局单例、class monkeypatch 必须在测试作用域内恢复。
   - 避免测试之间共享可变对象；必要时在 `setUp` 重新构造。

6. 精确断言 CI 关心的稳定行为
   - key 轮转顺序、addr/size 列表、block id、`ReqMeta` 字段、invalid block 集合、backend `get/put/exists` 参数必须明确断言。
   - 异常路径需断言返回值和副作用，例如 `task_done()`、`get_event.set()`、finished request、invalid blocks。
   - 不使用宽泛断言替代关键行为，例如只断言“不抛异常”。

7. 本地验证与交付说明分开
   - 本地开发优先运行 `tools/run_ascend_store_ut.sh -q`。
   - 提交说明中应明确本地隔离验证不等同于 CI smart-ut。
   - 最终交付以 CI smart-ut 或版本匹配环境下的 smart-ut 结果为准。

8. 不在任务12中修复生产代码
   - 任务12默认只补 UT，不修改 `vllm_ascend/distributed/kv_transfer/kv_pool/ascend_store/` 下的生产实现。
   - 如果测试暴露真实生产 bug，暂停对应修复，记录最小复现、失败断言、影响模块和建议 issue 标题。
   - 将 bug 情况反馈给用户，由用户发 issue 或决定是否另开修复任务。
   - 不为适配本地 fake 修改生产逻辑。

## 4. 分阶段实施计划

### 阶段0：基线与用例清单

目标：

- 使用 `tools/run_ascend_store_ut.sh -q` 建立本地 AscendStore UT 基线。
- 按六层列出拟新增测试方法名，确保数量和覆盖点不遗漏。
- 确认 `_mock_deps.py` 是否还缺少任务新增用例需要的轻量 mock 符号。

产出：

- 六层用例清单：`task12-testcase-list.md`。
- 需要补充的 fake/helper 列表：见 `task12-testcase-list.md` 第 8 节。

状态：

- 已完成本地隔离 UT 基线验证。
- 已完成现有 AscendStore UT 覆盖点提取。
- 已完成六层新增用例清单和 helper/fake 需求清单。

### 阶段1：`config_data` UT 补充

目标新增不少于 15 个用例。

覆盖重点：

- `ChunkedTokenDatabase.prepare_value_layer`
  - `layer_id > 0` 多层基址选择。
  - 有/无 `group_block_stride`。
  - 多 cache entry 的 addr/size 计算。
  - 非首 block 的 `block_id` 选择。

- `decode_adaptor_prefill_pp`
  - `partitions is None` 和单分区直接返回。
  - 多分区边界切分。
  - `group_num_layers` 已设置和缺省 fallback。
  - 最后一个 partition 吃掉剩余 addr/size。

- `ReqMeta.from_request_tracker`
  - `is_last_chunk=True/False`。
  - bytes hashes 与字符串 hashes。
  - `discard_partial_chunks=False`。
  - `skip_save=True + load_spec is None` 返回 `None`。
  - `load_spec.can_load=True` 与 `can_save` 组合。

### 阶段2：`kv_transfer` UT 补充

目标新增不少于 12 个用例。

覆盖重点：

- `KVCacheStoreRecvingThread`
  - 非零 `tp_rank` key/addr/size/block id 轮转。
  - `m_store.get` 部分失败。
  - `m_store.get` 返回 `None`。
  - 单 group 更新 `_invalid_block_ids`。
  - hybrid 多 group 失败不污染 `_invalid_block_ids`。
  - 无 key 时设置 finished 并 `task_done()`。

- `KVCacheStoreLayerRecvingThread`
  - 非零 `tp_rank` layerwise key 轮转。
  - 部分失败与 `None` 返回。
  - `task_done()` 和 `get_event.set()` 副作用。

- `KVTransferThread.run()`
  - `ready_event.set()`。
  - 正常请求、`None` 请求、异常请求路径。
  - 可控退出，避免测试 hang。

### 阶段3：`pool_scheduler` UT 补充

目标新增不少于 10 个用例。

覆盖重点：

- `build_connector_meta` 的 `scheduled_cached_reqs`
  - decode 请求追加 token、更新 tracker。
  - chunked 请求到 granularity 边界生成 `ReqMeta`。
  - `num_computed_token >= len(prompt_token_ids)` 跳过。
  - `_unfinished_requests` 缺失抛 `ValueError`。

- preempted -> resumed
  - `_preempted_req_ids` 清理。
  - `load_specs` 消费。
  - `_request_trackers` 重建。
  - resumed 请求携带可加载 `load_spec`。

- `LookupKeyClient`
  - `send_multipart` frame 结构。
  - `recv` bytes 转 int。
  - `send/recv` 超时或异常行为。
  - `close(linger=0)`。

### 阶段4：`pool_worker` UT 补充

目标新增不少于 15 个用例。

覆盖重点：

- `register_kv_caches`
  - `num_blocks`、`kv_caches`、group metadata 初始化。
  - `m_store.register_buffer`。
  - `token_database.set_group_buffers`。
  - MLA/sparse/aligned state 模式。
  - `use_layerwise=True` 下线程类构造和 `start()`。
  - `load_async=False` 下不创建普通 recv thread。

- `start_load_kv`
  - 同步路径 `load_async=False`。
  - key 轮转和 backend `get` 参数。
  - `load_spec is None`、`can_load=False` 跳过。
  - token_len 修正逻辑。
  - hybrid group 失败处理。

- layerwise load/save
  - `wait_for_layer_load`。
  - `save_kv_layer`。
  - `wait_for_save` 的 queue barrier。
  - `retrieve_layer` 有 key/无 key 生成器路径。
  - `store_layer` 有 key/无 key 生成器路径。

- `lookup_scheduler`
  - 普通命中和首次 miss。
  - `use_layerwise=True`。
  - backend `exists` 异常返回 0。
  - lookup gate group 过滤。

### 阶段5：`ascend_store_connector` UT 补充

目标新增不少于 10 个用例。

覆盖重点：

- `LookupKeyServer`
  - fake socket 服务线程启动。
  - 请求 frame 解析。
  - 调用 `pool_worker.lookup_scheduler(token_len, hashes, groups, use_layerwise)`。
  - 4 字节 big-endian response。
  - `close()`。

- connector 条件分支
  - `requires_piecewise_for_cudagraph`。
  - `kv_both` 角色下 save/load/finished 行为。
  - `use_layerwise=True` 下 `start_load_kv`、`wait_for_layer_load`、`save_kv_layer`、`wait_for_save`。

### 阶段6：`backend` UT 补充

目标新增不少于 8 个用例。

覆盖重点：

- `MemcacheBackend.set_device`
  - `torch.device(f"npu:{local_rank}")`。
  - `torch.npu.set_device` 调用。

- `MmcDirect`
  - `COPY_L2G=0`、`COPY_G2L=1`、`COPY_G2H=2`、`COPY_H2G=3`。
  - `get/put` 使用正确 enum value。

- `MooncakeBackend` fabric memory
  - `ASCEND_ENABLE_USE_FABRIC_MEM=1`。
  - setup `local_buffer_size=0`。
  - 不走 transfer engine。
  - lazy init 由 `put()` 触发。

- Backend init mock
  - `MooncakeBackend` 正常初始化。
  - `MemcacheBackend` A2/非 A2 lazy 逻辑。
  - `YuanrongBackend` 初始化 `HeteroClient.init()`。

### 阶段7：聚合验证与覆盖报告

执行顺序：

1. 单文件运行新增测试。
2. 运行本地隔离聚合测试：

   ```bash
   tools/run_ascend_store_ut.sh -q
   ```

3. 运行覆盖率：

   ```bash
   tools/run_ascend_store_ut.sh --cov=vllm_ascend.distributed.kv_transfer.kv_pool.ascend_store --cov-report=term-missing
   ```

4. 运行相关 lint：

   ```bash
   ruff check tests/ut/distributed/ascend_store
   bash -n tools/run_ascend_store_ut.sh
   ```

5. 在可用 CI/匹配环境中确认 smart-ut。
6. 输出覆盖报告，记录每层新增用例数、覆盖路径和剩余风险。

## 5. 风险与应对

| 风险 | 影响 | 应对 |
| --- | --- | --- |
| 本地隔离脚本通过但 CI smart-ut 失败 | 本地与 CI 语义不完全一致 | 新增测试只断言源码行为，不依赖本地 fake 特性；最终以 CI smart-ut 为准 |
| 线程测试 hang | 阻塞本地或 CI | 使用 fake thread、timeout、sentinel、side effect 控制退出 |
| ZMQ 服务线程不可控 | 测试不稳定 | patch `threading.Thread` 或 fake socket，同步执行一次请求 |
| mock tensor 行为不足 | worker 注册/load/save 测试失败 | 构造最小 FakeTensor/FakeStorage，只补被测路径字段 |
| 环境变量污染 | 影响其他 UT | 所有 env 修改使用 `patch.dict` 限定作用域 |
| 覆盖数量达标但断言弱 | 无法防回归 | 对顺序、字段、副作用、backend 参数做精确断言 |
| 测试暴露生产 bug | 任务范围扩大 | 不在任务12中修复生产代码；记录复现、影响和建议 issue 标题并反馈给用户 |
| 为本地隔离修改生产逻辑 | 交付偏离要求 | 本地隔离只改测试辅助层，不因 fake 行为调整生产代码 |

## 6. 质量验证标准

- 新增 UT 总数不少于 70。
- 六层新增用例数分别满足 15/12/10/15/10/8。
- `task12.md` 指定关键路径均有直接测试覆盖。
- 异常路径断言返回值和副作用，不能只断言“不抛异常”。
- 线程相关测试有明确退出条件。
- 新增测试不依赖真实 NPU、真实后端服务或真实端口。
- `ruff check tests/ut/distributed/ascend_store` 无错误。
- 覆盖报告包含每层新增用例数、覆盖关键路径和剩余风险。
- CI smart-ut 通过后再作为最终交付依据。

## 7. 排期建议

| 时间 | 目标 | 产出 |
| --- | --- | --- |
| Day 1 上午 | 基线、用例清单、helper/fake 梳理 | 六层测试方法清单 |
| Day 1 下午 | `config_data` | 新增 >= 15 个 UT |
| Day 2 上午 | `kv_transfer` | 新增 >= 12 个 UT |
| Day 2 下午 | `pool_scheduler` | 新增 >= 10 个 UT |
| Day 3 | `pool_worker` | 新增 >= 15 个 UT |
| Day 4 上午 | `ascend_store_connector` | 新增 >= 10 个 UT |
| Day 4 下午 | `backend` | 新增 >= 8 个 UT |
| Day 5 上午 | 聚合测试、lint、覆盖率 | 本地隔离验证和覆盖报告 |
| Day 5 下午 | CI/smart-ut 与交付材料 | PR 测试说明和覆盖总结 |

## 8. 验收追踪清单

| 层级 | 目标新增数 | 完成判定 |
| --- | ---: | --- |
| config_data | >= 15 | 多层 prepare、PP 分区、ReqMeta 组合覆盖 |
| kv_transfer | >= 12 | 非零 TP rank、run、None/异常容错覆盖 |
| pool_scheduler | >= 10 | cached decode/chunked、preempted resumed、LookupKeyClient 异常覆盖 |
| pool_worker | >= 15 | register、sync load、layer load/save、生成器、lookup_scheduler 覆盖 |
| ascend_store_connector | >= 10 | LookupKeyServer、piecewise、kv_both、layerwise save/load 覆盖 |
| backend | >= 8 | Memcache set_device、MmcDirect、Mooncake fabric、backend init 覆盖 |
| 总计 | >= 70 | 本地隔离验证、smart-ut、lint、覆盖报告完成 |
