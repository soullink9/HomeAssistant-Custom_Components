What leaves your Home Assistant, and what doesn't.

- Nothing calls out to the internet. The panel, cards and pixel art are served by your own Home Assistant; no fonts, scripts or images load from anywhere else.
- The only outbound connection is to the ComfyUI address you enter (only when it's set and Art style is Painted). Home Assistant sends prompts (and, with an edit model, the character's base painting) and receives the finished pictures, which are checked to be real images under 32 MB.
- Words come from the AI Task entity and conversation agent you pick. With Ollama that stays on your network; with a cloud LLM, your adventurer's progress and your chats go to that provider.
- Only you (or an admin) can act for your adventurer or chat as them. Other household members can watch your progress, but not your conversations.
- Paintings are served at `/life_rpg_art/<hash>.webp` without a login, like `/local`. The names are unguessable hashes.
- Saves stay in `.storage/life_rpg.<entry_id>`, paintings in `/config/life_rpg/art/`.