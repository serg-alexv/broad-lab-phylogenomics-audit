"""Source-only proposed race repair: one stat snapshot, exact birth, RSS sum."""
from pathlib import Path
import os

def sample_owned_rss(identities, *, read_text=None, page_size=None):
    read_text = read_text or (lambda pid: Path('/proc/'+str(pid)+'/stat').read_text())
    page_size = page_size or os.sysconf('SC_PAGE_SIZE')
    total = 0
    for identity in identities:
        try:
            fields = read_text(identity['pid']).rsplit(')', 1)[1].split()
        except (FileNotFoundError, ProcessLookupError):
            continue
        if int(fields[19]) != identity['creation_ticks']:
            continue
        total += max(0, int(fields[21])) * page_size
    return total
