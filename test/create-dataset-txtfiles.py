#!/usr/bin/env python

import sys, glob

if len(sys.argv) != 3:
   print "Usage: %s <root file pattern with full path> <xml output file>"
   sys.exit(1)

pattern = sys.argv[1]
out = open(sys.argv[2], 'w')
l = glob.glob(pattern)
print "Found %d files matching pattern" % len(l)
l.sort()
for file in l:
   file = file.split('/pnfs/desy.de/cms/tier2')[1]
   out.write('%s\n' % file)
out.close()

