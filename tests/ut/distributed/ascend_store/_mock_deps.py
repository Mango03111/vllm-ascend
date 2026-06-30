#
# Copyright (c) 2026 Huawei Technologies Co., Ltd. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# This file is a part of the vllm-ascend project.
#
"""Mock heavy dependencies (torch, vllm, etc.) for ascend_store unit tests.

IMPORTANT: This module MUST be imported before any vllm_ascend or vllm
imports in each test file.

Usage at the top of each test file:
    import tests.ut.distributed.ascend_store._mock_deps  # noqa: F401, E402
"""

import logging
import os
import sys
import types
from unittest.mock import MagicMock


def _set_module(name: str, module):
    sys.modules[name] = module
    parent_name, _, child_name = name.rpartition(".")
    if parent_name and parent_name in sys.modules:
        setattr(sys.modules[parent_name], child_name, module)
    return module


def _make_mod(name: str):
    mod = types.ModuleType(name)
    mod.__package__ = name.rpartition(".")[0]
    return mod


# ---------------------------------------------------------------------------
# Mock torch / torch_npu
# ---------------------------------------------------------------------------
_torch = _make_mod("torch")
_torch.Tensor = MagicMock  # type: ignore[attr-defined]
_torch.bool = "bool"  # type: ignore[attr-defined]
_torch.float16 = "float16"  # type: ignore[attr-defined]
_torch.zeros = MagicMock(return_value=MagicMock())  # type: ignore[attr-defined]
_torch.sum = MagicMock(return_value=0)  # type: ignore[attr-defined]
_torch.device = MagicMock()  # type: ignore[attr-defined]
_torch.distributed = MagicMock()  # type: ignore[attr-defined]
_torch.empty_like = MagicMock(return_value=MagicMock())  # type: ignore[attr-defined]
_npu = MagicMock()
_npu.Event = MagicMock
_npu.current_device = MagicMock(return_value=0)
_npu.set_device = MagicMock()
_torch.npu = _npu  # type: ignore[attr-defined]
_set_module("torch", _torch)
_set_module("torch.distributed", _torch.distributed)  # type: ignore[attr-defined]
_set_module("torch_npu", MagicMock())
_set_module("torch_npu._inductor", MagicMock())

# ---------------------------------------------------------------------------
# Mock vllm modules
# ---------------------------------------------------------------------------
_vllm_mock_modules = [
    "vllm",
    "vllm.config",
    "vllm.distributed",
    "vllm.distributed.kv_events",
    "vllm.distributed.kv_transfer",
    "vllm.distributed.kv_transfer.kv_connector",
    "vllm.distributed.kv_transfer.kv_connector.factory",
    "vllm.distributed.kv_transfer.kv_connector.v1",
    "vllm.distributed.kv_transfer.kv_connector.v1.base",
    "vllm.distributed.parallel_state",
    "vllm.envs",
    "vllm.forward_context",
    "vllm.logger",
    "vllm.model_executor",
    "vllm.model_executor.layers",
    "vllm.model_executor.layers.linear",
    "vllm.model_executor.layers.quantization",
    "vllm.platforms",
    "vllm.utils",
    "vllm.utils.hashing",
    "vllm.utils.math_utils",
    "vllm.utils.network_utils",
    "vllm.v1",
    "vllm.v1.attention",
    "vllm.v1.attention.backend",
    "vllm.v1.core.block_pool",
    "vllm.v1.core",
    "vllm.v1.core.kv_cache_manager",
    "vllm.v1.core.kv_cache_utils",
    "vllm.v1.core.sched",
    "vllm.v1.core.sched.output",
    "vllm.v1.kv_cache_interface",
    "vllm.v1.outputs",
    "vllm.v1.request",
    "vllm.v1.serial_utils",
]
for _mod_name in _vllm_mock_modules:
    _set_module(_mod_name, _make_mod(_mod_name))

sys.modules["vllm.utils.math_utils"].cdiv = lambda a, b: -(-a // b)  # type: ignore[attr-defined]
sys.modules["vllm.logger"].logger = logging.getLogger("vllm")  # type: ignore[attr-defined]
sys.modules["vllm.forward_context"].ForwardContext = MagicMock  # type: ignore[attr-defined]
sys.modules["vllm.utils.network_utils"].get_ip = MagicMock(return_value="127.0.0.1")  # type: ignore[attr-defined]
sys.modules["vllm.utils.network_utils"].make_zmq_socket = MagicMock()  # type: ignore[attr-defined]
sys.modules["vllm.utils.network_utils"].split_host_port = lambda addr: addr.rsplit(":", 1)  # type: ignore[attr-defined]

_config_mod = sys.modules["vllm.config"]
_config_mod.ParallelConfig = type("ParallelConfig", (), {})  # type: ignore[attr-defined]
_config_mod.VllmConfig = type("VllmConfig", (), {})  # type: ignore[attr-defined]

_dist_mod = sys.modules["vllm.distributed"]
_pcp_group = MagicMock(world_size=1, rank_in_group=0)
_dist_mod.get_pcp_group = MagicMock(return_value=_pcp_group)  # type: ignore[attr-defined]
_dist_mod.get_tensor_model_parallel_rank = MagicMock(return_value=0)  # type: ignore[attr-defined]
_dist_mod.get_tensor_model_parallel_world_size = MagicMock(return_value=1)  # type: ignore[attr-defined]

_parallel_state_mod = sys.modules["vllm.distributed.parallel_state"]
_world_group = MagicMock(local_rank=0, device_group=MagicMock())
_parallel_state_mod.get_world_group = MagicMock(return_value=_world_group)  # type: ignore[attr-defined]

_base_mod = sys.modules["vllm.distributed.kv_transfer.kv_connector.v1.base"]
_base_mod.KVConnectorBase_V1 = type("KVConnectorBase_V1", (), {"__init__": lambda self, **kw: None})  # type: ignore[attr-defined]
_base_mod.KVConnectorMetadata = type("KVConnectorMetadata", (), {})  # type: ignore[attr-defined]
_base_mod.KVConnectorWorkerMetadata = type("KVConnectorWorkerMetadata", (), {})  # type: ignore[attr-defined]
_base_mod.SupportsHMA = type("SupportsHMA", (), {})  # type: ignore[attr-defined]
_base_mod.KVConnectorRole = MagicMock()  # type: ignore[attr-defined]
_base_mod.KVConnectorRole.SCHEDULER = "SCHEDULER"
_base_mod.KVConnectorRole.WORKER = "WORKER"

_events_mod = sys.modules["vllm.distributed.kv_events"]
_events_mod.KVCacheEvent = type("KVCacheEvent", (), {})  # type: ignore[attr-defined]
_events_mod.KVConnectorKVEvents = type("KVConnectorKVEvents", (), {})  # type: ignore[attr-defined]


class _FakeAggregator:
    def __init__(self, *args, **kwargs):
        self._mock = MagicMock()

    def __getattr__(self, name):
        return getattr(self._mock, name)


_events_mod.KVEventAggregator = _FakeAggregator  # type: ignore[attr-defined]
_events_mod.BlockStored = type(  # type: ignore[attr-defined]
    "BlockStored",
    (),
    {"__init__": lambda self, **kwargs: self.__dict__.update(kwargs)},
)

_kv_cache_utils_mod = sys.modules["vllm.v1.core.kv_cache_utils"]
_kv_cache_utils_mod.BlockHash = bytes  # type: ignore[attr-defined]
_kv_cache_utils_mod.BlockHashList = list[bytes]  # type: ignore[attr-defined]
_kv_cache_utils_mod.maybe_convert_block_hash = lambda x: x  # type: ignore[attr-defined]

_sched_output_mod = sys.modules["vllm.v1.core.sched.output"]
_sched_output_mod.NewRequestData = MagicMock  # type: ignore[attr-defined]
_sched_output_mod.SchedulerOutput = MagicMock  # type: ignore[attr-defined]

_kv_cache_interface_mod = sys.modules["vllm.v1.kv_cache_interface"]
_kv_cache_interface_mod.FullAttentionSpec = type("FullAttentionSpec", (), {})  # type: ignore[attr-defined]
_kv_cache_interface_mod.KVCacheConfig = type("KVCacheConfig", (), {})  # type: ignore[attr-defined]
_kv_cache_interface_mod.MambaSpec = type("MambaSpec", (), {})  # type: ignore[attr-defined]
_kv_cache_interface_mod.SlidingWindowSpec = type("SlidingWindowSpec", (), {})  # type: ignore[attr-defined]
_kv_cache_interface_mod.UniformTypeKVCacheSpecs = type(  # type: ignore[attr-defined]
    "UniformTypeKVCacheSpecs",
    (),
    {"__init__": lambda self, kv_cache_specs=None: setattr(self, "kv_cache_specs", kv_cache_specs or {})},
)

sys.modules["vllm.v1.attention.backend"].AttentionMetadata = MagicMock  # type: ignore[attr-defined]
sys.modules["vllm.v1.core.block_pool"].BlockPool = MagicMock  # type: ignore[attr-defined]
sys.modules["vllm.v1.core.kv_cache_manager"].KVCacheBlocks = MagicMock  # type: ignore[attr-defined]
sys.modules["vllm.v1.outputs"].KVConnectorOutput = MagicMock  # type: ignore[attr-defined]
sys.modules["vllm.v1.request"].Request = MagicMock  # type: ignore[attr-defined]


class _FakeMsgpackCodec:
    def __init__(self, *args, **kwargs):
        pass

    def encode(self, value):
        return value if isinstance(value, list) else [value]

    def decode(self, frames):
        return frames


_serial_utils_mod = sys.modules["vllm.v1.serial_utils"]
_serial_utils_mod.MsgpackDecoder = _FakeMsgpackCodec  # type: ignore[attr-defined]
_serial_utils_mod.MsgpackEncoder = _FakeMsgpackCodec  # type: ignore[attr-defined]

sys.modules["vllm.envs"].VLLM_RPC_BASE_PATH = "/tmp/vllm_rpc"  # type: ignore[attr-defined]

# ---------------------------------------------------------------------------
# Mock external backends
# ---------------------------------------------------------------------------
for _mod_name in [
    "mooncake",
    "mooncake.engine",
    "mooncake.store",
    "memcache_hybrid",
    "yr",
    "yr.datasystem",
    "yr.datasystem.hetero_client",
    "yr.datasystem.kv_client",
    "yr.datasystem.object_client",
    "zmq",
]:
    _set_module(_mod_name, MagicMock())

sys.modules["mooncake.store"].ReplicateConfig = type("ReplicateConfig", (), {})  # type: ignore[attr-defined]

# ---------------------------------------------------------------------------
# Mock vllm_ascend transitive imports
# ---------------------------------------------------------------------------


def _make_pkg(name, path=""):
    mod = types.ModuleType(name)
    mod.__path__ = [path]  # type: ignore[attr-defined]
    mod.__package__ = name  # type: ignore[attr-defined]
    return mod


_repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
_vllm_ascend_root = os.path.join(_repo_root, "vllm_ascend")

_set_module("vllm_ascend", _make_pkg("vllm_ascend", _vllm_ascend_root))
_set_module(
    "vllm_ascend.distributed",
    _make_pkg("vllm_ascend.distributed", os.path.join(_vllm_ascend_root, "distributed")),
)

_kv_transfer_init = _make_pkg("vllm_ascend.distributed.kv_transfer")
_kv_transfer_init.register_connector = MagicMock()  # type: ignore[attr-defined]
_set_module("vllm_ascend.distributed.kv_transfer", _kv_transfer_init)

_kv_utils_pkg = _make_pkg("vllm_ascend.distributed.kv_transfer.utils")
_set_module("vllm_ascend.distributed.kv_transfer.utils", _kv_utils_pkg)
_mooncake_transfer_engine = MagicMock()
_mooncake_transfer_engine.global_te = MagicMock()
_set_module("vllm_ascend.distributed.kv_transfer.utils.mooncake_transfer_engine", _mooncake_transfer_engine)

_kv_pool_pkg = _make_pkg("vllm_ascend.distributed.kv_transfer.kv_pool")
_set_module("vllm_ascend.distributed.kv_transfer.kv_pool", _kv_pool_pkg)

_ascend_store_real_path = os.path.join(
    os.path.dirname(__file__),
    "..",
    "..",
    "..",
    "..",
    "vllm_ascend",
    "distributed",
    "kv_transfer",
    "kv_pool",
    "ascend_store",
)
_ascend_store_pkg = _make_pkg(
    "vllm_ascend.distributed.kv_transfer.kv_pool.ascend_store",
    os.path.abspath(_ascend_store_real_path),
)
_set_module("vllm_ascend.distributed.kv_transfer.kv_pool.ascend_store", _ascend_store_pkg)

_backend_pkg = _make_pkg(
    "vllm_ascend.distributed.kv_transfer.kv_pool.ascend_store.backend",
    os.path.join(os.path.abspath(_ascend_store_real_path), "backend"),
)
_set_module("vllm_ascend.distributed.kv_transfer.kv_pool.ascend_store.backend", _backend_pkg)

_ascend_utils = _make_mod("vllm_ascend.utils")
_ascend_utils.AscendDeviceType = MagicMock()
_ascend_utils.AscendDeviceType.A2 = "A2"
_ascend_utils.get_ascend_device_type = MagicMock(return_value=None)
_set_module("vllm_ascend.utils", _ascend_utils)

_ascend_distributed_utils = _make_mod("vllm_ascend.distributed.utils")
_ascend_distributed_utils.get_decode_context_model_parallel_rank = MagicMock(return_value=0)
_ascend_distributed_utils.get_decode_context_model_parallel_world_size = MagicMock(return_value=1)
_set_module("vllm_ascend.distributed.utils", _ascend_distributed_utils)

_ascend_parallel_state = _make_mod("vllm_ascend.distributed.parallel_state")
_ascend_parallel_state.get_global_rank = MagicMock(return_value=0)
_set_module("vllm_ascend.distributed.parallel_state", _ascend_parallel_state)
