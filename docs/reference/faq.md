# FAQ and troubleshooting

## Is this an official tap.az API?

No. tap.az has no public API for posting. The SDK uses the same GraphQL API, photo service and login service as the website, as one signed in account, and says who it is in the User-Agent. tap.az can change these at any time; addresses and paths are settings, so many changes can be followed with configuration.

## Can I sign in with a password?

No. tap.az signs in by phone and SMS code only, and so does the SDK. Save the cookie after the first sign in to avoid new codes.

## Two SMS codes arrived

The login service did not answer the first request usefully, so the SDK sent it again. `CodeSent.retried` was `True` and `CodeSent.note` says so. Use the latest code.

## `InvalidCodeError` with a code that is right

If the check had to be repeated, the first attempt may already have used the code. Ask for a new one.

## `SessionRequiredError`

The call needs a session and the client has no cookie at all. Pass one to `TapAz(...)`, set `TAPAZ_COOKIE`, or sign in.

## `AuthenticationError`

The client has a cookie but tap.az no longer accepts it. Sign in again and save the new cookie.

## `InvalidRequestError: Category … has subcategories, use a leaf category`

Ads can only be posted in a category without children. Use `category.walk()` and `category.leaf` to find the right one; see [Find a category](../examples/find-category.md).

## `InvalidRequestError: The ad is not valid for this category`

Read `exc.errors`: each entry names the property (`properties.<id>`) and the problem. The usual causes are a missing required property, an option id from another property, or a dependent property whose parent choice does not enable it.

## `'…' only applies when property … has an option that enables it`

You gave a value for a dependent property, but the option chosen in its parent does not switch it on. Either choose the parent option that enables it or leave the property out.

## `BannedError` or `UnconfirmedError`

tap.az refuses changes from a banned account, or from one whose phone or email is not confirmed. Sort it out on the tap.az website.

## `BlockedError`

Cloudflare answered with a challenge page. The SDK never tries to pass it. Run from another network, and send fewer requests at once.

## `OutcomeUnknownError` on `create`

The ad may exist. Look at `tap.ads.list("PENDING")` before posting again. See [Safety and retries](../guides/safety.md#when-the-outcome-is-unknown).

## My edit did not change the area

`update` sends the text, price, photos, contact type and boolean properties. tap.az only sets the other properties when the ad is created. Delete and post again to change them.

## Can I post to a region other than Baku?

Yes. Pass `region_id` from `tap.catalog.regions()`, or set `TAPAZ_DEFAULT_REGION`.

## How do I hide my phone number?

`contact_type=ContactType.ONLY_MESSAGES`.
