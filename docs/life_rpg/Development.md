For anyone changing the code. [CONTRIBUTING.md](CONTRIBUTING.md) has the rules the code keeps and how to release.

## Testing
Everything runs with plain Python 3.13; nothing needs a real Home Assistant, ComfyUI or LLM.

| Command | What it checks |
|---|---|
| `python3 tests/life_rpg/test_game.py` | The game's rules, then a three-year simulation of a casual, a steady and a dedicated player (the Pacing table comes from it). |
| `python3 tests/life_rpg/sim_longrun.py` | A 30-year soak with casual, steady, grinder, shopper and chaotic players (breaks of up to two months, missing and junk sensor data, random and invalid actions, a restart every year). It checks for crashes, broken invariants, save size and update speed. `python3 tests/life_rpg/sim_longrun.py 3 1 2` is a quicker 3-year run. |
| `python3 tests/life_rpg/ha/test_integration.py` | The whole Home Assistant side (setup, options, sensors, buttons, actions, the panel's websocket API, Assist tools, the painter and the LLM writer) against stand-ins for Home Assistant, a fake ComfyUI that checks every workflow against ComfyUI's real node signatures, and a fake LLM. Needs `pip install voluptuous pillow`. |
| `python3 tests/life_rpg/ha/soak.py 3 sdxl` | Three years of the Home Assistant side in fast time, with the fake ComfyUI (`sdxl` or `flux_unet`) and LLM: painting and writing budgets, queues, the art folder. |

GitHub Actions runs these on every push (shorter soaks), plus `ruff` and Home Assistant's `hassfest`. See [CONTRIBUTING.md](CONTRIBUTING.md) for where to make changes and how to release.

## Files
| Path | What it holds |
|---|---|
| `custom_components/life_rpg/` | The integration. `__init__.py` sets it up and registers the panel; `config_flow.py` the setup and Configure pages; `coordinator.py` reads the sensors and runs one adventurer's game; `sensor.py`, `event.py`, `button.py` the entities; `services.py` the actions; `websocket.py` the panel's API; `llm_api.py` the Assist tools; `lore.py` the LLM's words; `art.py` the ComfyUI painter. |
| `custom_components/life_rpg/engine/` | The whole game in plain Python, with no Home Assistant imports. `game.py` holds the `Game` class (the day loop, scoring, progression, the labyrinth, choices and emergencies), with its other parts in `shop.py` (the market), `board.py` (the bounty board), `inputs.py` (sensors, corrections and hand logging) and `characters.py` (portrait choices, chats and gifts). `rules.py` has the tuning constants and formulas, `content.py` every name, table and line of text, `loot.py` chests and gear, `market.py` gold, stock and haggling, and `appearance.py` looks and painting prompts. |
| `custom_components/life_rpg/frontend/` | The System panel and cards (`life-rpg.js`), their styles (`styles.js`), the pixel-art engine (`art.js`) and the cast (`cast.js`). Plain ES modules, no build step. |
| `custom_components/life_rpg/translations/`, `services.yaml`, `brand/` | UI text, action descriptions and the integration's icon and logo. |
| `examples/life_rpg/` | A dashboard view and four phone-notification automations to copy from. |
| `tests/life_rpg/` | The engine tests and simulations; `tests/life_rpg/ha/` the Home Assistant side. |
| `pyproject.toml`, `.github/` (repository root) | Lint settings, and the GitHub checks and issue forms shared by every integration. |