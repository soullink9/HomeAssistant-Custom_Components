Optional: words from your own LLM (through Home Assistant's AI Task), conversations with the goddess, and playing by voice through Assist.

## The goddess
**Configure → Goddess** names her (your voice assistant's name, say) everywhere: panel, titles, blessings, notifications, paintings, conversations and Assist.
- **Personality:** *a playful moon goddess* (built in), or *keep the model's own personality*, where the LLM is told only her name and her role in the game.
- **Talk through this conversation agent:** pick your own assistant (for example your Ollama agent). Her chat replies then come from that agent, in its own voice, with the game's facts sent along with each message. The conversation carries on through the day. Without an agent, the AI Task entity writes her replies. Either way she's told to answer what you actually said, ask things back and not recite your stats.
- **Her gifts:** now and then, while you're talking, she gives you something: a potion or charm, a blessed chest, a purse of gold or, rarely, a cosmetic. The game decides, never the LLM. There's at most one chance a day, and never two gifts within three weeks.

## Your LLM: the goddess, the merchant and the world
Any integration that offers an **AI Task** entity works; with Ollama, add an AI Task under the Ollama integration. Pick it under **Art and AI** (or leave it empty for Home Assistant's default) and choose the features:
- **Talk to the goddess:** a chat in the Goddess tab. Her portrait changes with her mood.
- **Written flavour:** her good-morning message, today's side quests, what the choice's character says, emergency narration, a bestiary entry for each guardian, lore for rare-or-better items, and a weekly chronicle in the Log tab.
- **Haggling:** talk to Marrow Fennick in your own words.

The LLM only writes words. The game decides every number. Without an LLM everything still works: the goddess speaks from 137 built-in lines, and haggling uses an offer box.

## Assist (voice and chat)
The integration adds a **Life RPG** toolset for conversation agents. Turn it on in your agent's options (Ollama → Configure → *Control Home Assistant*: tick **Life RPG** next to **Assist**). Then ask things like:
- "How close am I to clearing today?" or "How's the guardian doing?"
- "Take today's choice." / "Open my chests." / "Sell my junk."
- "What's the merchant selling?" / "Offer him 500 for the staff." / "Walk away from the staff." / "Buy the lucky charm."
- "What's on the bounty board?" / "I fed the dog."
- "Tell Lena I hit my steps before lunch."

Tools act for the adventurer linked to whoever is talking. A voice satellite with no signed-in user acts for the only adventurer, or the one you name.