# SunDrop video and music playback update — 14 October 2026

The earlier download was M4A, which contains audio and cannot show the video's picture. SunDrop selected the source's first available format and grouped its menu by extension. Separate video-only source streams were hidden. The built-in player also only played WAV, MP3 and OGG.

The format menu now clearly separates **Video** and **Audio only** and prefers video when available. Video quality entries show their resolution. When a source provides picture and sound separately, SunDrop combines the selected video with an appropriate audio stream using FFmpeg. FFprobe checks the resulting streams before the file is recorded as a completed video. If the source unexpectedly saves audio without video, the app explains the failure and keeps the file. Existing M4A downloads remain usable audio; download a Video option to get the picture.

The integrated player opens local video and audio files, with play/pause, previous/next library navigation, volume and seeking. Normal, Pixel and ASCII are optional display effects for actual video frames. They do not re-encode or change the saved file. Open File still launches the system player; File and Open local video / audio open files in SunDrop.

Music playback uses the exact MP4 supplied by the user as a muted looping visual. It pauses with the song. The visual's own audio is disabled so the selected music is the only audio output. The optional checkbox turns it off. No replacement CD artwork was generated. The copied asset `sundrop/assets/music-cd-reference.mp4` has SHA-256 `20b07c7fed35905b8c9221f62e19769d4f69eca2d20a4f568b9a0b91b070b96d`, matching the supplied original.

The GUI uses FFpyplayer for both audio and video. Mixing its SDL libraries with pygame in the same Windows GUI process caused version conflicts during development. The old standalone AudioPlayer API is retained, but the GUI uses one decoder family. Mono/stereo playback is normalized in memory, and the UI avoids reading an uninitialized native audio clock. Neither normalization nor effects write to the original file.

## Testing

- 85 Python tests passed: 42 SunDrop and 43 MathDuel.
- Actual local HTTP downloads tested separate video/audio merging, stream validation, corrupt selections, existing conversion and source-file preservation.
- Playback tests exercised decoded frames, pause, seek, volume, optional effects and the exact muted reference asset.
- Tk visual verification used the supplied video, captured Normal/Pixel/ASCII and music-reference views, checked displayed frames, pause and seeking, and confirmed unchanged source SHA-256. Screenshots are under `docs/evidence/sundrop-video/`.
- Audible output and the user's chosen online source still need the joint manual check. Automated tests do not claim human listening or a successful new download from YouTube/Instagram.

Install the updated requirements with `python -m pip install -r sundrop/requirements.txt`. FFmpeg/FFprobe are needed for merging and stream validation. FFpyplayer provides the integrated playback decoder. Reference: [FFpyplayer's official player documentation](https://matham.github.io/ffpyplayer/player.html).

## Test together

1. Play the existing M4A from Library. Confirm you hear your song and see the provided CD clip moving, without the clip's own audio.
2. Pause and resume. Both music and CD motion should pause and resume.
3. Fetch an authorized video URL, choose **Video · MP4**, select a resolution, and download. Play the new file in SunDrop and confirm picture and sound.
4. Switch Normal → Pixel → ASCII → Normal. The saved file remains unchanged.
