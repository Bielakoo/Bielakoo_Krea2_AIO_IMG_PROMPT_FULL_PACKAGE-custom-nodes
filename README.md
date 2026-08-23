# ComfyUI-BielakooAIOAutoResolution

Custom ComfyUI helper nodes created for the **Bielakoo Krea2 AIO IMG + Prompt Maker** workflow.

## Included nodes

### Bielakoo Krea2 AIO Auto Resolution
ComfyUI node type: `BielakooAIOAutoResolution`

Automatically creates a target latent canvas from the aspect ratio of the source image. It calculates a stable Krea2-oriented working resolution using target megapixels, minimum short side, maximum long side and a configurable grid multiple.

### Bielakoo Krea2 AIO Resolution Calculator
ComfyUI node type: `BielakooAIOResolutionCalculator`

Interactive helper that calculates recommended width, height and Auto Resolution settings from the source image dimensions and a selected quality profile.

Available profiles in the current version include:

- FAST / 1792
- BALANCED / 1920
- QUALITY / 2048
- HIGH QUALITY / 2304
- MAX DETAIL / 2560

The repository also contains the small frontend JavaScript extension used to display calculator results directly inside the node.

## Installation

Clone this repository directly into your ComfyUI `custom_nodes` directory.

### RunPod / Linux

```bash
cd /workspace/runpod-slim/ComfyUI/custom_nodes
git clone https://github.com/Bielakoo/ComfyUI-BielakooAIOAutoResolution.git
```

Then restart ComfyUI.

If your ComfyUI installation is in another location, clone the repository into that installation's `custom_nodes` directory instead.

## Updating

```bash
cd /workspace/runpod-slim/ComfyUI/custom_nodes/ComfyUI-BielakooAIOAutoResolution
git pull --ff-only
```

Restart ComfyUI after updating.

## Dependencies

No additional Python dependencies are required beyond the PyTorch and ComfyUI modules already present in a working ComfyUI installation.

This repository contains only the Bielakoo-authored Auto Resolution helper nodes. Other third-party nodes used by the complete Krea2 AIO workflow remain separate dependencies and should be installed from their original repositories.
