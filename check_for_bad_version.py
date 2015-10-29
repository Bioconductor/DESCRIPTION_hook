#!/usr/bin/env python


"""
Rejects version numbers in DESCRIPTION files which:
- Have more or less than 3 dot-separated segments
- Have any non-numeric characters within those segments
- Have a y (in x.y.z) that is even in devel or odd in release

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


repos = sys.argv[1]
txn = sys.argv[2]
svnlook = sys.argv[3]

diff = subprocess.check_output([svnlook, 'diff', '-t', txn, repos])

if (len(diff) > 0):
    lines = diff.split("\n")
    filename=None
    looking = False
    release=None
    for line in lines:
        if line.startswith("+++"):
            segs0 = line.split()
            filename = segs0[1]
            sprint(filename)
            segs = filename.split("/")
            if segs[len(segs)-1] == "DESCRIPTION":
                if (filename.startswith("trunk/madman/Rpacks") and len(segs) == 5)  \
                or (filename.startswith("branches/RELEASE_") and \
                len(segs) == 6 and segs[2] == "madman"  and segs[3] == "Rpacks"):
                    if len(segs) == 5:
                        release = False
                    else:
                        release = True
                    looking = True
            else:
                looking = False
        if looking:
            if line.startswith("+Version:"):
                segs1 = line.rstrip().split()
                version = segs1[len(segs1)-1]
                segs2 = version.split('.')
                if len(segs2) != 3:
                    sprint("Malformed version %s in file %s." % (version, filename))
                    sprint("See http://bioconductor.org/developers/how-to/version-numbering/")
                    sys.exit(1)
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
                        sprint("See http://bioconductor.org/developers/how-to/version-numbering/")
                        sys.exit(1)
                ys = segs2[1]
                y = int(ys)
                mod = y % 2
                if release and mod == 1:
                    sprint("The y in the x.y.z version number should be even in release")
                    sprint("in file %s." % filename)
                    sprint("See http://bioconductor.org/developers/how-to/version-numbering/")
                    sys.exit(1)
                if (not release) and mod == 0:
                    sprint("The y in the x.y.z version number should be odd in devel")
                    sprint("in file %s." % filename)
                    sprint("See http://bioconductor.org/developers/how-to/version-numbering/")
                    sys.exit(1)

sys.exit(0) # just to be explicit


