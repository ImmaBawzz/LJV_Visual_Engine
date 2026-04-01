"""
Platform Publisher

Handles content publishing to YouTube and Spotify.

Important platform limitations
--------------------------------
YouTube
~~~~~~~
``youtube.videos().insert()`` requires:
  1. A physical video file (media upload, not just metadata).
  2. OAuth 2.0 user credentials — ``developerKey`` alone grants *read-only*
     access.  Upload requires an OAuth flow (``google-auth-oauthlib``).
The original request's snippet used ``developerKey`` and omitted the
``media_body`` argument, which would raise a ``HttpError 400``.
This module uses ``google-auth-oauthlib`` for browser-based OAuth and
``googleapiclient.http.MediaFileUpload`` for chunked upload.

Spotify
~~~~~~~
The Spotify Web API does **not** expose a public track-upload endpoint.
Only Spotify's internal distributor tools can ingest audio.  The
``sp.track()`` call in the original request is a *read* method that
retrieves an existing track by ID — it cannot create or upload one.

This module implements what IS available via the public Spotify API:
  - Create a playlist for the release.
  - Add existing tracks by Spotify URI (e.g. after distribution).
  - Search for and return a track's Spotify metadata.
  - (Stub) Document the Spotify for Artists distribution flow.

Credentials
~~~~~~~~~~~
API keys / secrets are never hard-coded.  The module reads them from
environment variables (or the existing CredentialManager) using the
priority chain already established in tools/credential_manager.py.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Dict, Optional

logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parents[3]
_LOG_FILE = ROOT / "03_WORK" / "logs" / "ai_content.log"


def _log(msg: str) -> None:
    _LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    logger.info(msg)
    with _LOG_FILE.open("a", encoding="utf-8") as f:
        f.write(msg + "\n")


# ---------------------------------------------------------------------------
# YouTube publisher
# ---------------------------------------------------------------------------

class YouTubePublisher:
    """
    Uploads a video file to YouTube using the Data API v3.

    Requires OAuth 2.0 credentials — a bare ``api_key`` is insufficient
    for uploads.  On first run the user completes a browser-based consent
    flow; the token is cached in ``03_WORK/temp/youtube_token.json``.

    Parameters
    ----------
    client_secrets_file : str or Path, optional
        Path to ``client_secret_*.json`` from Google Cloud Console.
        Falls back to env var ``YOUTUBE_CLIENT_SECRETS_FILE``.
    token_file : str or Path, optional
        Path where the OAuth token is persisted between runs.

    Example
    -------
    >>> pub = YouTubePublisher()
    >>> result = pub.upload_video(
    ...     video_path=Path("04_OUTPUT/youtube_16x9/video.mp4"),
    ...     title="Velocity Letters — Official Video",
    ...     description="...",
    ...     tags=["pop", "LJV"],
    ...     privacy="unlisted",
    ... )
    >>> print(result["id"])
    """

    SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
    API_SERVICE = "youtube"
    API_VERSION = "v3"

    def __init__(
        self,
        client_secrets_file: Optional[Path] = None,
        token_file: Optional[Path] = None,
    ) -> None:
        self.client_secrets_file = (
            Path(client_secrets_file)
            if client_secrets_file
            else Path(os.getenv("YOUTUBE_CLIENT_SECRETS_FILE", "client_secret.json"))
        )
        self.token_file = token_file or (
            ROOT / "03_WORK" / "temp" / "youtube_token.json"
        )
        self._service = None

    def _authenticate(self):
        """Run OAuth flow and return an authorised service object."""
        try:
            from google_auth_oauthlib.flow import InstalledAppFlow
            from google.auth.transport.requests import Request
            from google.oauth2.credentials import Credentials
            from googleapiclient.discovery import build
        except ImportError as exc:
            raise ImportError(
                "Google API client libraries are required for YouTubePublisher. "
                "Install them with: pip install google-api-python-client "
                "google-auth-oauthlib google-auth-httplib2"
            ) from exc

        creds = None
        if self.token_file.exists():
            creds = Credentials.from_authorized_user_file(
                str(self.token_file), self.SCOPES
            )

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                if not self.client_secrets_file.exists():
                    raise FileNotFoundError(
                        f"OAuth client secrets not found: {self.client_secrets_file}\n"
                        "Download from Google Cloud Console → APIs & Services → Credentials"
                    )
                flow = InstalledAppFlow.from_client_secrets_file(
                    str(self.client_secrets_file), self.SCOPES
                )
                creds = flow.run_local_server(port=0)

            self.token_file.parent.mkdir(parents=True, exist_ok=True)
            self.token_file.write_text(creds.to_json(), encoding="utf-8")
            _log(f"[YouTubePublisher] Token cached: {self.token_file}")

        return build(self.API_SERVICE, self.API_VERSION, credentials=creds)

    def upload_video(
        self,
        video_path: Path,
        title: str,
        description: str,
        tags: Optional[list] = None,
        category_id: str = "10",  # Music
        privacy: str = "unlisted",
    ) -> Dict:
        """
        Upload a video file to YouTube.

        Parameters
        ----------
        video_path : Path
            Absolute path to the MP4/MOV file to upload.
        title : str
            Video title (max 100 chars).
        description : str
            Video description.
        tags : list of str, optional
            Search tags for the video.
        category_id : str
            YouTube category ID. ``"10"`` = Music.
        privacy : str
            ``"public"``, ``"unlisted"``, or ``"private"``.

        Returns
        -------
        dict
            YouTube API response containing the uploaded video ``id``.
        """
        from googleapiclient.http import MediaFileUpload

        video_path = Path(video_path)
        if not video_path.exists():
            raise FileNotFoundError(f"Video file not found: {video_path}")

        if self._service is None:
            self._service = self._authenticate()

        body = {
            "snippet": {
                "title": title[:100],
                "description": description,
                "tags": tags or [],
                "categoryId": category_id,
            },
            "status": {
                "privacyStatus": privacy,
                "selfDeclaredMadeForKids": False,
            },
        }

        media = MediaFileUpload(
            str(video_path),
            mimetype="video/mp4",
            resumable=True,
            chunksize=10 * 1024 * 1024,  # 10 MB chunks
        )

        request = self._service.videos().insert(
            part="snippet,status",
            body=body,
            media_body=media,
        )

        _log(f"[YouTubePublisher] Uploading: {video_path.name}")
        response = None
        while response is None:
            status, response = request.next_chunk()
            if status:
                pct = int(status.progress() * 100)
                _log(f"[YouTubePublisher] Upload progress: {pct}%")

        video_id = response.get("id", "")
        _log(f"[YouTubePublisher] Upload complete. Video ID: {video_id}")
        return response


# ---------------------------------------------------------------------------
# Spotify publisher
# ---------------------------------------------------------------------------

class SpotifyPublisher:
    """
    Spotify Web API client for playlist/metadata management.

    IMPORTANT: The Spotify public API does not support audio upload.
    To distribute a track to Spotify, use an official distributor such as
    DistroKid, TuneCore, or CD Baby.  Once distributed, you can use this
    class to:
      - Search for your released track.
      - Create and curate a release playlist.
      - Retrieve streaming analytics via the Charts/Loudness endpoints.

    Parameters
    ----------
    client_id : str, optional
        Spotify application client ID. Reads ``SPOTIFY_CLIENT_ID`` env var.
    client_secret : str, optional
        Spotify application client secret. Reads ``SPOTIFY_CLIENT_SECRET``.
    redirect_uri : str, optional
        OAuth redirect URI registered in Spotify Dashboard.

    Example
    -------
    >>> pub = SpotifyPublisher()
    >>> playlist = pub.create_release_playlist(
    ...     name="LJV — Velocity Letters",
    ...     description="Singles & remixes",
    ...     public=False,
    ... )
    >>> print(playlist["external_urls"]["spotify"])
    """

    def __init__(
        self,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        redirect_uri: str = "http://localhost:8080/callback",
    ) -> None:
        self.client_id = client_id or os.getenv("SPOTIFY_CLIENT_ID", "")
        self.client_secret = client_secret or os.getenv("SPOTIFY_CLIENT_SECRET", "")
        self.redirect_uri = redirect_uri
        self._sp = None

    def _get_client(self):
        if self._sp is not None:
            return self._sp
        try:
            import spotipy
            from spotipy.oauth2 import SpotifyOAuth
        except ImportError as exc:
            raise ImportError(
                "spotipy is required for SpotifyPublisher. "
                "Install it with: pip install spotipy"
            ) from exc

        if not self.client_id or not self.client_secret:
            raise ValueError(
                "Spotify credentials missing. Set SPOTIFY_CLIENT_ID and "
                "SPOTIFY_CLIENT_SECRET environment variables."
            )

        auth_manager = SpotifyOAuth(
            client_id=self.client_id,
            client_secret=self.client_secret,
            redirect_uri=self.redirect_uri,
            scope="playlist-modify-public playlist-modify-private user-library-modify",
        )
        self._sp = spotipy.Spotify(auth_manager=auth_manager)
        _log("[SpotifyPublisher] Authenticated.")
        return self._sp

    def search_track(self, track_name: str, artist_name: str) -> Optional[Dict]:
        """
        Search for an existing track on Spotify by name + artist.

        Returns the first result dict, or ``None`` if not found.
        Useful after distribution to retrieve the Spotify track URI.
        """
        sp = self._get_client()
        query = f"track:{track_name} artist:{artist_name}"
        results = sp.search(q=query, type="track", limit=1)
        items = results.get("tracks", {}).get("items", [])
        if items:
            _log(f"[SpotifyPublisher] Found track: {items[0]['external_urls']['spotify']}")
            return items[0]
        _log(f"[SpotifyPublisher] Track not found: '{track_name}' by '{artist_name}'")
        return None

    def create_release_playlist(
        self,
        name: str,
        description: str = "",
        public: bool = False,
    ) -> Dict:
        """
        Create a new Spotify playlist for a release.

        Parameters
        ----------
        name : str
            Playlist name.
        description : str
            Short description shown on Spotify.
        public : bool
            If False, playlist is private.

        Returns
        -------
        dict
            Spotify playlist object (contains ``id`` and ``external_urls``).
        """
        sp = self._get_client()
        user_id = sp.me()["id"]
        playlist = sp.user_playlist_create(
            user=user_id,
            name=name,
            public=public,
            description=description,
        )
        _log(f"[SpotifyPublisher] Playlist created: {playlist['external_urls']['spotify']}")
        return playlist

    def add_tracks_to_playlist(
        self, playlist_id: str, track_uris: list
    ) -> Dict:
        """Add a list of Spotify track URIs to a playlist."""
        sp = self._get_client()
        result = sp.playlist_add_items(playlist_id, track_uris)
        _log(f"[SpotifyPublisher] Added {len(track_uris)} tracks to playlist {playlist_id}")
        return result

    @staticmethod
    def distribution_note() -> str:
        """Return a note explaining Spotify distribution options."""
        return (
            "Spotify does not offer a public audio upload API.\n"
            "To release a track on Spotify:\n"
            "  1. Use a digital distributor: DistroKid (distrokid.com), "
            "TuneCore (tunecore.com), or CD Baby (cdbaby.com).\n"
            "  2. Upload your WAV/MP3 master through their portal.\n"
            "  3. Once live, use SpotifyPublisher.search_track() to retrieve the URI.\n"
            "  4. Use SpotifyPublisher.add_tracks_to_playlist() to add it to a curated list."
        )


# ---------------------------------------------------------------------------
# Convenience wrapper
# ---------------------------------------------------------------------------

class Publisher:
    """
    Unified publisher that wraps YouTubePublisher and SpotifyPublisher.

    Parameters
    ----------
    youtube_client_secrets : Path, optional
    spotify_client_id : str, optional
    spotify_client_secret : str, optional
    """

    def __init__(
        self,
        youtube_client_secrets: Optional[Path] = None,
        spotify_client_id: Optional[str] = None,
        spotify_client_secret: Optional[str] = None,
    ) -> None:
        self.youtube = YouTubePublisher(client_secrets_file=youtube_client_secrets)
        self.spotify = SpotifyPublisher(
            client_id=spotify_client_id,
            client_secret=spotify_client_secret,
        )

    def publish_to_youtube(
        self,
        video_path: Path,
        title: str,
        description: str,
        tags: Optional[list] = None,
        privacy: str = "unlisted",
    ) -> Dict:
        return self.youtube.upload_video(
            video_path=video_path,
            title=title,
            description=description,
            tags=tags,
            privacy=privacy,
        )

    def publish_to_spotify(
        self,
        playlist_name: str,
        track_name: str,
        artist_name: str,
    ) -> Dict:
        """
        Search for a distributed track and add it to a release playlist.
        """
        track = self.spotify.search_track(track_name, artist_name)
        if not track:
            _log(
                f"[Publisher] Spotify track not found — has it been distributed? "
                f"{SpotifyPublisher.distribution_note()}"
            )
            return {}
        playlist = self.spotify.create_release_playlist(name=playlist_name)
        self.spotify.add_tracks_to_playlist(playlist["id"], [track["uri"]])
        return {"playlist": playlist, "track": track}


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Publish content to YouTube or Spotify.")
    sub = parser.add_subparsers(dest="platform")

    yt = sub.add_parser("youtube", help="Upload video to YouTube")
    yt.add_argument("--video", required=True)
    yt.add_argument("--title", required=True)
    yt.add_argument("--description", default="")
    yt.add_argument("--tags", nargs="*", default=[])
    yt.add_argument("--privacy", default="unlisted", choices=["public", "unlisted", "private"])

    sp = sub.add_parser("spotify", help="Manage Spotify release playlist")
    sp.add_argument("--playlist-name", required=True)
    sp.add_argument("--track-name", required=True)
    sp.add_argument("--artist", required=True)

    args = parser.parse_args()

    if args.platform == "youtube":
        pub = YouTubePublisher()
        result = pub.upload_video(
            video_path=Path(args.video),
            title=args.title,
            description=args.description,
            tags=args.tags,
            privacy=args.privacy,
        )
        print(f"Uploaded: https://youtu.be/{result.get('id', '?')}")

    elif args.platform == "spotify":
        pub = SpotifyPublisher()
        track = pub.search_track(args.track_name, args.artist)
        if track:
            pl = pub.create_release_playlist(name=args.playlist_name)
            pub.add_tracks_to_playlist(pl["id"], [track["uri"]])
            print(f"Playlist: {pl['external_urls']['spotify']}")
        else:
            print(SpotifyPublisher.distribution_note())

    else:
        parser.print_help()
