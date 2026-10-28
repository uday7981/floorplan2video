# workers/image — OpenAI image edit → photoreal end frames

Queue `end_frame`. Sends `clay.png` plus the shot-type prompt to OpenAI's image
edit endpoint at 1280×720 (or closest supported size, then crop). Writes to
`frames/`, logs est and actual cost. Built in **M3**.
