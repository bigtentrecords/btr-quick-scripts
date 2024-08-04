import argparse
import csv
import datetime as dt
import logging
import os
from time import sleep

from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
import spotipy
from spotipy.client import Spotify as SpotifyClient
from spotipy.exceptions import SpotifyException
from spotipy.oauth2 import SpotifyClientCredentials


SPOTIFY_BASE_URL = "https://open.spotify.com"


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_discovered_on_playlist_uris(driver: WebDriver, artist_id: str) -> list[str]:
    """Gets uris for all Spotify playlists which an artist is featured on

    Args:
      artist_uri (str): Spotify artist uri

    Returns a list of Spotify playlist uris"""
    # navigate to discovered on page
    driver.get(f"{SPOTIFY_BASE_URL}/artist/{artist_id}/discovered-on")
    sleep(1)

    # harvest ids from links and return
    grid_container = driver.find_element(
        By.CSS_SELECTOR, "div[data-testid=grid-container]"
    )
    playlist_ids = [
        e.get_attribute("href").split("/")[-1]
        for e in grid_container.find_elements(By.CSS_SELECTOR, "a")
    ]
    return playlist_ids


def get_playlist_metadata(sp: SpotifyClient, playlist_id: str) -> dict:
    """Gets playlist metadata for a given Spotify playlist

    Args:
      playlist_id (str): Spotify playlist id

    Returns playlist metadata in a dict"""
    try:
        playlist = sp.playlist(playlist_id)
    except SpotifyException:
        logger.warning("failed to scrape playlist spotify:playlist:%s", playlist_id)
        playlist_metadata = {}
    else:
        last_updated = max(
            [
                dt.datetime.strptime(item["added_at"], "%Y-%m-%dT%H:%M:%S%z")
                for item in playlist["tracks"]["items"]
                if item["added_at"]
            ]
        )
        playlist_metadata = {
            "playlist_uri": playlist["uri"],
            "name": playlist["name"],
            "description": playlist["description"],
            "followers": playlist["followers"]["total"],
            "tracks": playlist["tracks"]["total"],
            "last_updated": last_updated.strftime("%Y-%m-%d %H:%M:%S"),
            "owner": playlist["owner"]["display_name"],
            "owner_uri": playlist["owner"]["uri"],
            "owner_followers": playlist["owner"].get("followers", {}).get("total", 0),
        }
    return playlist_metadata


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-a",
        "--artists",
        nargs="+",
        help="list of Spotify artist ids or path to text file of Spotify artist ids",
        required=True,
    )
    parser.add_argument(
        "-f", "--file", action="store_true", help="indicates if artists is a file path"
    )

    # unpack artists argument
    args = parser.parse_args()
    if args.file:
        with open(args.artists[0], mode="r", encoding="utf8") as f:
            artist_ids = f.read().strip().split("\n")
    else:
        artist_ids = args.artists

    # set up selenium driver and spotipy client
    driver = webdriver.Chrome()
    sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials())

    # grab playlists
    playlists = {}
    for a in artist_ids:
        aname = sp.artist(a)["name"]
        discovered_on_playlists = get_discovered_on_playlist_uris(driver, a)
        logger.info(
            "%s discovered on %i playlists", aname, len(discovered_on_playlists)
        )
        for p in discovered_on_playlists:
            if p in playlists:
                playlists[p]["featured_artists"].append(a)
                playlists[p]["featured_artist_count"] += 1
            else:
                playlist_metadata = get_playlist_metadata(sp, p)
                if playlist_metadata:
                    playlist_metadata["featured_artists"] = [aname]
                    playlist_metadata["featured_artist_count"] = 1
                    playlists.update({p: playlist_metadata})

    # reshape playlist dict into list of dicts
    playlists = [{"id": k} | v for k, v in playlists.items()]

    # write to csv
    nonce = dt.datetime.now().strftime("%Y%m%d%H%M%S")
    if args.file:
        head, tail = os.path.split(args.artists[0])
        fpath = os.path.join(head, f"{tail.split('.')[0]}_{nonce}.csv")
    else:
        fpath = f"./{'_'.join(args.artists)}_{nonce}.csv"
    with open(fpath, mode="w", encoding="utf16") as f:
        writer = csv.DictWriter(f, fieldnames=playlists[0].keys())
        writer.writeheader()
        writer.writerows(playlists)


if __name__ == "__main__":
    load_dotenv()
    main()
