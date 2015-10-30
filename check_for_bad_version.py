#!/usr/bin/env python


"""
Rejects version numbers in DESCRIPTION files which:
- Have more or less than 3 dot-separated segments
- Have any non-numeric characters within those segments
- Have a y (in x.y.z) that is even in devel or odd in release
- Have a lower version number than before
- Change x or y in release

If the commit is rejected, users are referred to
http://bioconductor.org/developers/how-to/version-numbering/ .

This file lives in https://github.com/Bioconductor/DESCRIPTION_hook

This script should be called like this from the pre-commit file:

$REPOS/hooks/DESCRIPTION_hook/check_for_bad_version.py "$REPOS" "$TXN" "$SVNLOOK"|| exit 1

TODO:
In future, perhaps the hook can detect if you are decrementing
the version number and reject the commit if so.

"""


from __future__ import print_function
import sys
import os
import subprocess


def sprint(*objs):
    print(*objs, file=sys.stderr)

def erxit():
    sprint("See http://bioconductor.org/developers/how-to/version-numbering/")
    sys.exit(1)



class InvalidSegmentNumberError:
    '''An invalid BiocVersion - does not have 3 segments'''

class InvalidCharacterError:
    '''Version has non-numeric character in a segment'''

class BiocVersion:
    x = 0
    y = 0
    z = 0

    def __init__(self, vstr):
        segs = vstr.strip().split(".")
        if len(segs) != 3:
            raise(InvalidSegmentNumberError)
        for seg in segs:
            fail = False
            if '-' in seg:
                fail = True
            try:
                int(seg)
            except:
                fail = True
            if fail:
                raise(InvalidCharacterError)
        self.x = int(segs[0])
        self.y = int(segs[1])
        self.z = int(segs[2])

    def compare(self, other):
        if self.x > other.x:
            return 1
        if self.x < other.x:
            return -1
        if self.x == other.x:
            if self.y > other.y:
                return 1
            if self.y < other.y:
                return -1
            if self.y == other.y:
                if self.z > other.z:
                    return 1
                if self.z < other.z:
                    return -1
                return 0

    def __str__(self):
        return str(self.x) + "." + str(self.y) + "." + str(self.z)

repos = sys.argv[1]
txn = sys.argv[2]
svnlook = sys.argv[3]

diff = subprocess.check_output([svnlook, 'diff', '-t', txn, repos])

if (len(diff) > 0):
    lines = diff.split("\n")
    filename=None
    looking = False
    release=None
    oldversion=None
    oldbiocversion=None
    for line in lines:
        if line.startswith("+++"):
            segs0 = line.split()
            filename = segs0[1]
            segs = filename.split("/")
            if segs[len(segs)-1] == "DESCRIPTION":
                if (filename.startswith("trunk/madman/Rpacks") and len(segs) == 5)  \
                or (filename.startswith("branches/RELEASE_") and \
                len(segs) == 6 and segs[2] == "madman"  and segs[3] == "Rpacks"):
                    if len(segs) == 5:
                        release = False
                    else:
                        release = True
                    oldversion = None
                    oldbiocversion = None
                    looking = True
            else:
                looking = False
        if looking:
            if line.startswith("-Version:"):
                segs1 = line.rstrip().split()
                oldversion = segs1[len(segs1)-1]
                try:
                    oldbiocversion = BiocVersion(oldversion)
                except:
                    pass
            if line.startswith("+Version:"):
                segs1 = line.rstrip().split()
                version = segs1[len(segs1)-1]
                segs2 = version.split('.')
                if len(segs2) != 3:
                    sprint("Malformed version %s in file %s." % (version, filename))
                    erxit()
                for seg in segs2:
                    fail = False
                    if '-' in seg:
                        fail = True
                    try:
                        int(seg)
                    except: 
                        fail = True
                    if fail:
                        sprint("Malformed version %s in file %s." % (version, filename))
                        erxit()
                ys = segs2[1]
                y = int(ys)
                mod = y % 2
                if release and mod == 1:
                    sprint("The y in the x.y.z version number should be even in release")
                    sprint("in file %s." % filename)
                    erxit()
                if (not release) and mod == 0:
                    sprint("The y in the x.y.z version number should be odd in devel")
                    sprint("in file %s." % filename)
                    erxit()
                biocversion = BiocVersion(version)
                if (oldbiocversion is not None):
                    if (biocversion.compare(oldbiocversion) == -1):
                        sprint("Can't decrement version from %s to %s." % \
                          (oldversion, version))
                        sprint("Error in file %s." % filename)
                        erxit()
                    if release and ((biocversion.x != oldbiocversion.x) \
                      or (biocversion.y != oldbiocversion.y)):
                        sprint("x and y of the x.y.z version cannot change in release.")
                        sprint("Error in file %s." % filename)
                        erxit()



sys.exit(0) # just to be explicit


