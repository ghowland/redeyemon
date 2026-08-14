"""
archive

by Geoff Howland  <geoff AT ge01f DOT com>

Archives changes, storing each change of state in an appended file.

Must specify file size to rotate, so we can continuously append to the current
file, and delete only files after snapshotting.

TODO(g): Merge snapshop and archive.  If we want to really track the data, we
MUST use both, so keeping them separate is pointless.
"""

