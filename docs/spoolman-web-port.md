# Spoolman integration — current functionality (NiimPrintX desktop app)

**What it is:** an integration with [Spoolman](https://github.com/Donkie/Spoolman) (a
self-hosted filament spool inventory tracker) that lets a user pull spool data from
their Spoolman server and print a NiimBot label for it, either auto-generated or from
a custom user-designed template.

## Connection

- User enters a Spoolman server base URL (e.g. `http://spoolman.local:7912`); the app
  normalizes it, appends `/api/v1`, and does a lightweight GET to validate the
  connection.
- Last-used URL is persisted to a local JSON settings file (also settable via
  `SPOOLMAN_URL` env var or `--base-url` CLI flag) so reconnecting is automatic.
- Only two read endpoints are used: `GET /api/v1/spool` (list, with optional filters)
  and `GET /api/v1/spool/{id}` (single spool for the CLI print path). It's read-only
  against Spoolman — nothing is ever written back.

## Browsing spools

- Fetches spools with optional filters: filament name, material, vendor name,
  location, and an "include archived" toggle.
- Displays them in a sortable table: ID, vendor, filament name, material, color hex,
  remaining weight, location.
- A free-text search box re-queries by filament name.
- Fetching happens on a background thread so the UI doesn't block.

## Label generation — two paths

1. **Automatic layout** (no template saved): renders vendor name, filament name
   (word-wrapped, up to 3 lines), and a "MATERIAL · #id" caption, with font sizes
   auto-shrunk to fit. Layout adapts to aspect ratio — a QR code sits beside the text
   on wide labels, above it on square/tall ones.
2. **Custom template**: the user designs a template using the app's own text/icon
   canvas editor (same editor used for regular labels), with `{vendor}`, `{name}`,
   `{material}`, `{id}`, `{caption}` tokens in any text field and a QR-code placeholder
   image. Templates are saved per (device, label-size) pair. At print time, tokens are
   substituted with the live spool's data and the QR is regenerated at that
   placeholder's size/position.

- The QR code encodes a deep link back to the spool (`{base_url}/spool/show/{id}`) if
  connected, else a `spoolman:spool:{id}` fallback URI.
- Output is a flat raster image (Pillow) sized exactly to the target label in the
  printer's print DPI — this is what actually gets sent to the printer.

## Print flow

- "Generate label" renders the image and opens a print-preview dialog (density,
  copies, offset controls) shared with the rest of the app's printing.
- A CLI equivalent exists too: `niimprintx spoolman list|config|print|sizes`, useful as
  a reference for the same request shapes without the GUI.

## What a web port would need to replicate

- Spoolman client: base URL config + the two GET endpoints (filter params:
  `filament.name`, `filament.material`, `filament.vendor.name`, `location`,
  `allow_archived`).
- Server-side (or client-side canvas) image rendering matching the two layout
  algorithms above, at the target label's pixel dimensions/DPI.
- A template data model: token-bearing text fields + a "this image is the QR
  placeholder" flag, keyed by device+label-size.
- Nothing about auth — Spoolman itself doesn't require any in this integration.
