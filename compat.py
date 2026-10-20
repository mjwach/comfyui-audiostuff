"""Compatibility patch between ComfyUI's PromptModelTracker and VHS lazy audio.

Recent ComfyUI versions walk every linked node output with
PromptModelTracker.add(), calling .values() on anything that is a Mapping,
to find models in use. VideoHelperSuite's audio output is a LazyAudioMap
whose first access runs ffmpeg, and that raises when the video has no audio
stream. The result is a crash before any downstream node (including
Ensure Video Audio) can handle the missing audio.

Unloaded lazy audio cannot contain models, so this patch makes the tracker
skip it. The audio is then loaded by whichever node actually reads it,
where the error can be handled. Nothing else about the tracker changes.
"""

import functools
import logging

log = logging.getLogger("audiostuff")


def _is_unloaded_vhs_audio(obj):
    # Matched by name so this works whatever order custom nodes load in.
    cls = type(obj)
    return (cls.__name__ == "LazyAudioMap"
            and "videohelpersuite" in (cls.__module__ or "").lower()
            and getattr(obj, "_dict", True) is None)


def apply():
    try:
        from comfy.model_patcher import PromptModelTracker
    except Exception:
        return  # Older ComfyUI without the tracker: nothing to patch.

    original = PromptModelTracker.add
    if getattr(original, "_audiostuff_patched", False):
        return

    @functools.wraps(original)
    def add(self, outputs):
        if _is_unloaded_vhs_audio(outputs):
            return
        return original(self, outputs)

    add._audiostuff_patched = True
    PromptModelTracker.add = add
    log.info("[audiostuff] Patched PromptModelTracker to leave VHS lazy audio unloaded.")
