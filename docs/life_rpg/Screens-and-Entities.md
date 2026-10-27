What's on each tab of the System panel, the dashboard card, the example automations, and every entity and event the integration creates.

## Screens
**The System panel** has ten tabs (the tab bar wraps onto two rows on a phone):
- **Status:** your adventurer in their gear, level, rank, HP and MP, job, race, attributes, skills, active bonuses and where they come from, today's episode title and the goddess's line.
- **Quests:** the daily choice, the daily quests, emergency and penalty windows with timers, and the bounty board.
- **Labyrinth:** this week's guardian, floor trait, depth, creature tally and bestiary.
- **Inventory:** paper doll with six slots, chests, items, enhance, sell and salvage.
- **Market:** Marrow Fennick, the current stock, haggling, your bag of consumables and your wardrobe.
- **Class:** all eight jobs with their levels, passives and skills, plus skill proficiency.
- **Records:** badges, and the titles and hidden quests you've earned.
- **Goddess:** her portrait, devotion and blessings, a chat with her, and your racial gift tree.
- **Log:** 30-day chart, the weekly chronicle and the System log.
- **Gallery** (while paintings are on): every painting with its Repaint, and the choices for you, the goddess and Marrow.

If several adventurers exist, switch between them at the top; you can only act for your own (admins can act for anyone).

**Cards:** `type: custom:life-rpg-card` with `view: compact | status | quests | labyrinth` and an optional `adventurer: Name`. Tapping a card opens the panel. [`examples/life_rpg/dashboard.yaml`](../../examples/life_rpg/dashboard.yaml) has a ready view.

**Phone notifications:** the [`examples/life_rpg/automations/`](../../examples/life_rpg/automations) folder has one automation per file: System notifications, an 8 pm "secure your streak" nudge, a Sunday "guardian within reach" push, and chore approvals for kids mode. To add one: **Settings → Automations & scenes → Create automation → Create new automation → ⋮ → Edit in YAML**, replace everything with the file's contents, change `notify.mobile_app_your_phone` and the `user_` prefix, and save.

## Entities (adventurer "User")
`sensor.user_level`, `_level_progress`, `_xp`, `_xp_today`, `_streak`, `_rank`, `_job`, `_title`, `_race`, `_labyrinth` (guardian HP left, %), `_daily_choice`, `_gold` (with your bag and the merchant's mood as attributes), `_chests`, `_emergency_quest`, `_devotion`, one attribute sensor per quest (`_stamina` … with its skill as attributes) and one quest sensor per quest (`_stamina_quest` …). `sensor.user_devotion` carries the goddess's `morning_message` once it's written each day, handy for a daily briefing.

`event.user_achievements` fires every event:
- `level_up`, `rank_up`, `attribute_up`, `skill_up`
- `quest_complete`, `day_cleared`, `perfect_day`, `streak_milestone`, `personal_record`, `reading_held`
- `job_change`, `job_level`, `race_evolved`
- `title_earned`, `badge_earned`, `hidden_quest`
- `emergency_quest`, `emergency_cleared`, `emergency_failed`, `emergency_declined` (with `fine`, `excused` and, for failures, `why`: work, late or off)
- `penalty_quest`, `penalty_cleared`, `streak_broken`, `shield_earned`, `shield_used`
- `guardian_appeared`, `guardian_defeated`
- `choice_offered`, `choice_won`, `choice_lost`
- `bounty_claimed`, `bounty_done`
- `chest_dropped`, `devotion_up`, `bargain_struck`, `market_restocked`, `goddess_gift`

Events that pay gold carry a `gold` attribute.