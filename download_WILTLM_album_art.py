""""Script to download album art for tracks in WILTLM playlist"""

import argparse
import os
import sys

from dotenv import load_dotenv
import requests
import spotipy
from spotipy.client import Spotify as SpotifyClient
from spotipy.oauth2 import SpotifyOAuth


DL_FOLDER_PATH_ROOT = "/Users/nickdemasi/Mirror/Big_Tent/WILTLM"
WILTTM_PLAYLIST_ID: str = "4xjL4vPqFFTb9hEtxbbirJ"


def format_dl_folder_path(month: str) -> str:
    """Formats folder name and path where WILTLM album art will be written"""
    dl_folder_name = f"{month}_WILTLM"
    dl_folder_path = f"{DL_FOLDER_PATH_ROOT}/{dl_folder_name}"
    return dl_folder_path


def get_playlist_tracks(sc: SpotifyClient, playlist_id: str) -> list[dict]:
    """Pings Spotify Web API for a playlist object and collects track objects"""
    playlist_tracks = [
        itm["track"] for itm in sc.playlist(playlist_id)["tracks"]["items"]
    ]
    return playlist_tracks


def download_album_art(track: dict, destination: str) -> int:
    """Downloads album art from track objects to destination folder"""
    # unpack track object
    track_name = "_".join(track["name"].replace("/", "").split(" "))
    artist_name = "_".join(track["artists"][0]["name"].replace("/", "").split(" "))
    img_url = track["album"]["images"][0]["url"]

    # download image
    img_data = requests.get(img_url).content
    with open(f"{destination}/covers/{artist_name}-{track_name}.jpg", "wb") as handler:
        handler.write(img_data)

    return 0


def main(args):
    # unpack args
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-m", "--month", help="month of the playlist written in YYYY-MM form"
    )
    parser.add_argument("-p", "--playlist-id", help="Spotify id of the playlist")
    args = parser.parse_args()

    # assign args to variables
    month = args.month
    playlist_id = args.playlist_id or WILTTM_PLAYLIST_ID

    # connect to api
    scope = "user-library-read"
    sp = spotipy.Spotify(auth_manager=SpotifyOAuth(scope=scope))

    # prepare download folder
    dl_folder_path = format_dl_folder_path(month)
    # Create the directory if needed
    if not os.path.exists(dl_folder_path):
        os.makedirs(dl_folder_path)
    try:
        os.makedirs(f"{dl_folder_path}/covers")
    except FileExistsError:
        print("Covers folder already exists")

    # doublecheck destination folder with user
    print(f"Writing alubm art to {dl_folder_path}")
    user_input = input("Continue? Y/N: ")
    while user_input.lower() not in ("y", "n"):
        user_input = input("Invalid input, please answer Y/N: ")
    if user_input.lower() == "n":
        print("Ending program now.")
        return

    # download album art
    tracks = get_playlist_tracks(sp, playlist_id)
    for i, trk in enumerate(tracks):
        download_album_art(trk, dl_folder_path)
        print(f"Downloaded {i+1} of {len(tracks)} covers")


if __name__ == "__main__":
    load_dotenv()
    args = sys.argv[1:]
    main(args)
