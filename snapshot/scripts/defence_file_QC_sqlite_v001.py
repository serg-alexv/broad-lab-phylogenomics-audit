"""Bounded disk-backed file signatures and captured Linux birth identities; no science."""
import sqlite3,json
from pathlib import Path
import local_tree2_dispatcher as b

class VerifiedFiles:
 def __init__(self,path):
  self.path=Path(path);assert not self.path.exists();self.db=sqlite3.connect(self.path)
  self.db.execute('PRAGMA journal_mode=DELETE');self.db.execute('PRAGMA cache_size=-1024');self.db.execute('PRAGMA temp_store=FILE')
  self.db.execute('CREATE TABLE files(path TEXT PRIMARY KEY,sha TEXT NOT NULL,bytes INTEGER NOT NULL)')
  self.db.execute('CREATE TABLE births(boot TEXT,pid INTEGER,ticks INTEGER,value TEXT,PRIMARY KEY(boot,pid,ticks))');self.pending=0
 def __contains__(self,path):return self.db.execute('SELECT 1 FROM files WHERE path=?',(str(path),)).fetchone() is not None
 def __getitem__(self,path):
  row=self.db.execute('SELECT sha,bytes FROM files WHERE path=?',(str(path),)).fetchone();assert row is not None;return row
 def __setitem__(self,path,value):
  self.db.execute('INSERT INTO files VALUES(?,?,?)',(str(path),*value));self.pending+=1
  if self.pending>=128:self.db.commit();self.pending=0
 def __len__(self):return self.db.execute('SELECT COUNT(*) FROM files').fetchone()[0]
 def identity(self,value):
  assert type(value['pid']) is int and type(value['creation_ticks']) is int and value['boot_id']
  self.db.execute('INSERT OR IGNORE INTO births VALUES(?,?,?,?)',(value['boot_id'],value['pid'],value['creation_ticks'],json.dumps(value,separators=(',',':'))))
 def birth_count(self):return self.db.execute('SELECT COUNT(*) FROM births').fetchone()[0]
 def verify_all(self,root,guard,publish):
  self.db.commit();count=len(self)
  for i,(path,sha,size) in enumerate(self.db.execute('SELECT path,sha,bytes FROM files ORDER BY path'),1):
   guard();b.bind(root,{'path':path,'sha256':sha,'bytes':size})
   if i%128==0:publish('Final independent posthash of every saved artifact '+str(i)+'/'+str(count))
  self.db.commit()
 def close(self):self.db.commit();self.db.close()
