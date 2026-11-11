from __future__ import annotations

from typing import Any, Mapping, Optional

from ._core import GRAPHQL, AsyncEngine, Op, SyncEngine
from .resources import Ads, Auth, Catalog, Photos


class _Namespaces:
    def _mount(self) -> None:
        self.auth = Auth(self)
        self.catalog = Catalog(self)
        self.ads = Ads(self)
        self.photos = Photos(self)

    @staticmethod
    def _raw(query: str, variables: Optional[Mapping[str, Any]], operation: Optional[str], safe: bool,
             auth: bool) -> Op:
        return Op(GRAPHQL, query=query, variables=dict(variables) if variables is not None else None,
                  operation=operation or "", safe=safe, auth=auth)


class TapAz(SyncEngine, _Namespaces):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._mount()

    def me(self) -> Any:
        return self.auth.me()

    def graphql(self, query: str, variables: Optional[Mapping[str, Any]] = None, *, operation: Optional[str] = None,
                safe: bool = False, auth: bool = True) -> Any:
        return self._run(self._raw(query, variables, operation, safe, auth))


class AsyncTapAz(AsyncEngine, _Namespaces):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._mount()

    async def me(self) -> Any:
        return await self.auth.me()

    async def graphql(self, query: str, variables: Optional[Mapping[str, Any]] = None, *,
                      operation: Optional[str] = None, safe: bool = False, auth: bool = True) -> Any:
        return await self._run(self._raw(query, variables, operation, safe, auth))
