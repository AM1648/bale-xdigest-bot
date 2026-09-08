import httpx
from io import BytesIO

class MediaError(Exception):
    """Downloaded media exceeds Bale upload limits."""

class MediaDownloader:
    PHOTO_LIMIT = 10 * 1024 * 1024   # Bale upload limits
    VIDEO_LIMIT = 50 * 1024 * 1024

    def __init__(self, http_client: httpx.AsyncClient):
        self.http = http_client

    async def download_photo(self, url: str) -> bytes:
        return await self._download(url, self.PHOTO_LIMIT)

    async def download_video(self, url: str) -> bytes:
        return await self._download(url, self.VIDEO_LIMIT)

    async def download_gif(self, url: str) -> bytes:
        # GIFs are sent as animations; same limit as video
        return await self._download(url, self.VIDEO_LIMIT)

    async def _download(self, url: str, cap: int) -> bytes:
        async with self.http.stream("GET", url) as response:
            response.raise_for_status()
            buffer = BytesIO()
            async for chunk in response.aiter_bytes(65536):
                buffer.write(chunk)
                if buffer.tell() > cap:
                    raise MediaError(f"larger than {cap // (1024 * 1024)} MB")
            return buffer.getvalue()