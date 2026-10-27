The game draws everything as pixel art. With your own ComfyUI it can paint it all instead. This page covers setting that up and choosing how you, the goddess and Marrow look.

## Pixel art or paintings
Everything has a pixel-art version drawn in the browser: your adventurer in their gear, every item and guardian, the goddess in each mood, Marrow Fennick, the choice characters, and every potion and cosmetic. Without ComfyUI that's the game's art; with ComfyUI it's the stand-in until a painting is ready.

**Art and AI → Art style:** **Painted** uses ComfyUI, and under **Paint** you can leave categories off (they stay pixel art). **Pixel art only** ignores ComfyUI and any saved paintings. While paintings are on, the panel header has a **Paintings / Pixel art** button so each person can choose on their own device.

## Painting with ComfyUI (local, free)
1. Run ComfyUI somewhere Home Assistant can reach it (for example the `comfyui` Docker image on your GPU machine, port 8188).
2. Pick the matching **Model type** under **Art and AI**:
   - **SDXL:** a fantasy-capable SDXL fine-tune (Juggernaut XL, DreamShaper XL) in `models/checkpoints`. The quick choice.
   - **Flux, all-in-one checkpoint:** a single-file Flux dev checkpoint (for example `flux1-dev-fp8.safetensors`) in `models/checkpoints`.
   - **Flux, separate files:** the model in `models/diffusion_models` (for example `flux1-dev.safetensors`), the text encoders `clip_l` and `t5xxl` in `models/text_encoders`, and `ae.safetensors` in `models/vae`. Pick the model in the Checkpoint list; the rest is found automatically, and the form tells you if something's missing.
   - **Custom:** your own workflow, saved with ComfyUI's *Export (API)* as `/config/life_rpg/workflow.json`, with the placeholders `%PROMPT%`, `%NEGATIVE%`, `%SEED%`, `%WIDTH%`, `%HEIGHT%`, `%OUT_WIDTH%`, `%OUT_HEIGHT%` and `%PREFIX%`. This is how to add LoRAs or upscalers.
3. Enter the ComfyUI address (for example `http://192.168.1.20:8188`), pick the model and choose what gets painted.

What gets painted, most important first: your adventurer, in the gear you actually wear, with your race's features, your job's look, your gift's glow, your rank's aura and any backdrop, pose or dye you own; this week's guardian; the market's current stock (once you open the Market, so deliveries nobody looks at don't keep ComfyUI busy); the goddess in six moods, in the backdrop you chose for her (by default a shrine that grows with your devotion); Marrow Fennick's faces; the twenty choice characters; then your gear and the bestiary. The game's interface (chests, emblems, badges) stays drawn by the game.

## Consistent characters with an image-edit model
Painted from scratch, the same character can look like a different person from one picture to the next. Pick an **Image-edit model** under **Art and AI** to fix that:
- **Flux Kontext** (for example `flux1-kontext-dev.safetensors` in `models/diffusion_models`). It uses the same text encoders and VAE as Flux, found automatically.
- **Qwen Image Edit** (for example `qwen_image_edit_2509_fp8_e4m3fn.safetensors`), which also needs `qwen_2.5_vl_7b` in `models/text_encoders` and `qwen_image_vae` in `models/vae`.

Your adventurer, the goddess and Marrow Fennick then each get one **base painting**: who they are, full body, standing on a plain grey backdrop in plain clothes. It's painted bigger and with more steps than anything else, whatever the painting speed, so the edits have plenty of detail to work from. Every other picture of them is an edit of it: the goddess's moods, outfit and backdrop, Marrow's faces, outfit, accessory and where he trades, your gear, job, pose and backdrop. A new piece of armour edits your portrait instead of repainting you. Your main model still paints everything else (items, guardians, choice characters). If your ComfyUI is missing an edit node, those pictures are painted from scratch instead and the log says why.

Without an edit model, every mood of a character is painted from the prompt, but with the same seed and the same words for who they are (race, age, build, hair, eyes), so they drift much less from picture to picture.

## The Gallery
The **Gallery** tab (while paintings are on) shows every painting, each with its own **Repaint**: ComfyUI paints a new version, the old one stays on screen until it's ready, and then the old file is deleted. With an edit model, each character's base painting comes first; repainting a base redoes every picture of that character from the new one. The tab also shows how many paintings there are, how much space they take and roughly how long the waiting ones will take.

Beside you, the goddess and Marrow are their choices, grouped by what changing them does:

| Group | What's in it | What happens when you change it |
|---|---|---|
| **Shown differently** | Framing | Nothing is repainted. Every painting of them is full body, and the panel crops it (full body, three-quarter, waist up, head and shoulders or close-up), on the Status, Goddess and Market tabs and in the Gallery. |
| **Edited from the base painting** | Outfit, accessory, what you hold, backdrop | The base painting stays, so the face stays. Each picture is edited again. (Without an edit model, each is painted again.) |
| **A new base painting** | Race, age, build, hair, eyes | This is who they are, so a new base painting is made, then every picture is edited from it. |

**You:** age (kid, teen, young adult, adult or elderly), hair or fur colour, hairstyle, eye colour and build (slender to heavyset); what you hold (your equipped weapon, nothing, or a sword, bow, staff, warhammer, spear or dagger); framing. Your race is your adventurer's. Hair, eyes and build change the pixel art too.

**The goddess:** race (human, elf, half-elf, dwarf, fox-eared beastkin, dragonkin or celestial), age, build (petite, slender, average, athletic, sturdy or full-figured), hair colour, hairstyle (eight styles), eye colour; outfit (fourteen, from her moonlit dress to a starlight gown, priestess robes, a huntress's tunic, a festival yukata, scholar's robes, a silver ballgown or a modern hoodie); backdrop (her shrine, which grows with your devotion; **Match each mood**, a different scene for each of her moods, from a calm lantern-lit shrine to storm clouds when she's worried; a night sky, a temple garden, a moonlit lake, a star library, a birch forest or plain grey); framing.

**Marrow Fennick:** race (gnome, halfling, dwarf, human, elf, goblin, raccoon-eared beastkin or dragonkin), age, build (wiry, slight, average, stout, broad-shouldered, heavyset or tall and lanky), hair and beard (eight styles); outfit (eleven, from his patched velvet waistcoat to a sailor's coat, desert robes, a noble's doublet or a tinker's harness), accessory (monocle, spectacles, tinker's goggles, eyepatch, pipe, feathered hat, merchant's scales or nothing), where he trades (his wagon, a market stall, a tavern table, a caravan tent, a cramped shop, a harbour stall or plain grey); framing.

Paintings are kept at 704 × 1024 (base paintings at 768 × 1152), so even a close-up crop stays sharp.

## Painting speed
| Setting | What it does |
|---|---|
| **Quality** | Everything at full size. |
| **Balanced** (default) | Item icons are painted smaller; they're shown small anyway. |
| **Fast** | Also about a third fewer steps, and spare common and uncommon gear stays pixel art. It loads a full-size Flux model at half the video memory, so it can stay loaded beside Ollama instead of reloading for every picture, which is the usual reason paintings crawl on a shared GPU. |

**My model is a fast variant:** tick this for Lightning, Turbo or Hyper SDXL models, or Flux Schnell (4 to 8 steps, a few seconds a picture).

**Sharing the GPU with Ollama:** both want video memory. If paintings wait while your Ollama model is loaded, shorten Ollama's keep-alive so it unloads sooner, or start ComfyUI with `--lowvram`.

**Keeping the folder small:** paintings are saved as WebP in `/config/life_rpg/art/`. A repaint or a new portrait replaces its file. The folder is capped at 1 GB and 1,500 pictures; past that, the least recently shown go first. The built-in workflows use ComfyUI's preview output, so ComfyUI's own `output` folder doesn't fill up. Base paintings sent for editing go to ComfyUI's `input/life_rpg` folder and are overwritten, not added to.

Jobs run one at a time. If ComfyUI is offline the queue waits; if a painting fails, the error shows in the log and that picture is tried again after six hours.