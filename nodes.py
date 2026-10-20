"""Audio helper nodes for ComfyUI."""

import math

import torch


def _positive_float(value):
    """Return value as a finite positive float, or None."""
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if math.isfinite(number) and number > 0:
        return number
    return None


def _duration_from_video_info(video_info):
    """Work out the clip length in seconds from a VHS video_info dict.

    The loaded_* values come first because they reflect frame caps and
    skipped frames, which is what the loaded audio (if any) is trimmed to.
    """
    if not isinstance(video_info, dict):
        raise ValueError("video_info must be the video_info output of a VHS Load Video node.")

    for key in ("loaded_duration", "source_duration"):
        seconds = _positive_float(video_info.get(key))
        if seconds:
            return seconds

    for frames_key, fps_key in (("loaded_frame_count", "loaded_fps"),
                                ("source_frame_count", "source_fps")):
        frames = _positive_float(video_info.get(frames_key))
        fps = _positive_float(video_info.get(fps_key))
        if frames and fps:
            return frames / fps

    raise ValueError("video_info does not contain a usable duration.")


def _read_audio(audio):
    """Read an AUDIO input, returning (waveform, sample_rate) or raising.

    VHS hands out a lazy mapping that only runs ffmpeg when it is first
    indexed, and that call raises if the file has no audio stream. Reading
    it here, inside the caller's try block, turns that into a clean result.
    """
    if audio is None:
        raise ValueError("no audio input")
    waveform = audio["waveform"]
    sample_rate = int(audio["sample_rate"])
    if not isinstance(waveform, torch.Tensor) or waveform.dim() != 3:
        raise ValueError("waveform is not a [batch, channels, samples] tensor")
    if waveform.shape[-1] == 0:
        raise ValueError("audio contains no samples")
    if sample_rate <= 0:
        raise ValueError(f"invalid sample rate {sample_rate}")
    return waveform, sample_rate


class EnsureVideoAudio:
    """Pass a video's audio through, or substitute silence of the same length."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "audio": ("AUDIO",),
                "video_info": ("VHS_VIDEOINFO",),
                "fallback_sample_rate": ([44100, 48000, 32000, 22050, 16000], {"default": 44100}),
                "fallback_channels": ("INT", {"default": 2, "min": 1, "max": 8, "step": 1}),
            }
        }

    RETURN_TYPES = ("AUDIO", "BOOLEAN", "STRING")
    RETURN_NAMES = ("audio", "has_source_audio", "status")
    FUNCTION = "run"
    CATEGORY = "audiostuff"
    DESCRIPTION = (
        "Reports whether the source video has usable audio. Passes that audio through "
        "unchanged if so; otherwise outputs silence matching the video's duration."
    )

    def run(self, audio, video_info, fallback_sample_rate=44100, fallback_channels=2):
        try:
            waveform, sample_rate = _read_audio(audio)
        except Exception as error:
            reason = " ".join(str(error).split()) or type(error).__name__
            if len(reason) > 300:
                reason = reason[:297] + "..."
        else:
            seconds = waveform.shape[-1] / sample_rate
            status = f"Source audio found: {seconds:.3f}s, {waveform.shape[1]} ch, {sample_rate} Hz."
            return ({"waveform": waveform, "sample_rate": sample_rate}, True, status)

        seconds = _duration_from_video_info(video_info)
        rate = int(fallback_sample_rate)
        channels = int(fallback_channels)
        samples = max(1, round(seconds * rate))
        silence = torch.zeros((1, channels, samples), dtype=torch.float32)
        status = (f"No usable source audio ({reason}). "
                  f"Generated {seconds:.3f}s of {channels}-ch silence at {rate} Hz.")
        print(f"[audiostuff] {status}")
        return ({"waveform": silence, "sample_rate": rate}, False, status)


NODE_CLASS_MAPPINGS = {
    "AudioStuff_EnsureVideoAudio": EnsureVideoAudio,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "AudioStuff_EnsureVideoAudio": "Ensure VHS Audio",
}
