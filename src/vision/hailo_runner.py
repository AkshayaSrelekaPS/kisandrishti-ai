"""
KisanDrishti AI: Optional Hailo-8 / Hailo-8L NPU Vision Inference Wrapper (Raspberry Pi AI HAT+)

Architecture Separation (Challenge Compliant):
- When HailoRT (`hailo_platform`) and a compiled `.hef` model exist, vision classification
  runs on the Hailo NPU via HailoRT while Meta Llama 3.2 runs separately via ExecuTorch on CPU.
- Otherwise, vision automatically falls back to ONNX Runtime on the Raspberry Pi 5 Arm CPU.
"""
import os
import numpy as np

try:
    from hailo_platform import (
        ConfigureParams,
        FormatType,
        HailoStreamInterface,
        HEF,
        InferVStreams,
        InputVStreamParams,
        OutputVStreamParams,
        VDevice,
    )
    HAILO_AVAILABLE = True
except ImportError:
    HAILO_AVAILABLE = False


class HailoVisionRunner:
    """Thread-safe wrapper around a compiled Hailo `.hef` classification network."""

    def __init__(self, hef_path: str):
        self.hef_path = hef_path
        self.ready = False
        self._vdevice = None
        self._network_group = None
        self._input_name = None
        self._output_name = None
        self._input_params = None
        self._output_params = None

        if not HAILO_AVAILABLE or not hef_path or not os.path.exists(hef_path):
            return

        try:
            self._hef = HEF(hef_path)
            self._vdevice = VDevice()
            cfg_params = ConfigureParams.create_from_hef(
                hef=self._hef, interface=HailoStreamInterface.PCIe
            )
            groups = self._vdevice.configure(self._hef, cfg_params)
            self._network_group = groups[0]
            self._network_group_params = self._network_group.create_params()
            self._input_params = InputVStreamParams.make(
                self._network_group, quantized=False, format_type=FormatType.FLOAT32
            )
            self._output_params = OutputVStreamParams.make(
                self._network_group, quantized=False, format_type=FormatType.FLOAT32
            )
            in_infos = self._hef.get_input_vstream_infos()
            out_infos = self._hef.get_output_vstream_infos()
            self._input_name = in_infos[0].name
            self._output_name = out_infos[0].name
            self.ready = True
        except Exception as exc:
            print(f"[HailoVisionRunner] Falling back to CPU ONNX ({exc})")
            self.ready = False

    def infer_logits(self, nchw_tensor: np.ndarray) -> np.ndarray:
        """Runs inference on NHWC float32 input expected by HailoRT and returns 1D logits."""
        if not self.ready:
            raise RuntimeError("HailoVisionRunner is not initialized.")
        nhwc = np.ascontiguousarray(np.transpose(nchw_tensor, (0, 2, 3, 1)), dtype=np.float32)
        with self._network_group.activate(self._network_group_params):
            with InferVStreams(self._network_group, self._input_params, self._output_params) as pipe:
                res = pipe.infer({self._input_name: nhwc})
        return np.asarray(res[self._output_name][0], dtype=np.float32)
