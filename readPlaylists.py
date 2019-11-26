import itertools
from collections import Counter

playlistSeparator = ["–", "–", "—"]

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
            if metaTitle != self.title and not ("(" in metaTitle or "[" in metaTitle):
                print("'{}'".format(self.getTitleFromMetadata()))
                print("'{}'".format(self.title))
                print("\n")

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

class Song:
    def __init__(self, songLine):
        line = songLine.replace("\n", "")
        self.title, self.artists, self.album, self.url = line.split("\t")
        self.artists = [artist.strip() for artist in self.artists.split(",")]

    def __repr__(self):
        return "{} - {} - {}".format(self.artist, self.album, self.title)

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
        Playlist(nameAndSong[0], nameAndSong[1:])


filename = "playlists3.txt"
readPlaylists(filename)

