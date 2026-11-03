# Technical references and asset provenance

Reviewed 31 October 2026. User-provided hardware/OS evidence takes precedence over generic marketing assumptions for this unit.

- Hardware identity and Ubuntu 20.04.3: owner statement and `/etc/os-release` pasted into this chat. Kernel, BSP and installed runtime versions remain unmeasured.
- Corporate slide design and artwork: `Quectel-corporate-PPT-template-2026-EN.pptx`, supplied in the workspace. Arial typography, official colors (#FA0505 red, #210079 blue), cover and section artwork come from this file. The saved viewer deck preserves corporate artwork as backgrounds and uses editable training text/tables. It does not import the original PowerPoint masters as editable master objects.
- Qualcomm Workbench overview: https://workbench.aihub.qualcomm.com/docs/
- Compile job API/examples: https://workbench.aihub.qualcomm.com/docs/hub/compile_examples.html
- Profile job API: https://workbench.aihub.qualcomm.com/docs/hub/generated/qai_hub.submit_profile_job.html
- Hosted devices and deployment: https://workbench.aihub.qualcomm.com/docs/hub/deployment.html
- Qualcomm MobileNet V2 reference model: https://github.com/qualcomm/ai-hub-models/blob/main/qai_hub_models/models/mobilenet_v2/README.md
- Qualcomm PoseNet reference model: https://github.com/qualcomm/ai-hub-models/blob/main/qai_hub_models/models/posenet_mobilenet/README.md
- TensorFlow Lite model links and baseline models: https://github.com/tensorflow/tensorflow/blob/master/tensorflow/lite/g3doc/android/delegates/nnapi.md
- MediaPipe official models: https://github.com/google-ai-edge/mediapipe/blob/master/docs/solutions/models.md
- Hand model tensor processing: https://github.com/google-ai-edge/mediapipe/blob/master/mediapipe/modules/hand_landmark/hand_landmark_cpu.pbtxt
- Hand landmark task and its complete palm-detector pipeline: https://developers.google.com/edge/mediapipe/solutions/vision/hand_landmarker
- Linux RMNET: https://www.kernel.org/doc/html/latest/networking/device_drivers/cellular/qualcomm/rmnet.html
- Docker host networking: https://docs.docker.com/engine/network/drivers/host/
- systemd unit behavior: https://www.freedesktop.org/software/systemd/man/latest/systemd.service.html
- Existing QNN runtime documentation: https://docs.qualcomm.com/bundle/publicresource/topics/80-63442-10/htp_backend.html

Baseline model download origins and hashes are recorded in `models/models.lock.json`; per-task URLs and preprocessing are in `ai/profiles.json`. These baseline weights are TensorFlow/MediaPipe reference assets, not QB560D-specific or AI Hub exports. Follow upstream model cards/licenses for redistribution or commercial use. No ownership of third-party weights or corporate artwork is asserted.

Reference inputs: `media/sources.json`. `grace_hopper.jpg` is the portrait distributed in the official TensorFlow sample bucket. `right_hands.jpg` is an official MediaPipe test asset. The demo crops one hand at runtime; the original remains unchanged. The slides now use actual QB560D-EU CPU outputs, labelled with TFLite 2.8.4. JSON files retain execution-platform metadata. Preparation-computer results remain separate.

DeepLabV3 model: https://storage.googleapis.com/download.tensorflow.org/models/tflite/gpu/deeplabv3_257_mv_gpu.tflite . This version replaced the selfie segmentation model after an actual unsupported-custom-op failure on the vendor runtime. The active profile uses 21 Pascal VOC classes and argmax decoding.

Manual cellular RIL: the installed `/usr/bin/qlril-api-test` menu, library202411060822, and the owner's successful71/d transcript are the board-specific evidence. Read [the guide](CELLULAR_RIL.md), [captured menu](../evidence/ril/20261101-manual/menu.txt) and [live summary](../evidence/ril/20261101-manual/summary.json). The [AOSP RIL header](https://android.googlesource.com/device/generic/goldfish/+/bf3559a47ee8a4937035596a0a5c64273bbb0923/radio/ril/ril.h) supplies the registration/RAT enumeration. Quectel's [QLRIL menu example for another board](https://docs.quectel.com/zh/Quectel%20Pi/Quectel%20Pi%20M1_L1/%E4%BD%BF%E7%94%A8%E6%8C%87%E5%8D%97/%E5%AE%9A%E4%BD%8D/%E5%AE%9A%E4%BD%8D.html) is contextual; it does not establish QB560D-EU GNSS support.

Focused NR check: [actual RIL/AT samples and bounded traffic](../evidence/ril/20261101-5g-verification/summary.json). The [Quectel RG50xQ/RM5xxQ AT manual](https://www.quectel.com/content/uploads/2024/05/Quectel_RG50xQRM5xxQ_Series_AT_Commands_Manual_V1.2.pdf), sections 5.5, 5.20 and 5.22, is a reference for 5GS registration/serving-cell/EN-DC formats in another module family, not a support claim for SG560D. The [Cloudflare speedtest project](https://github.com/cloudflare/speedtest) documents the payload endpoint. The local test uses a fixed size and rate limit only to observe radio state during activity.
