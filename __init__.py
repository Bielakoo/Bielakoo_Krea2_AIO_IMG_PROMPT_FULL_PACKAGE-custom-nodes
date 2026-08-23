from __future__ import annotations
import math
import torch
import comfy.model_management


class BielakooAIOAutoResolution:
    """Create an EmptySD3-style target latent from the BASE IMAGE aspect ratio.

    The source image itself is not resampled here. Krea2EditModelPatch keeps using its
    recommended pixel path (vae + source_image + target_latent) and performs the
    training-matched fit. This node only chooses a stable output canvas automatically.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image": ("IMAGE",),
                "target_megapixels": ("FLOAT", {"default": 1.6, "min": 0.75, "max": 3.0, "step": 0.05}),
                "min_short_side": ("INT", {"default": 1024, "min": 512, "max": 1536, "step": 32}),
                "max_long_side": ("INT", {"default": 2048, "min": 1024, "max": 4096, "step": 32}),
                "multiple": ("INT", {"default": 32, "min": 16, "max": 128, "step": 16}),
            }
        }

    RETURN_TYPES = ("LATENT", "INT", "INT", "STRING")
    RETURN_NAMES = ("LATENT", "width", "height", "summary")
    FUNCTION = "make"
    CATEGORY = "Bielakoo/Krea2 AIO"

    @staticmethod
    def _round_mult(v: float, mult: int) -> int:
        return max(mult, int(round(float(v) / mult)) * mult)

    @classmethod
    def calculate_canvas(cls, w: int, h: int, target_megapixels: float, min_short_side: int, max_long_side: int, multiple: int):
        mult = max(16, int(multiple))
        min_short = max(mult, int(min_short_side))
        max_long = max(min_short, int(max_long_side))
        target_px = max(0.25, float(target_megapixels)) * 1_000_000.0

        short = min(w, h)
        long = max(w, h)
        scale_mp = math.sqrt(target_px / float(w * h))
        scale_min = min_short / float(short)
        scale = max(scale_mp, scale_min)
        scale = min(scale, max_long / float(long))

        nw = cls._round_mult(w * scale, mult)
        nh = cls._round_mult(h * scale, mult)

        if max(nw, nh) > max_long:
            s2 = max_long / float(max(nw, nh))
            nw = cls._round_mult(nw * s2, mult)
            nh = cls._round_mult(nh * s2, mult)
            if max(nw, nh) > max_long:
                if nw >= nh:
                    nw = (max_long // mult) * mult
                    nh = cls._round_mult(nw * h / float(w), mult)
                else:
                    nh = (max_long // mult) * mult
                    nw = cls._round_mult(nh * w / float(h), mult)
        return nw, nh

    def make(self, image, target_megapixels=1.6, min_short_side=1024, max_long_side=2048, multiple=32):
        if image is None or not hasattr(image, "shape") or len(image.shape) != 4:
            raise ValueError("Bielakoo Auto Resolution: invalid BASE IMAGE tensor.")

        h = int(image.shape[1])
        w = int(image.shape[2])
        batch = int(image.shape[0])
        if w < 1 or h < 1:
            raise ValueError("Bielakoo Auto Resolution: BASE IMAGE has invalid dimensions.")

        nw, nh = self.calculate_canvas(w, h, target_megapixels, min_short_side, max_long_side, multiple)
        mult = max(16, int(multiple))
        max_long = max(int(min_short_side), int(max_long_side))

        latent = torch.zeros(
            [batch, 16, nh // 8, nw // 8],
            device=comfy.model_management.intermediate_device(),
            dtype=comfy.model_management.intermediate_dtype(),
        )
        actual_mp = (nw * nh) / 1_000_000.0
        src_mp = (w * h) / 1_000_000.0
        action = "UP" if actual_mp > src_mp * 1.03 else ("DOWN" if actual_mp < src_mp * 0.97 else "KEEP")
        summary = (
            f"AUTO {action}: BASE {w}x{h} ({src_mp:.2f} MP) -> "
            f"KREA2 {nw}x{nh} ({actual_mp:.2f} MP) | grid {mult} | max long {max_long}"
        )
        print("[BielakooAIOAutoResolution] " + summary, flush=True)
        return {"ui": {"text": [summary]}, "result": ({"samples": latent, "downscale_ratio_spacial": 8}, nw, nh, summary)}


class BielakooAIOResolutionCalculator:
    """Interactive helper for choosing Auto Resolution values from source dimensions.

    Enter the BASE image width/height and a quality profile. The calculator uses the
    exact same 32-grid sizing logic as BielakooAIOAutoResolution, then returns values
    that can be copied directly into the Auto Resolution node.
    """

    PROFILES = {
        "FAST / 1792": (1.30, 960, 1792),
        "BALANCED / 1920": (1.60, 1056, 1920),
        "QUALITY / 2048": (1.90, 1088, 2048),
        "HIGH QUALITY / 2304": (2.36, 1152, 2304),
        "MAX DETAIL / 2560": (2.60, 1216, 2560),
    }

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "source_width": ("INT", {"default": 736, "min": 64, "max": 16384, "step": 1}),
                "source_height": ("INT", {"default": 1380, "min": 64, "max": 16384, "step": 1}),
                "quality_profile": (list(cls.PROFILES.keys()), {"default": "BALANCED / 1920"}),
                "multiple": ("INT", {"default": 32, "min": 16, "max": 128, "step": 16}),
            }
        }

    RETURN_TYPES = ("INT", "INT", "FLOAT", "INT", "INT", "INT", "STRING")
    RETURN_NAMES = (
        "recommended_width", "recommended_height", "target_megapixels",
        "min_short_side", "max_long_side", "multiple", "summary"
    )
    FUNCTION = "calculate"
    CATEGORY = "Bielakoo/Krea2 AIO"
    OUTPUT_NODE = True

    def calculate(self, source_width=736, source_height=1380, quality_profile="BALANCED / 1920", multiple=32):
        w = int(source_width)
        h = int(source_height)
        if w < 1 or h < 1:
            raise ValueError("Bielakoo Resolution Calculator: width and height must be positive.")

        profile_mp, profile_min, profile_max = self.PROFILES.get(
            quality_profile, self.PROFILES["BALANCED / 1920"]
        )
        nw, nh = BielakooAIOAutoResolution.calculate_canvas(
            w, h, profile_mp, profile_min, profile_max, int(multiple)
        )

        actual_mp = (nw * nh) / 1_000_000.0
        src_mp = (w * h) / 1_000_000.0
        rec_min = min(nw, nh)
        rec_max = max(nw, nh)
        mult = int(multiple)
        ar_src = w / float(h)
        ar_work = nw / float(nh)
        ar_err = abs(ar_work - ar_src) / max(abs(ar_src), 1e-9) * 100.0

        summary = (
            f"BASE {w}x{h} ({src_mp:.2f} MP) -> BEST {nw}x{nh} ({actual_mp:.2f} MP) | "
            f"profile {quality_profile} | 32-grid AR error {ar_err:.2f}%\n"
            f"COPY TO AUTO RESOLUTION: target_megapixels={actual_mp:.2f} | "
            f"min_short_side={rec_min} | max_long_side={rec_max} | multiple={mult}"
        )
        print("[BielakooAIOResolutionCalculator] " + summary.replace("\n", " | "), flush=True)
        return {
            "ui": {"text": [summary]},
            "result": (nw, nh, round(actual_mp, 2), rec_min, rec_max, mult, summary),
        }


NODE_CLASS_MAPPINGS = {
    "BielakooAIOAutoResolution": BielakooAIOAutoResolution,
    "BielakooAIOResolutionCalculator": BielakooAIOResolutionCalculator,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "BielakooAIOAutoResolution": "Bielakoo Krea2 AIO Auto Resolution",
    "BielakooAIOResolutionCalculator": "Bielakoo Krea2 AIO Resolution Calculator",
}


# Frontend extension used to show calculator results directly inside the node.
WEB_DIRECTORY = "./web"

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS", "WEB_DIRECTORY"]
