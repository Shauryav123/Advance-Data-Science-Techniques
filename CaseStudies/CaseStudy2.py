p=input('Patient name: ')
def pc(t):
 parts=t.split(',')
 r=[]
 for part in parts:
  part=part.strip()
  if part!='': r.append(part)
 return r
req=pc(input('Requested depts (comma separated): '))
avail=pc(input('Available depts (comma separated): '))
prev=pc(input('Previously visited depts (comma separated): '))
emer=pc(input('Emergency depts (comma separated): '))
pref=pc(input('Preferred doctors (comma separated): '))
docs=pc(input('Available doctors (comma separated): '))
rs=set(req);as_=set(avail);ps=set(prev);es=set(emer)
common=list(rs&as_);unavail=list(rs-as_);prev_req=list(rs&ps);urgent=list(rs&es)
dup=[]
for x in req:
 if req.count(x)>1 and x not in dup: dup.append(x)
rec=None
if urgent: rec=urgent[0]
elif common: rec=common[0]
elif avail: rec=avail[0]
status="Immediate" if urgent else ("Scheduled" if common else "Unavailable")
print('\nAppointment Report')
print('Patient:',p)
print('Requested:',req)
print('Available:',avail)
print('Common:',common)
print('Unavailable:',unavail)
print('Previous:',prev_req)
print('Duplicates:',dup)
print('Emergency:',emer)
print('Recommended:',rec)
print('Status:',status)
a=None
for d in pref:
 for dd in docs:
  if d==dd: a=d;break
 if a: break
if a: print('Assigned doctor:',a)
else: print('Available doctors:',docs)
