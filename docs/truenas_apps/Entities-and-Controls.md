# Entities and Controls

Home Assistant asks TrueNAS for fresh data **once a minute**. Each poll opens a short connection and closes it again.

## Per app

Each app (not each container) is a Home Assistant device named after the app.

| Entity | Example id | What it does |
|---|---|---|
| Switch | `switch.plex` | On while the app is running or starting up. Turn off to stop it; turn on to start it. |
| Status sensor | `sensor.plex_status` | `running`, `stopped`, `crashed`, `deploying` or `stopping`. |
| Restart button | `button.plex_restart` | Stops the app and starts it again. If the app is already stopped it only starts it. |
| Force recreate button | `button.plex_force_recreate` | Asks TrueNAS to redeploy the app, which rebuilds its containers from scratch. |
| Update | `update.plex` | On when TrueNAS says an update is available. Shows in Settings → Updates with the app's own icon. |

(Exact ids depend on your app names.)

### Controls run in the background

Pressing a button or flipping a switch starts a TrueNAS job and returns straight away. The update entity shows
"in progress" until TrueNAS finishes. Things to know:

- Only **one action per app at a time**. A second press while one is running shows an error ("another action is still running").
- If a job fails, Home Assistant creates a **persistent notification** with TrueNAS's error. It clears itself after the next success.
- A job that never finishes is abandoned after 30 minutes and the app is released again.

### App updates

The **Install** button on an app's update entity upgrades the app to the latest version TrueNAS offers, with default
settings, the same as the Upgrade button in TrueNAS. The new image is pulled and the app is recreated by TrueNAS.
The "backup" checkbox in Home Assistant's update dialog does nothing here.

## The TrueNAS device

| Entity | Example id | What it does |
|---|---|---|
| Pool usage | `sensor.truenas_tank_usage` | Percent of the pool that's allocated, one per pool. |
| System update | `update.truenas` | Shows the installed version and the newer one when TrueNAS finds an update, with a link to the release notes. |

### The system update entity never installs

This is deliberate. Updating the operating system should be done in the TrueNAS UI after saving your configuration
and taking a backup. If you press **Install** on this entity, Home Assistant shows a message saying so and nothing happens.

`update.truenas` also carries these **attributes**, which the [System Information Card](System-Information-Card.md) uses:
`hostname`, `platform` (`TrueNAS hardware` or `Generic`), `edition` (`Community` or `Enterprise`) and `version_name`
(the release codename).

## When things go wrong

- If TrueNAS can't be reached, all entities become **unavailable** and the integration retries every minute.
- If an app disappears from TrueNAS, its entities become unavailable (see [Installation](Installation.md) to delete them).
- If the API key isn't allowed to read update or system information, only the matching entity is unavailable.

See [Troubleshooting](Troubleshooting.md).