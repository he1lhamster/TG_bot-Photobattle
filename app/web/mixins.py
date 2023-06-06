from aiohttp.abc import StreamResponse
from aiohttp.web_exceptions import HTTPUnauthorized


class AuthRequiredMixin:
    """
    check for auth in request, if not - return error,
    else return parent view class via super()
    """

    async def _iter(self) -> StreamResponse:
        if not getattr(self.request, "admin", None):
            raise HTTPUnauthorized
        return await super(
            AuthRequiredMixin, self
        )._iter()  # return to parent view class
