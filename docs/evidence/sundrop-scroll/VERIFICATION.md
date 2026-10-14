# SunDrop scroll repair — 14 October 2026

The user clarified that the problem was repeated/garbled text when scrolling the downloader, rather than a failed YouTube download.

Replaced CTkScrollableFrame's canvas-window movement with a clipped native child-frame viewport in both the downloader and player. Wheel bursts are coalesced to one movement per 16 ms; scrollbar dragging uses the same bounded position. Removed independent styling of composite controls' internal buttons, which could disagree with the composite's font/width calculations. Static playback labels and control states now update only when their values change.

The existing colors, cards, menus, inputs, download actions, library and player remain. No operating-system/GPU settings were changed. Background network operations still communicate through the Tk event queue.

Actual Tk verification sent 160 wheel events in Light and Dark modes, preserved the URL, permission state and format selection, and reported no callback errors. Before/after images at the same position differed by less than 1% of pixels above the comparison threshold. Screenshots include intermediate scrolling views and settled views. All 85 Python tests passed.

The precise user's Windows/driver contribution is not proven. The change removes the canvas scroll path implicated in the toolkit's [reported visual scrolling bug](https://github.com/TomSchimansky/CustomTkinter/issues/1510). User verification of repeated scrolling remains the final check.

A separate YouTube diagnostic on the earlier RADHA link successfully extracted formats and fetched a small video sample. It warned about missing JS runtime setup, and the installed pip package lacked optional EJS components. The default extras were installed locally during investigation; this was not identified as the cause of the user's visual glitch.
