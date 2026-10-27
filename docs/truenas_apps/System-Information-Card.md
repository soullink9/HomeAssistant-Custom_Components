# System Information Card

An example dashboard card that looks like the **System Information** panel in TrueNAS, plus a few counts from this
integration. It's a plain built-in **Markdown** card: no HACS, no custom cards, no JavaScript.

It reads the attributes of the `update.truenas` entity and needs nothing else.

## Add it

1. Edit a dashboard, **Add card → Manual**.
2. Paste the contents of [`examples/truenas_apps/system_information_card.yaml`](../../examples/truenas_apps/system_information_card.yaml).

It shows platform, edition, version (with the release codename if TrueNAS reports one), hostname, whether a system
update is waiting, how many apps are running out of the total, and how many app updates are pending.

## If `update.truenas` has a different id

The card assumes the system update entity is `update.truenas`. If yours is named differently, change the
`{% set u = 'update.truenas' %}` line at the top of the card.

## Notes

- Uptime isn't shown because the integration doesn't expose it.
- If the API key can't read system information, platform, edition, version name and hostname show `—`.