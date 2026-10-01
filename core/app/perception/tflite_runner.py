import os
from typing import Optional, Dict, Any, Tuple
import numpy as np
import cv2
from app.logger import logger

class TFLiteInferenceRunner:
    def __init__(self, model_path: Optional[str] = None) -> None:
        self.model_path = model_path
        self._interpreter = None
        self._input_details = None
        self._output_details = None
        self.is_quantized = False
        self._init_runner()

    def _init_runner(self) -> None:
        if self.model_path and os.path.exists(self.model_path):
            try:
                try:
                    import tflite_runtime.interpreter as tflite
                    self._interpreter = tflite.Interpreter(model_path=self.model_path)
                except ImportError:
                    import tensorflow as tf
                    self._interpreter = tf.lite.Interpreter(model_path=self.model_path)
                self._interpreter.allocate_tensors()
                self._input_details = self._interpreter.get_input_details()
                self._output_details = self._interpreter.get_output_details()
                input_dtype = self._input_details[0]["dtype"]
                self.is_quantized = input_dtype in (np.int8, np.uint8)
                logger.info(f"Loaded TFLite model from {self.model_path} (quantized={self.is_quantized})")
                return
            except Exception as e:
                logger.warning(f"Failed to load model {self.model_path}: {e}. Falling back to simulation runner.")
        self._interpreter = None
        self.is_quantized = True

    def preprocess(
        self,
        image: np.ndarray,
        target_size: Tuple[int, int] = (48, 48),
        grayscale: bool = True
    ) -> np.ndarray:
        if image is None or image.size == 0:
            raise ValueError("Input image is empty")
        if grayscale and len(image.shape) == 3:
            processed = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        elif not grayscale and len(image.shape) == 2:
            processed = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
        else:
            processed = image.copy()
        resized = cv2.resize(processed, target_size, interpolation=cv2.INTER_AREA)
        if len(resized.shape) == 2:
            resized = np.expand_dims(resized, axis=-1)
        tensor = np.expand_dims(resized, axis=0)
        if self._input_details:
            scale, zero_point = self._input_details[0].get("quantization", (0.0, 0))
            dtype = self._input_details[0]["dtype"]
            if self.is_quantized and scale > 0:
                normalized = tensor.astype(np.float32) / 255.0
                quantized = (normalized / scale + zero_point).astype(dtype)
                return quantized
            return (tensor.astype(np.float32) / 255.0).astype(dtype)
        if self.is_quantized:
            return tensor.astype(np.int8)
        return tensor.astype(np.float32) / 255.0

    def infer(self, input_tensor: np.ndarray) -> np.ndarray:
        if self._interpreter is not None and self._input_details and self._output_details:
            self._interpreter.set_tensor(self._input_details[0]["index"], input_tensor)
            self._interpreter.invoke()
            output = self._interpreter.get_tensor(self._output_details[0]["index"])
            scale, zero_point = self._output_details[0].get("quantization", (0.0, 0))
            if self.is_quantized and scale > 0:
                return (output.astype(np.float32) - zero_point) * scale
            return output
        seed = int(np.sum(input_tensor)) % 100
        np.random.seed(seed)
        dummy_logits = np.random.uniform(0.1, 0.9, size=(1, 7))
        exp_logits = np.exp(dummy_logits - np.max(dummy_logits))
        return exp_logits / np.sum(exp_logits)

    def get_model_info(self) -> Dict[str, Any]:
        if self._interpreter is not None and self._input_details and self._output_details:
            return {
                "loaded": True,
                "model_path": self.model_path,
                "input_shape": self._input_details[0]["shape"].tolist(),
                "input_dtype": str(self._input_details[0]["dtype"]),
                "output_shape": self._output_details[0]["shape"].tolist(),
                "output_dtype": str(self._output_details[0]["dtype"]),
                "is_quantized": self.is_quantized
            }
        return {
            "loaded": False,
            "model_path": self.model_path,
            "input_shape": [1, 48, 48, 1],
            "input_dtype": "int8",
            "output_shape": [1, 7],
            "output_dtype": "float32",
            "is_quantized": True
        }
