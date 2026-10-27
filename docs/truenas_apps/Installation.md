# Installation

**Needs:** Home Assistant 2026.9 or newer, and TrueNAS 25.10 (Goldeye) or newer. It was built and tested on 25.10.7.

## 1. Download

Copy the [`custom_components/truenas_apps`](../../custom_components/truenas_apps) folder from this repository into `/config/custom_components/` (so you end up with
`/config/custom_components/truenas_apps/manifest.json`), then restart Home Assistant.

## 2. Make an API key in TrueNAS

In the TrueNAS web UI open the user menu in the top right, choose **API Keys**, and **Add** one. Copy the key when
TrueNAS shows it; it can't be shown again.

What the key needs to be allowed to do:

| To get | The key must be able to |
|---|---|
| Apps, status, pools | read apps and pools (required: setup fails without it) |
| Start, stop, restart, recreate, upgrade | change apps |
| TrueNAS system update entity | read the update status (optional) |
| System information attributes | read system information (optional) |

The simplest choice is a key for an administrator account. A key with fewer rights should still work: the optional
entities then show as unavailable, and a control the key isn't allowed to use fails with an error in the log. The
exact minimum set of roles hasn't been tested, so if you build a restricted key, please open an issue with what
worked.

## 3. Add the integration

**Settings → Devices & services → Add integration → TrueNAS Apps**, then enter:

- **Host**: the hostname or IP of TrueNAS, with `:port` if you changed the port. No `https://` and no path.
- **API key**: the key from step 2.
- **Verify SSL certificate**: leave **off** if TrueNAS uses its default self-signed certificate. Turn it on if the
  certificate is trusted by Home Assistant (for example one from Let's Encrypt, reached by the name on the certificate).

Home Assistant tests the connection before saving, and creates one device per app plus a **TrueNAS** device.

## Changing settings later

On the integration page (**Settings → Devices & services → TrueNAS Apps**), open ⋮ → **Reconfigure** to change the
host, the API key or the SSL setting without losing your entities.

If TrueNAS rejects the stored key (you deleted or regenerated it), Home Assistant shows a **Repair** / "Reconfiguration
required" notice. Open it and enter the new key. Polling stops until you do, so TrueNAS isn't hammered with bad logins.

## Apps you remove from TrueNAS

When you delete an app in TrueNAS, its entities become unavailable. To clear them, open the app's device page and use
**Delete**. Home Assistant only allows this once the app is really gone from TrueNAS.

## Updating the integration

Replace the `truenas_apps` folder with the new version from this repository and restart.

## Removing

Delete the integration entry in **Settings → Devices & services**, then (optional) remove the folder and delete the API
key in TrueNAS.