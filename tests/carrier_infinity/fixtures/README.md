# Test fixtures

Recorded Carrier cloud responses (serial numbers and personal details already replaced), used by the tests.

They come from the test suite of [carrier_api](https://github.com/dahlb/carrier_api) (commit `03bd75e`), the
library this integration uses to talk to Carrier, and are shared under its MIT licence: see
[LICENSE.carrier_api](LICENSE.carrier_api).

| File | What it is |
|---|---|
| `systems.json` | One Infinity system: profile, status and configuration (from `tests/graphql/systems.json`) |
| `energy.json` | That system's energy figures (from `tests/graphql/energy.json`) |
| `messages/*.json` | Websocket messages Carrier pushes when something changes (from `tests/messages/`) |
