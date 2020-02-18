import pickle
from pathlib import Path

memoizeDir = Path(".memoize")
if not memoizeDir.is_dir():
    memoizeDir.mkdir()

def memoize(func):
    def wrapper(*args, **kwargs):
        callName = func.__name__ + str(getHash(args, kwargs))
        resultFile = Path(memoizeDir, callName)
        if resultFile.is_file():
            result, args_, kwargs_ = pickle.load(resultFile.open("rb"))
            if args_ == args and kwargs_ == kwargs:
                return result
            else: # hash collision
                return func(*args, **kwargs)
        else:
            result = func(*args, **kwargs)
            pickle.dump((result, args, kwargs), resultFile.open("wb"))
            return result
    return wrapper

def getHash(args, kwargs):
    return (tuple(convertToHashable(arg) for arg in args) + tuple(convertToHashable((k, v)) for (k, v) in kwargs.items())).__hash__()

def convertToHashable(obj):
    try:
        return obj.__hash__()
    except TypeError:
        return str(obj).__hash__()
