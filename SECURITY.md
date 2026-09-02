# Security Policy

Slipcase is a desktop application. It renders local image files, stores API
credentials on disk, and downloads cover art from third-party services. Those
last two are where its security surface is.

## Reporting a vulnerability

Use GitHub's private vulnerability reporting: open the
[Security tab](https://github.com/milnet01/Slipcase/security) and choose
**Report a vulnerability**. That opens a thread only the maintainer can see.

Please do not open a public issue for a security problem before it is fixed.

This is a personal project maintained by one person in their own time. There
is no service-level agreement and no bounty. What you can expect is an
acknowledgement, a plain answer about whether the report is in scope, and
credit in the release notes if you want it.

## What is in scope

The application maintains a small set of security invariants. A way to defeat
any of them is in scope:

- **Download allowlist** — image downloads are restricted to known service
  domains (`ALLOWED_IMAGE_DOMAINS` in `api/base.py`). A way to make the app
  fetch a URL outside that list, including through a redirect, is a finding.
- **Accepted image formats** — a download is decoded only if it is PNG, JPEG
  or WEBP. A way to reach another decoder is a finding.
- **Download and image size caps** — there is a byte cap on any single
  download and a pixel ceiling that rejects a decompression bomb before it is
  decoded.
- **Credential handling** — API errors are scrubbed of passwords and keys
  before they are displayed, and the config directory and file are created
  with owner-only permissions.
- **Transport** — every API request uses HTTPS with certificate verification
  on.
- **No code execution from data** — text a user supplies, such as a title or
  a serial, is drawn as image text and never evaluated.

## What is out of scope

- **ScreenScraper credentials appearing in a URL query string.** The upstream
  API mandates that form and offers no header or body alternative, so the
  credentials reach ScreenScraper's own access logs. The transport is HTTPS
  and the values are scrubbed before display. This is documented in
  `api/screenscraper.py` and is accepted, not overlooked.
- **Anything requiring an attacker to already have write access** to the
  machine running Slipcase, or to the configuration file.
- **Vulnerabilities in the third-party services themselves.** Report those to
  ScreenScraper, TheGamesDB or the libretro project.
- **Denial of service** achieved by feeding the app a deliberately large local
  file you supplied yourself.

## Supported versions

Only the most recent release is supported. Fixes land on `main` and go out in
the next release; there are no backports to older versions.
