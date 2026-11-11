# Changelog

## 0.1.0

- Sync `TapAz` and async `AsyncTapAz`
- Phone login with an SMS code through the tap.az login service, then `loginUser` for the session cookie
- Session cookie import and export, with Cloudflare cookies always dropped
- Catalog: category tree, a category with its properties, dependent property options, regions, contact types
- Ads: create, validate, update, delete with a delete reason, prolong, get, cursor pages and a helper that reads every page
- Category properties checked before posting, with every problem listed
- Photo upload from bytes, a path or a file, and rotation
- Ad mutations and the login are never resent after an ambiguous failure; `OutcomeUnknownError`
- Reads retry with backoff, connection failures retry because nothing was sent
- Answers from the login service without a known error are asked again, with a note when more than one SMS may arrive
- Cloudflare challenge pages raise `BlockedError`
- goodconf settings, addresses, paths and messages are configurable
