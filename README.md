# comfyui-audiostuff

Small audio helper nodes for ComfyUI.

## Ensure Video Audio (audiostuff)

Connect the `audio` and `video_info` outputs of a VideoHelperSuite **Load Video** node.

| Output | Meaning |
| --- | --- |
| `audio` | The source audio unchanged, or silence as long as the loaded clip if there is none |
| `has_source_audio` | `True` only if the video had a readable, non-empty audio track |
| `status` | One line explaining what happened |

Feed `has_source_audio` into a switch node to skip audio-dependent branches for silent videos.

### Compatibility patch

Recent ComfyUI versions scan every linked output for models (`PromptModelTracker`), which
forces VHS's lazy audio to load immediately and crashes on videos without an audio track,
before any downstream node can handle it. On load, this pack makes the tracker skip VHS audio
that hasn't been loaded yet (it can't contain models). See `compat.py`. As a side effect, VHS
audio is no longer decoded until a node actually reads it.

## Install

Clone into `ComfyUI/custom_nodes` and restart ComfyUI. No extra dependencies.

## License

Public domain under the [Unlicense](LICENSE).
