Where each quest's numbers come from, what to do when your phone doesn't share one, and how the game protects itself from sensors that count wrong.

## Phones and missing data
| Quest | Android (Health Connect) | iPhone (Home Assistant app) |
|---|---|---|
| Walk | Daily steps | Steps (pedometer, resets at midnight) |
| Climb | Daily floors* | Floors ascended |
| Rest, Lights out | Sleep duration | Log in Home Assistant |
| Drink water | Daily hydration* | Log in Home Assistant |

\* Samsung Health doesn't share water intake or floors with Health Connect, so those sensors stay empty however the phone is set up. Use **Log in Home Assistant** for those quests, or log water in an app that writes to Health Connect.

**Log in Home Assistant** makes a quest loggable by hand, on its own or on top of a sensor:
- **Panel:** +1 glass / +500 mL (16 fl oz) / Undo on Drink water, +1 flight / +3 / Undo on Climb, and a sleep form (fell asleep, woke up) under the quests.
- **Dashboard card:** + Water and + Stairs on the compact card.
- **Buttons:** `button.<name>_log_a_glass_of_water` and `button.<name>_log_a_flight_of_stairs`, handy for an NFC tag on your water bottle or at the top of the stairs.
- **Actions:** `life_rpg.log` (water or floors; a negative amount undoes), `life_rpg.correct` (today's real count or a record) and `life_rpg.log_sleep` (bedtime and wake, like `22:40` and `06:50`; with only a bedtime it logs just Lights out).
- **Assist:** "I drank a glass of water", "I climbed three flights", "I slept from 11 to 6:30".
- **iPhone and Apple Health:** a Shortcuts personal automation (say, "When my alarm is stopped") with *Find Health Samples*, then the Home Assistant app's *Perform Action* calling `life_rpg.log_sleep` or `life_rpg.log`.

Sleep logged by hand and sleep your phone also reported count once, not twice. Lights out is read from the sleep sensor's session times, its sleep-stage timeline, or the companion app's separate *sleep start* sensor, whichever is there.

## When a sensor gets it wrong
If two apps write the same steps into Health Connect, the total doubles. The game guards against it:
- **Impossible jumps are held back.** Steps can't rise faster than about 260 a minute, floors 4 and water 150 mL, plus an allowance for a phone syncing after time offline. You get a "Reading held back" notice, and the quest shows what was held with a **They were real** button.
- **Each day has a ceiling:** 100,000 steps, 500 floors, 10 litres; and no more than 16 hours of sleep.
- **Fixes upstream are followed.** If the count drops (you removed the duplicate source), the game follows once the lower number has held for 15 minutes.
- **Corrections are off unless you allow them**, per quest, under **Quests and goals → Allow corrections**, so nobody can just type in a number. Turn one on, fix the count (or an inflated record) with **Wrong count?**, then turn it off again.

A steady double count from the start of the day can look human, so set the real count once and fix the source in Health Connect (set the app priority for steps so only one app counts).