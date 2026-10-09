"""Local owner CLI only. Never expose these operations as public HTTP routes."""
import argparse,json
from pilot import application
p=argparse.ArgumentParser();p.add_argument('action',choices=['invite','revoke','delete']);p.add_argument('--code');p.add_argument('--hours',type=int,default=24);a=p.parse_args()
if a.action=='invite':print(application.invite(a.hours))
else:
 if not a.code:raise SystemExit('--code required')
 digest=application.digest(a.code)
 with application.db() as d:
  row=d.execute('SELECT session FROM invites WHERE digest=?',(digest,)).fetchone()
  if not row:raise SystemExit('Invite not found')
  d.execute('UPDATE invites SET revoked=1 WHERE digest=?',(digest,));d.execute('DELETE FROM tickets WHERE invite=?',(digest,))
 if a.action=='delete' and row[0]:
  with application.brain.db() as d:
   d.execute('DELETE FROM live_events WHERE session_id=?',(row[0],));d.execute('DELETE FROM live_sessions WHERE id=?',(row[0],))
 print(json.dumps({'done':a.action}))
