# Die Donut Clique – Social Media

Post images for the Instagram account [@donut.clique](https://instagram.com/donut.clique), the story game
[Die Donut Clique](https://steffenschaffhausen.com/?sjs_game=donut-clique) by Steffen Schaffhausen.

| Folder | What |
|---|---|
| `templates/pop.html` | pop-art comic components (bursts, halftone, rays, balloons) in the game's colours and fonts |
| `templates/render-pop.js` | renders `posts.json`: carousels and singles as PNG (1080×1350), reels as MP4 (1080×1920, 30 fps) |
| `templates/portraits.json`, `templates/scenes.json` | the clique's portraits and the game's backgrounds (without the player's own figure) |
| `posts/<nr>-<slug>/` | one folder per post: `slide-N.png` or `reel.mp4` + `cover.png`, and `caption.md` |

| `templates/sound.py` | original soundtrack for the reels: 160 BPM beat in F minor plus comic sound effects synced to the animation (numpy/scipy, no samples) |

Render: `node templates/render-pop.js [id ...]`, then `python3 templates/sound.py [id ...]` for the reels (needs Playwright with Chromium and ffmpeg).

Planning and approval live in Notion (Redaktionsplan). Publishing runs through Buffer, scheduled
once a week after approval.
