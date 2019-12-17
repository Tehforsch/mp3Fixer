import itertools
from collections import Counter
from pathlib import Path
import os
from mutagen.easyid3 import EasyID3
import re
import shutil
from datetime import date

DRY_RUN = False
HIDE_WRONG_PLAYLISTS = True
playlistSeparator = ["–", "–", "—"]
playlistFile = "playlists3.txt"
collectionSource = "/home/toni/oldMusic"
collectionTarget = Path("target")
songFileNameFormat = "{number:02d} - {artist} - {title}.mp3"


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
    return sum(char1 != char2 for (char1, char2) in itertools.zip_longest(s1, s2)) / max(len(s1), len(s2))

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
<<<<<<< HEAD
        self.date = getDate(self.tryRead("date"))
||||||| merged common ancestors
=======
        self.isNone = any(x is None for x in [self.artist, self.album, self.title])
>>>>>>> e0cca04f38782b335a7f024004ebbd2a8d8a5699

    def tryRead(self, tag):
        try:
            return self[tag][0]
        except:
            if not tag in ["album"]:
                print("TAG NOT AVAILABLE: {} FOR MP3: {}".format(tag, self.path))
            return ""

    def __repr__(self):
        return getSongString(self.artist, self.album, self.title)

class Collection:
    def __init__(self, playlistFile, path):
        self.playlists = list(readPlaylists(playlistFile))
        self.path = path
        self.songs = list(song for playlist in self.playlists for song in playlist.songs)
        self.mp3s = sorted(self.getAllMp3s(), key=lambda mp3: str(mp3))
        print("Loaded all mp3s")
        self.findCorrespondingSongs()

    def getAllMp3s(self):
        return list(Mp3(f) for f in self.path.glob("*.mp3"))
    
    def findCorrespondingSongs(self):
        for mp3 in self.mp3s:
            targetSong = self.findSong(mp3)
            targetPlaylist = next(playlist for playlist in self.playlists if targetSong in playlist.songs)
            targetPlaylist.addMp3(mp3, targetSong)
            self.songs.remove(targetSong)

    def findSong(self, mp3):
        return min(self.songs, key=lambda song:sum(stringDistance(x1, x2) for (x1, x2) in zip([mp3.artist, mp3.album, mp3.title], [song.artist, song.album, song.title])))

    def copy(self, target):
        target.mkdir(exist_ok=True)
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
<<<<<<< HEAD
        if mp3.date is not None:
            mp3["date"] = str(mp3.date.year)
            mp3["originaldate"] = str(mp3.date.year)
        else:
            mp3["originaldate"] = ""
            print("MISSING DATE!!!")
||||||| merged common ancestors
=======
        mp3["date"] = ""
>>>>>>> e0cca04f38782b335a7f024004ebbd2a8d8a5699
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
        print("{} += {}".format(self.title, str(song)))

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

collection = Collection(playlistFile, Path(collectionSource))
print("COMPLETE PLAYLISTS:")
print("\n".join(playlist.resultStr() for playlist in collection.playlists if playlist.isComplete))
collection.copy(collectionTarget)
