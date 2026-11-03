import importlib.util
import io
import json
from pathlib import Path
import subprocess
import sys
import threading
import unittest
import urllib.error
import urllib.request
import zipfile
from unittest import mock

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "ai"))
from run_demo import prepare_input, dequantize, postprocess, finger_state
from fetch_models import member
sys.path.insert(0, str(ROOT / "host"))
from adb_lab import remote_exit_status, select_device, marked_command


class ModelContracts(unittest.TestCase):
    def test_raw_rgb_quantized_input_preserves_pixels(self):
        image = Image.fromarray(np.array([[[0, 128, 255]]], dtype=np.uint8))
        result = prepare_input(image, {"input_kind": "raw"}, {"dtype": np.uint8})
        np.testing.assert_equal(result, np.array([[[[0, 128, 255]]]], dtype=np.uint8))

    def test_normalization_and_quantization(self):
        image = Image.fromarray(np.array([[[0, 128, 255]]], dtype=np.uint8))
        result = prepare_input(image, {"input_kind": "normalized", "mean": 128, "std": 128}, {"dtype": np.int8, "quantization": (1 / 128, 0)})
        np.testing.assert_equal(result, np.array([[[[-128, 0, 127]]]], dtype=np.int8))

    def test_dequantized_scores(self):
        result = dequantize(np.array([0, 128, 255], dtype=np.uint8), {"quantization": (1 / 256, 0)})
        np.testing.assert_allclose(result, [0, 0.5, 255 / 256])

    def test_detection_threshold_and_background_offset(self):
        tensors = [np.array([[[0.1, 0.2, 0.8, 0.9], [0, 0, 1, 1]]]), np.array([[0, 1]]), np.array([[0.9, 0.1]]), np.array([2])]
        profile = {"outputs": {"boxes": 0, "classes": 1, "scores": 2, "count": 3}, "label_offset": 1}
        result = postprocess("detection", tensors, profile, ["???", "person", "bicycle"], 0.5)
        self.assertEqual(len(result["detections"]), 1)
        self.assertEqual(result["detections"][0]["label"], "person")

    def test_posenet_offsets_use_model_dimensions(self):
        heatmap = np.full((1, 3, 3, 17), -10.0)
        heatmap[0, 1, 2, :] = 10
        offsets = np.zeros((1, 3, 3, 34))
        offsets[0, 1, 2, :17] = 2
        profile = {"outputs": {"heatmaps": 0, "offsets": 1}, "size": [257, 353]}
        result = postprocess("pose", [heatmap, offsets], profile, [], 0.5)
        self.assertAlmostEqual(result["keypoints_yxs"][0][0], 178 / 353)
        self.assertAlmostEqual(result["keypoints_yxs"][0][1], 256 / 257)
        self.assertEqual(result["visible_keypoints"], 17)

    def test_low_presence_does_not_claim_gesture(self):
        result = postprocess("gesture", [np.zeros((1, 63)), np.array([[0.1]])], {"outputs": {"landmarks": 0, "presence": 1}}, [], 0.5)
        self.assertEqual(result["gesture"], "no_hand")

    def test_open_hand_rule(self):
        points = np.zeros((21, 3))
        for tip, pip in ((8, 6), (12, 10), (16, 14), (20, 18)):
            points[pip, 1] = 1
            points[tip, 1] = 2
        self.assertEqual(finger_state(points)["gesture"], "open_hand")

    def test_segmentation_argmax_and_shape(self):
        mask = np.zeros((1, 257, 257, 21))
        mask[:, :128, :, 15] = 0.9
        profile = {"outputs": {"mask": 0}, "class_labels": [str(i) for i in range(21)]}
        result = postprocess("segmentation", [mask], profile, [], 0.5)
        self.assertAlmostEqual(result["foreground_fraction"], 128 / 257)
        with self.assertRaises(ValueError):
            postprocess("segmentation", [np.zeros((1, 8, 8, 1))], profile, [], 0.5)

    def test_archive_reads_only_exact_member(self):
        payload = io.BytesIO()
        with zipfile.ZipFile(payload, "w") as archive:
            archive.writestr("model.tflite", b"safe")
            archive.writestr("../outside.txt", b"not extracted")
        self.assertEqual(member(payload.getvalue(), "sample.zip", "model.tflite"), b"safe")
        with self.assertRaises(KeyError):
            member(payload.getvalue(), "sample.zip", "missing")


class ApplicationHTTP(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        spec = importlib.util.spec_from_file_location("telemetry", ROOT / "app" / "telemetry.py")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        cls.server = mod.ThreadingHTTPServer(("127.0.0.1", 0), mod.Handler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.base = "http://127.0.0.1:" + str(cls.server.server_port)

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()

    def test_health_and_telemetry(self):
        with urllib.request.urlopen(self.base + "/health") as response:
            self.assertEqual(json.load(response), {"status": "ok"})
        with urllib.request.urlopen(self.base + "/telemetry") as response:
            body = json.load(response)
        self.assertEqual(body["application"], "qb560d-training")
        self.assertGreaterEqual(body["process_uptime_s"], 0)

    def test_unknown_route_returns_404(self):
        with self.assertRaises(urllib.error.HTTPError) as error:
            urllib.request.urlopen(self.base + "/missing")
        self.assertEqual(error.exception.code, 404)


class LegacyADB(unittest.TestCase):
    def test_remote_failure_survives_local_adb_success(self):
        self.assertEqual(remote_exit_status(0, b"log\r\n__QB560D_EXIT__=78\r\n"), 78)
        self.assertEqual(remote_exit_status(0, b"log\r\r\n__QB560D_EXIT__=0\r\r\n"), 0)
        self.assertEqual(remote_exit_status(0, b"missing marker"), 1)
        self.assertEqual(remote_exit_status(2, b"__QB560D_EXIT__=0\n"), 2)

    def test_unknown_serial_uses_transport(self):
        with mock.patch("adb_lab.subprocess.check_output", return_value="List of devices attached\n? device product:qcm6490-Ubuntu transport_id:1\n"):
            self.assertEqual(select_device("adb", None), ["-t", "1"])

    def test_multiple_devices_are_rejected(self):
        with mock.patch("adb_lab.subprocess.check_output", return_value="List of devices attached\na device transport_id:1\nb device transport_id:2\n"):
            with self.assertRaises(ValueError):
                select_device("adb", None)


if __name__ == "__main__":
    unittest.main()
