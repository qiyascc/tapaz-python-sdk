from __future__ import annotations

import asyncio
import os

from tapaz_sdk import AdTab, AsyncTapAz


async def main() -> None:
    async with AsyncTapAz(os.environ["TAPAZ_COOKIE"]) as tap:
        for ad in await tap.ads.all(AdTab.PUBLISHED):
            print(ad.id, ad.title, ad.price, ad.url)
        for ad in await tap.ads.all(AdTab.REJECTED):
            print(ad.id, ad.reject_reason)


if __name__ == "__main__":
    asyncio.run(main())
