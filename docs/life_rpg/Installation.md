Life RPG is a custom integration for Home Assistant. This page covers installing it, adding an adventurer and the options.

**Needs:** Home Assistant 2026.9 or newer. Optional: [ComfyUI](https://github.com/comfyanonymous/ComfyUI) for paintings, and an LLM integration with an AI Task entity (Ollama, for example) for the goddess's and the merchant's words.

## Download

Copy the [`custom_components/life_rpg`](../../custom_components/life_rpg) folder from this repository into `/config/custom_components/` (so you end up with `/config/custom_components/life_rpg/manifest.json`), then restart Home Assistant.

## Set up

1. On each Android phone, enable the Health Connect sensors in **Companion app → Settings → Manage sensors → Health Connect**: daily steps, sleep duration, daily floors and daily hydration.
2. Use the button under these steps, or go to **Settings → Devices & services → Add integration → Life RPG**. Each entry is one adventurer. Pick:
   - **Name:** becomes the entity prefix (`User` gives `sensor.user_level`).
   - **Home Assistant user:** who plays as this adventurer in the System panel.
   - **Race:** chosen for life.
   - **Body:** how your adventurer is drawn (androgynous, feminine or masculine).
   - **Goddess name** (optional): she's called Lune unless you name her.
   - **Sensors and goals.** Leave a sensor empty to skip that quest, or tick it under **Log in Home Assistant**.
3. Open **System** in the sidebar.

[![Open your Home Assistant instance and start setting up Life RPG.](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=life_rpg)

## Options

Everything else is under the integration's **Configure** menu, and progress is always kept when you change it:

| Page | What's there |
|---|---|
| **Quests and goals** | Sensors, goals, the linked user, clock (12 or 24 hours), water unit (mL or US fl oz), quests you log by hand, and which counts you may correct. |
| **Bounties** | How many daily side quests (0 to 10, 5 by default), and kids mode. |
| **Goddess** | Her name, her personality, and an optional conversation agent to talk through. |
| **Working hours and emergencies** | When you're at work (emergencies there never cost anything), or a schedule, calendar, binary sensor or input boolean that says so. |
| **Art and AI** | Pixel art or paintings, ComfyUI, an optional image-edit model, painting speed, and the AI Task entity for words. |

## Updating

**After an update** (copy the new `life_rpg` folder over the old one), restart Home Assistant. Browsers and the Home Assistant app pick up the new panel by themselves; if a screen was left open, it says so and offers a **Reload** button.

Next: [Phones and Sensors](Phones-and-Sensors.md) if a quest stays empty, then [How the Game Works](How-the-Game-Works.md).