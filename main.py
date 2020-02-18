import itertools
import bisect
from collections import Counter
from pathlib import Path
import os
from mutagen.easyid3 import EasyID3
import re
import shutil
from datetime import date
import yaml
from memoize import memoize

DRY_RUN = False
HIDE_WRONG_PLAYLISTS = True
playlistSeparator = ["–", "–", "—"]
playlistFile = "playlists4.txt"
collectionSource = "/home/toni/rawMusic"
collectionTarget = Path("/home/toni/finishedMusic")
songFileNameFormat = "{number:02d} - {artist} - {title}.mp3"

MAX_DIST = 999999

forbiddenCharacters = ["'", "&", "."]

with open("missingTemp.txt", "r") as f:
    playlistsWithMissingSongs = [line.replace("\n", "") for line in f.readlines()]

def cleanName(string):
    for character in forbiddenCharacters:
        string = string.replace(character, "")
    return string.lower()

def artistEquality(playlistArtist,  mp3Artist):
    alternateNames = {
        "Shostakovich, Dmitri": "Dmitri Shostakovich",
        "Of Mice & Men": "Of Mice  Men",
        "Emerson Lake and Palmer": "Emerson, Lake  Palmer",
        "Dvorak, Antonin": "Antonin Dvorak",
        "Donnie Trumpet & The Social Experiment": "Donnie Trumpet  The Social Experiment",
        "Ben Levin Group": "Ben Levin",
        "At The Drive In": "At The Drive-In",
        "Anderson Paak": "Anderson .Paak"
        }
    if playlistArtist in alternateNames:
        if mp3Artist == alternateNames[playlistArtist]:
            return True
    return cleanName(playlistArtist) in cleanName(mp3Artist)

def getDate(string):
    if "-" in string:
        year, month, day = string.split("-")
        return date(int(year), int(month), int(day))
    elif string.strip() == "":
        return None
    else:
        return date(year=int(string), month=1, day=1)

def getSongString(artist, album, title):
    return "{} - {} - {}".format(artist, album, title)

def stringDistance(s1, s2):
    if len(s1) == 0 or len(s2) == 0:
        print(s1, "and", s2)
        raise

    return sum(char1 != char2 for (char1, char2) in itertools.zip_longest(s1, s2)) / max(len(s1), len(s2))

def songDistance(mp3, song):
    if not artistEquality(song.artist, mp3.artist):
        return MAX_DIST
    else:
        return stringDistance(cleanName(mp3.title), cleanName(song.title))

def stripFeature(title):
    matches = re.match("(.*?)\s*(feat.|ft.|featuring)(.*)", title)
    if matches is None:
        return title
    return matches.groups()[0]

def fullStrip(s):
    return s.lower().replace(".", "").strip()

class Mp3(EasyID3):
    def __init__(self, path):
        super().__init__(path)
        self.path = path
        self.artist = stripFeature(self.tryRead("artist"))
        self.album = self.tryRead("album")
        self.title = self.tryRead("title")
        self.date = getDate(self.tryRead("date"))
        self.isNone = any(x is None for x in [self.artist, self.album, self.title])
        if cleanName(self.title).strip() == "":
            print(self, "EMPTY")
            raise

    def tryRead(self, tag):
        try:
            return self[tag][0]
        except:
            if not tag in ["album", "date"]:
                print("TAG NOT AVAILABLE: {} FOR MP3: {}".format(tag, self.path))
            return ""

    def __repr__(self):
        return getSongString(self.artist, self.album, self.title)

class Collection:
    def __init__(self, playlists_, path):
        if type(playlists_) == list:
            self.playlists = playlists_
        else:
            self.playlists = list(readPlaylists(playlists_))
        self.path = path
        self.songs = list(song for playlist in self.playlists for song in playlist.songs)
        self.songartists = list(song.artist for song in self.songs)
        self.mp3s = sorted(self.getAllMp3s(), key=lambda mp3: str(mp3))
        self.findCorrespondingSongs()

    def getAllMp3s(self):
        return list(Mp3(f) for f in self.path.rglob("*.mp3"))
    
    def findCorrespondingSongs(self):
        self.notAssigned = []
        for mp3 in self.mp3s:
            targetSong = self.findSong(mp3)
            if targetSong is None:
                self.notAssigned.append(mp3)
                continue
            targetPlaylist = next(playlist for playlist in self.playlists if targetSong in playlist.songs)
            targetPlaylist.addMp3(mp3, targetSong)
            self.songs.remove(targetSong)

    def findSong(self, mp3):
        if len(self.songs) == 0:
            return None
        song = min(self.songs, key=lambda song: songDistance(mp3, song))
        distance = songDistance(mp3, song)
        if distance == MAX_DIST:
            print("ARTIST NOT FOUND: {} ---------- {}".format(mp3, song))
            return None
        elif distance > 0:
            print("HIGH DISTANCE: {} ({})---------- {}".format(mp3, mp3.path, song))
            return None
        return song

    def copy(self, target):
        target.mkdir(exist_ok=True)
        for mp3 in self.notAssigned:
            sourcePath = mp3.path
            targetDir = Path("~", "musicNotAssigned")
            targetDir.mkdir(exist_ok=True, parents=True)
            targetPath = Path(targetDir, mp3.path.name)
            if not DRY_RUN:
                shutil.copyfile(sourcePath, targetPath)
            print("'{}' -> '{}'".format(sourcePath, targetPath))
        for playlist in self.playlists:
            self.copyPlaylist(playlist, target)

    def copyPlaylist(self, playlist, target):
        if not playlist.isComplete:
            return
        minDate = max((mp3.date for mp3 in playlist.mp3s if mp3.date is not None), default=None)
        for (song, mp3) in zip(playlist.songs, playlist.mp3s):
            resultMp3 = self.copySong(song, mp3, target)
            resultMp3.date = minDate
            self.fixTags(song, resultMp3)

    def fixTags(self, song, mp3):
        mp3["artist"] = song.artist
        mp3["album"] = song.album
        mp3["title"] = song.title
        mp3["tracknumber"] = str(song.number)
        if mp3.date is not None:
            mp3["date"] = str(mp3.date.year)
            mp3["originaldate"] = str(mp3.date.year)
        else:
            mp3["originaldate"] = ""
            print("MISSING DATE!!!")
        mp3.save()
        print("{} fixed -> {}.".format(mp3, song))

    def copySong(self, song, mp3, target):
        sourcePath = mp3.path
        targetDir = Path(target, song.artist, song.album)
        targetDir.mkdir(exist_ok=True, parents=True)
        targetPath = Path(targetDir, song.fileName)
        if not DRY_RUN:
            shutil.copyfile(sourcePath, targetPath)
        return Mp3(targetPath)
        print("'{}' -> '{}'".format(sourcePath, targetPath))

class Playlist:
    def __init__(self, titleLine, songLines):
        self.title = titleLine.replace("\n", "")
        for separator in playlistSeparator:
            self.title = self.title.replace(separator, "-")
        self.songs = [Song(s) for s in songLines]
        self.albums = set(song.album for song in self.songs)
        self.album = list(self.albums)[0]
        if self.hasMultipleAlbums:
            pass
        self.allArtists, self.artist = self.getArtists()
        for song in self.songs:
            song.artist = self.artist
        else:
            metaTitle = self.getTitleFromMetadata()
            metaTitle = self.fixUppercase(metaTitle)
            metaTitle = self.fixSpotifyPlaylistNaming2(metaTitle)
            if not HIDE_WRONG_PLAYLISTS and metaTitle != self.title and not ("(" in metaTitle or "[" in metaTitle):
                print("'{}'".format(self.getTitleFromMetadata()))
                print("'{}'".format(self.title))
                print("\n")
            self.artist, self.album = self.getArtistAndAlbumFromTitle()
        self.mp3s = [None for _ in self.songs]
        self.fixSongs()

    def fixSongs(self):
        for (i, song) in enumerate(self.songs):
            song.artist = self.artist
            song.album = self.album
            song.number = i + 1

    def getArtistAndAlbumFromTitle(self):
        split = [x for x in self.title.split("-")]
        return split[0].strip(), "-".join(split[1:]).strip()

    def fixUppercase(self, metaTitle):
        if self.title.lower() == metaTitle.lower():
            return self.title
        return metaTitle

    def fixSpotifyPlaylistNaming2(self, metaTitle):
        stripped = self.title.rstrip(" 2")
        if stripped == metaTitle:
            self.title = metaTitle
        return metaTitle

    def getArtists(self):
        allArtists = [artist for song in self.songs for artist in song.artists]
        counted = Counter(allArtists)
        return counted, max(counted.keys(), key=lambda k: counted[k])

    def getTitleFromMetadata(self):
        return "{} - {}".format(self.artist, self.album)

    @property
    def hasMultipleAlbums(self):
        return len(self.albums) != 1

    @property
    def hasMultipleArtists(self):
        return len(self.artists) != 1

    def addMp3(self, mp3, song):
        self.mp3s[self.songs.index(song)] = mp3
        # print("{} += {}".format(self.title, str(mp3.path)))

    @property
    def isComplete(self):
        return all(x is not None for x in self.mp3s)

    def resultStr(self):
        return "{}:\n{}".format(self.title, "\n".join("\t{}".format(mp3) for mp3 in self.mp3s))

class Song:
    def __init__(self, songLine):
        line = songLine.replace("\n", "")
        self.title, self.artists, self.album, self.url = line.split("\t")
        self.artists = [artist.strip() for artist in self.artists.split(",")]

    def __repr__(self):
        return getSongString(self.artist, self.album, self.title)

    @property
    def fileName(self):
        return songFileNameFormat.format(artist=self.artist, album=self.album, title=self.title, number=self.number).replace("/", "")

def isEmpty(line):
    return line.strip() == ""

def isWeirdPlaylist(title):
    return title.rstrip("\n") in ["to record", "sorted all", "Raushören", "a-morelife", "The Mountain", "good kid", "kind of blue", "californication", "anamnesis", "rest", "Guitar - Standard Tuning", "Guitar - Drop C", "Guitar - Drop D", "Guitar - Drop C#"]

def readPlaylists(filename):
    with open(filename, "r") as f:
        lines = f.readlines()
    namesAndSongs = (list(nameAndSongs) for (isEmpty, nameAndSongs) in itertools.groupby(lines, isEmpty) if not isEmpty)
    for nameAndSong in namesAndSongs:
        if isWeirdPlaylist(nameAndSong[0]):
            continue
        yield Playlist(nameAndSong[0], nameAndSong[1:])

@memoize
def getCollection(*args):
    return Collection(*args)

collection = getCollection(playlistFile, Path(collectionSource))
print("COMPLETE PLAYLISTS:")
print("\n".join(playlist.resultStr() for playlist in collection.playlists if playlist.isComplete))
print("INCOMPLETE PLAYLISTS:")
print("\n".join(playlist.resultStr() for playlist in collection.playlists if not playlist.isComplete and not playlist.title in playlistsWithMissingSongs))
collection.copy(collectionTarget)

# yaml.dump([playlist for playlist in collection.playlists if not playlist.isComplete], "incompletePlaylists.txt")
