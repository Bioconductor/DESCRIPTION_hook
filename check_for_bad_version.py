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
import subprocess
import re

def sprint(*objs):
    print(*objs, file=sys.stderr)

repos = sys.argv[1]
txn = sys.argv[2]
svnlook = sys.argv[3]

diff = subprocess.check_output([svnlook, 'diff', '-t', txn, repos])

if (len(diff) == 0):
    sys.exit(0)

filename = None
looking = False
release = None

for line in diff.split("\n"):
    if line.startswith("+++ "):
        looking = False
    m = re.search("\+\+\+ ((\S+)/madman/Rpacks/[^/]+/DESCRIPTION)", line)
    if m:
        filename = m.group(1)
        if m.group(2) == "trunk":
            release = False
        elif m.group(2).startswith("branches/RELEASE_"):
            release = True
        else:
            continue
        looking = True
        continue
    if looking:
        mv = re.search("\+Version:\s*(\d+)\.(\d+)\.(\d+)(.*?)\s*$", line)
        if mv:
            try:
                if len(mv.group(4)):
                    raise
                x = int(mv.group(1))
                y = int(mv.group(2))
                z = int(mv.group(3))
            except:
                sprint("Malformed version line '%s' in file %s." % (line, filename))
                sprint("See http://bioconductor.org/developers/how-to/version-numbering/")
                sys.exit(1)

            mod = y % 2
            if release and mod == 1:
                sprint("The y in the x.y.z version number should be even in release")
                sprint("in file %s." % filename)
                sprint("See http://bioconductor.org/developers/how-to/version-numbering/")
                sys.exit(1)
            elif not release and mod == 0:
                sprint("The y in the x.y.z version number should be odd in devel")
                sprint("in file %s." % filename)
                sprint("See http://bioconductor.org/developers/how-to/version-numbering/")
                sys.exit(1)

sys.exit(0) # just to be explicit
