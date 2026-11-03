# Training workspace workflow

- The canonical presentation is `training_v2/slides/QB560D_EU_Training.pptx`. Always open and inspect its latest contents before an edit. Preserve manual additions, unrelated text, artwork, formatting, notes, slide order and structure.
- Before editing, save a dated backup under `training_v2/.build/pptx-backups/`. Validate a separate candidate and confirm that the canonical file has not changed before replacing it.
- The official reference is `training_v2/slides/fontes/Quectel-corporate-PPT-template-2026-EN.pptx`; preserve its bytes. Yocto and Docker source presentations are also in `slides/fontes`, outside the student release.
- Slide count is not fixed. Preserve the current count unless the requested edit adds or removes slides. Historical JSON and generation scripts in `archive/slide_generation` must never overwrite the current presentation.
- `training_v2/README.md` is the single training entry point. Host commands start in `training_v2`. Resolve code, model and tool locations from the script path, independently of the current working directory.
- Shared ADB transports are in `training_v2/host`; the portable Windows client is in `training_v2/tools/platform-tools`. Core training must not import transport code from a demo.
- Provisioning is in `training_v2/provision_target`, QAIRT support in `training_v2/runtimes/qairt_2_51`, gestures in `training_v2/demos/hand_gesture`, Docker in `training_v2/demos/docker`, and AI Hub in `training_v2/Qualcomm_AI_Hub_Training`.
- Yocto is lecture-only. Do not execute build/setup labs as part of the Yocto module.
- Host reorganization does not authorize changing the target's `/opt` paths, firmware, modem or network state. Preserve existing ownership identifiers, runtime/model locks and historical evidence.
- Regenerate provisioning bundles/plans after changing their sources. Never update asset hashes merely to silence a mismatch. Recreate virtual environments at their destination; do not distribute `.venv`.
- `host/build_release.py` creates complete versioned packages under `dist/`. Exclude development builds, virtual environments, raw caches beyond locked runtime inputs, historical releases, authoring sources and firmware. Validate a fresh extraction independently of the working tree.
