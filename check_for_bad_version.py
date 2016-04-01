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

You can run this script with no arguments in order
to run its unit tests.

"""


from __future__ import print_function
import sys
import os
import subprocess
import unittest


def sprint(*objs):
    print(*objs, file=sys.stderr)


def myexit(status, msg):
    if (len(sys.argv)==4): # live
        sys.exit(status)
    else: # testing
        return(msg)

def erxit(msg):
    sprint(msg)
    sprint("See http://bioconductor.org/developers/how-to/version-numbering/")
    return(myexit(1, msg))



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


def process_diff(diff):
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
                if len(segs0) < 1:
                    # For some reason Karim Mezhoud gets hung up here,
                    # but says 'git diff' produces no output, so it's hard
                    # to know how to diagnose this. (accessing segs0[1] gives
                    # an index out of bounds error.) So bail for now.
                    return(myexit(0, "OK"))
                filename = segs0[1]
                segs = filename.split("/")
                if segs[len(segs)-1] == "DESCRIPTION":
                    if (filename.startswith("trunk/madman/Rpacks/") and len(segs) == 5)  \
                    or (filename.startswith("branches/RELEASE_") and \
                    len(segs) == 6 and segs[2] == "madman"  and segs[3] == "Rpacks"):
                        if len(segs) == 5:
                            release = False
                        else:
                            release = True
                        oldversion = None
                        oldbiocversion = None
                        biocversion = None
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
                    try:
                        biocversion = BiocVersion(version)
                    except InvalidSegmentNumberError:
                        return(erxit("Version number should be 3 segments; got %s in file %s." % (version, filename)))
                    except InvalidCharacterError:
                        return(erxit("Invalid character(s) in version %s in file %s." % (version, filename)))
                    mod = biocversion.y % 2
                    if release and mod == 1:
                        msg = "The y in the x.y.z version number should be even in release\n"
                        msg += "in file %s." % filename
                        return(erxit(msg))
                    if (not release) and mod == 0:
                        msg ="The y in the x.y.z version number should be odd in devel\n"
                        msg += "in file %s." % filename
                        return(erxit(msg))
                    if (oldbiocversion is not None):
                        if (biocversion.compare(oldbiocversion) == -1):
                            msg = "Can't decrement version from %s to %s.\n" % \
                              (oldversion, version)
                            msg += "Error in file %s." % filename
                            return(erxit(msg))
                        if release and ((biocversion.x != oldbiocversion.x) \
                          or (biocversion.y != oldbiocversion.y)):
                            msg = "x and y of the x.y.z version cannot change in release.\n"
                            msg += "Error in file %s." % filename
                            return(erxit(msg))
    return(myexit(0, "OK")) # just to be explicit

class TestHook(unittest.TestCase):

    def test_wrong_y_in_devel(self):
        diff='''Index: trunk/madman/Rpacks/apkg/DESCRIPTION
===================================================================
--- trunk/madman/Rpacks/apkg/DESCRIPTION    (revision 0)
+++ trunk/madman/Rpacks/apkg/DESCRIPTION    (working copy)
@@ -0,0 +1 @@
+Version: 1.0.1'''
        res = process_diff(diff)
        expected='''The y in the x.y.z version number should be odd in devel
in file trunk/madman/Rpacks/apkg/DESCRIPTION.'''
        self.assertEqual(expected, res)

    def test_wrong_y_in_release(self):
        diff='''Index: branches/RELEASE_3_2/madman/Rpacks/apkg/DESCRIPTION
===================================================================
--- branches/RELEASE_3_2/madman/Rpacks/apkg/DESCRIPTION (revision 0)
+++ branches/RELEASE_3_2/madman/Rpacks/apkg/DESCRIPTION (working copy)
@@ -0,0 +1 @@
+Version: 1.1.1'''
        res = process_diff(diff)
        expected='''The y in the x.y.z version number should be even in release
in file branches/RELEASE_3_2/madman/Rpacks/apkg/DESCRIPTION.'''
        self.assertEqual(expected, res)

    def test_wrong_number_of_segments(self):
        diff='''Index: branches/RELEASE_3_2/madman/Rpacks/apkg/DESCRIPTION
===================================================================
--- branches/RELEASE_3_2/madman/Rpacks/apkg/DESCRIPTION (revision 0)
+++ branches/RELEASE_3_2/madman/Rpacks/apkg/DESCRIPTION (working copy)
@@ -0,0 +1 @@
+Version: 1.1.1.1'''
        res = process_diff(diff)
        expected='''Version number should be 3 segments; got 1.1.1.1 in file branches/RELEASE_3_2/madman/Rpacks/apkg/DESCRIPTION.'''
        self.assertEqual(expected, res)


    def test_invalid_characters(self):
        diff='''Index: branches/RELEASE_3_2/madman/Rpacks/apkg/DESCRIPTION
===================================================================
--- branches/RELEASE_3_2/madman/Rpacks/apkg/DESCRIPTION (revision 0)
+++ branches/RELEASE_3_2/madman/Rpacks/apkg/DESCRIPTION (working copy)
@@ -0,0 +1 @@
+Version: 1.1.a1'''
        res = process_diff(diff)
        expected='''Invalid character(s) in version 1.1.a1 in file branches/RELEASE_3_2/madman/Rpacks/apkg/DESCRIPTION.'''
        self.assertEqual(expected, res)

    def test_valid_new_commit(self):
        diff='''Index: branches/RELEASE_3_2/madman/Rpacks/pkg2/DESCRIPTION
===================================================================
--- branches/RELEASE_3_2/madman/Rpacks/pkg2/DESCRIPTION (revision 0)
+++ branches/RELEASE_3_2/madman/Rpacks/pkg2/DESCRIPTION (working copy)
@@ -0,0 +1 @@
+Version: 1.2.3'''
        res = process_diff(diff)
        expected='''OK'''
        self.assertEqual(expected, res)

    def test_decrementing(self):
        diff='''Index: branches/RELEASE_3_2/madman/Rpacks/pkg2/DESCRIPTION
===================================================================
--- branches/RELEASE_3_2/madman/Rpacks/pkg2/DESCRIPTION (revision 6)
+++ branches/RELEASE_3_2/madman/Rpacks/pkg2/DESCRIPTION (working copy)
@@ -1 +1 @@
-Version: 1.2.3
+Version: 1.0.3'''
        res = process_diff(diff)
        expected='''Can't decrement version from 1.2.3 to 1.0.3.\nError in file branches/RELEASE_3_2/madman/Rpacks/pkg2/DESCRIPTION.'''
        self.assertEqual(expected, res)

    def test_change_x_in_release(self):
        diff='''Index: branches/RELEASE_3_2/madman/Rpacks/pkg2/DESCRIPTION
===================================================================
--- branches/RELEASE_3_2/madman/Rpacks/pkg2/DESCRIPTION (revision 6)
+++ branches/RELEASE_3_2/madman/Rpacks/pkg2/DESCRIPTION (working copy)
@@ -1 +1 @@
-Version: 1.2.3
+Version: 2.2.3'''
        res = process_diff(diff)
        expected='''x and y of the x.y.z version cannot change in release.\nError in file branches/RELEASE_3_2/madman/Rpacks/pkg2/DESCRIPTION.'''
        self.assertEqual(expected, res)


    def test_change_y_in_release(self):
        diff='''Index: branches/RELEASE_3_2/madman/Rpacks/pkg2/DESCRIPTION
===================================================================
--- branches/RELEASE_3_2/madman/Rpacks/pkg2/DESCRIPTION (revision 6)
+++ branches/RELEASE_3_2/madman/Rpacks/pkg2/DESCRIPTION (working copy)
@@ -1 +1 @@
-Version: 1.2.3
+Version: 1.4.3'''
        res = process_diff(diff)
        expected='''x and y of the x.y.z version cannot change in release.\nError in file branches/RELEASE_3_2/madman/Rpacks/pkg2/DESCRIPTION.'''
        self.assertEqual(expected, res)


if __name__ == "__main__":
    if (len(sys.argv) == 4): # run normally
        repos = sys.argv[1]
        txn = sys.argv[2]
        svnlook = sys.argv[3]

        try:
            diff = subprocess.check_output([svnlook, 'diff', '-t', txn, repos])
            process_diff(diff)
        except:
            # if there is a problem running svnlook,
            # we'll just exit, possibly allowing bad commits!
            myexit(0, "OK")
    else: # run unit tests
        unittest.main()
