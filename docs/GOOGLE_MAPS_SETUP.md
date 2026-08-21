# Google Maps setup

Maps are optional. Without a key the dashboard shows a list of locations and client report
PDFs print a location table instead of a map — nothing breaks. This is how to turn the real
maps on.

You need **two keys**, because one is exposed to browsers and one is not. Using a single key
for both would mean either a browser key that anyone can lift from your page and use to run
up your bill, or a server key that cannot work in a browser at all.

| Key | Lives in | Used for | Restrict by |
|---|---|---|---|
| `NEXT_PUBLIC_GOOGLE_MAPS_API_KEY` | `frontend/.env.local` | The interactive map and the location search box | **HTTP referrer** |
| `GOOGLE_MAPS_API_KEY` | `backend/.env` | The static map image inside client report PDFs | **IP address** |

## 1. Create a project and enable billing

1. Go to <https://console.cloud.google.com/>
2. Create a project — call it `olrac-signage`
3. **Billing → Link a billing account.** Maps will not work without it, even inside the free
   allowance. Google gives a recurring monthly credit that covers small fleets; you are only
   charged past it.

## 2. Enable the three APIs

**APIs & Services → Library**, enable each:

- **Maps JavaScript API** — the interactive map on the screen and ad pages
- **Places API** — the location search box in Screen Settings
- **Maps Static API** — the map image in client report PDFs

Missing one shows up as a map that loads grey, or a search that returns nothing.

## 3. Create the browser key

**APIs & Services → Credentials → Create credentials → API key**

1. Name it `olrac-browser`
2. **Application restrictions → Websites**, and add every origin the dashboard is served
   from. Include the LAN address if you open the console from a phone:
   ```
   http://localhost:3000/*
   http://192.168.0.170:3000/*
   https://your-domain.com/*
   ```
3. **API restrictions → Restrict key** → Maps JavaScript API, Places API
4. Paste it into `frontend/.env.local`:
   ```
   NEXT_PUBLIC_GOOGLE_MAPS_API_KEY=AIza...
   ```

> A `NEXT_PUBLIC_` value is compiled into the JavaScript that ships to the browser, so it is
> readable by anyone who opens devtools. That is normal and expected for a Maps browser key
> — the referrer restriction is what protects it, not secrecy. Do not skip step 2.

## 4. Create the server key

Create a second key, `olrac-server`:

1. **Application restrictions → IP addresses**, add the server's public IP
2. **API restrictions → Restrict key** → Maps Static API
3. Paste it into `backend/.env`:
   ```
   GOOGLE_MAPS_API_KEY=AIza...
   ```

## 5. Check the keys

Before restarting anything, ask Google whether the keys are any good:

```bash
python scripts/check-maps-keys.py
```

It gives the **server key** a real verdict — Google's rejection text distinguishes a wrong
key, a disabled API and unlinked billing, so you get the actual reason rather than a guess.

It can only confirm the **browser key** is present and well-formed, and no tool can do
better: that key is referrer-restricted, so a request from a script is *meant* to fail, and
the JavaScript API reports a bad key only at runtime inside the page. The dashboard covers
that case — if Google rejects it, the map is replaced by a message naming the reason.

## 6. Restart

```bash
powershell -ExecutionPolicy Bypass -File scripts/start-dev.ps1
```

The browser key is compiled into the bundle, so it only takes effect after a rebuild. The
script now rebuilds automatically whenever `.env.local` is newer than the last build — you
do not need to stop anything first, and a failed build stops the script rather than quietly
serving the previous bundle.

Then:

1. Open a screen → **Settings** → type a place in **Location**. Google suggestions should
   appear and picking one shows "Pinned at ...".
2. Save, and the map appears on the screen page with a green pin if it is online.
3. Open an advert → **Groups & screens** — every screen running it, pinned, with its play
   count in the popup.
4. Download a booking **Report** — page one carries the map image.

## Keeping the bill small

- **Set a budget alert** under Billing → Budgets & alerts. Do this before you forget.
- **Set daily quota caps** per API under APIs & Services → Quotas, so a bug or a scraped key
  cannot run all month.
- The dashboard loads the SDK **once per page**, and the search box waits 400 ms after you
  stop typing and uses a session token, which is how Google bills autocomplete as one
  charge per search rather than one per keystroke.
- Report PDFs fetch **one** static image each.

## If the map does not appear

| What you see | Cause |
|---|---|
| Location list with "no Google Maps key configured" | The key is missing, or you did not rebuild after adding it |
| "The map could not load" | Referrer restriction does not match the URL you are on, Maps JavaScript API not enabled, or billing not linked |
| Map loads but is grey with a watermark | Billing is not linked to the project |
| Search returns nothing | Places API not enabled, or not allowed on that key |
| Dashboard map works, PDF has a table | The **server** key is missing, or Maps Static API is not enabled on it |

The browser console names the exact reason — Google's errors are specific, and worth reading
before changing anything.
