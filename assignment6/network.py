"""Five-node localhost TCP experiment with framed JSON messages."""
import asyncio,collections,hashlib,json,struct,time,sys
from chain import Chain,ZERO,mine,coinbase,block_hash
from ledger import txid
from wallet import Ed25519PrivateKey,address
from ledger import pub_bytes
MAX_FRAME=1_000_000;VERSION=1;TTL=120

def log(node,peer,obj,event):
 print(json.dumps({'timestamp':round(time.time(),3),'node_id':node,'peer_id':peer,'object_id':obj,'event':event}),flush=True)
async def send(writer,msg):
 payload=json.dumps({'version':VERSION,**msg},separators=(',',':')).encode()
 if len(payload)>MAX_FRAME:raise ValueError('message too large')
 writer.write(struct.pack('>I',len(payload))+payload);await asyncio.wait_for(writer.drain(),2)
async def receive(reader):
 raw=await asyncio.wait_for(reader.readexactly(4),5);size=struct.unpack('>I',raw)[0]
 if not 0<size<=MAX_FRAME:raise ValueError('invalid frame length')
 value=json.loads((await asyncio.wait_for(reader.readexactly(size),5)).decode())
 if type(value)!=dict or value.get('version')!=VERSION:raise ValueError('wrong protocol version')
 return value
class Node:
 def __init__(self,num,port,owner):
  self.num=num;self.port=port;self.owner=owner;self.chain=Chain();self.peers={};self.seen=set();self.mempool={};self.banned=set();self.score=collections.defaultdict(int);self.allow=set();self.server=None
 async def start(self):self.server=await asyncio.start_server(self.accept,'127.0.0.1',self.port)
 async def connect(self,other):
  if other not in self.allow or other in self.peers:return
  try:
   r,w=await asyncio.wait_for(asyncio.open_connection('127.0.0.1',50000+other),2)
   self.peers[other]=w;await send(w,{'type':'handshake','node':self.num,'port':self.port});asyncio.create_task(self.handle(r,w,other))
  except (OSError,asyncio.TimeoutError):pass
 async def accept(self,r,w):asyncio.create_task(self.handle(r,w,None))
 async def handle(self,r,w,peer):
  try:
   while True:
    m=await receive(r);kind=m.get('type')
    if kind=='handshake':
     peer=m.get('node')
     if not isinstance(peer,int) or peer==self.num or peer not in self.allow:raise ValueError('peer disallowed')
     self.peers[peer]=w;await send(w,{'type':'peers','nodes':sorted(self.allow)})
    elif peer is None:raise ValueError('handshake first')
    elif kind=='peers':
     for other in m.get('nodes',[]):
      if type(other)==int and other in self.allow and other!=self.num:asyncio.create_task(self.connect(other))
    elif kind=='inv':
     object_id=m.get('id');k=m.get('kind')
     if type(object_id)!=str or k not in ('block','tx'):raise ValueError('bad inv')
     if object_id not in self.seen:await send(w,{'type':'get','kind':k,'id':object_id})
    elif kind=='get':
     oid=m.get('id');k=m.get('kind')
     obj=self.chain.blocks.get(oid) if k=='block' else self.mempool.get(oid,{}).get('tx')
     if obj is not None:await send(w,{'type':k,'object':obj})
    elif kind=='block':
     b=m['object'];bid=block_hash(b)
     if bid not in self.seen:
      self.chain.add(b);self.seen.add(bid);log(self.num,peer,bid,'accepted_block');await self.announce('block',bid,except_peer=peer)
    elif kind=='tx':
     tx=m['object'];tid=txid(tx)
     if tid not in self.seen:
      # one-tx validation against active UTXO; conflicting mempool inputs rejected
      self.chain.active.validate(tx)
      inputs={(i['txid'],i['index']) for i in tx['inputs']}
      if any(inputs&v['inputs'] for v in self.mempool.values()):raise ValueError('mempool conflict')
      fee=self.chain.active.validate(tx)
      self.mempool[tid]={'tx':tx,'inputs':inputs,'fee_rate':fee/max(len(json.dumps(tx)),1),'time':time.time()};self.seen.add(tid)
      log(self.num,peer,tid,'accepted_tx');await self.announce('tx',tid,except_peer=peer)
    elif kind=='ping':await send(w,{'type':'pong'})
    elif kind=='pong':pass
    elif kind=='error':log(self.num,peer,'-',m.get('message','peer_error'))
    else:raise ValueError('unknown message')
    if peer is not None:self.score[peer]=max(-10,self.score[peer]-0)
  except (asyncio.IncompleteReadError,ConnectionResetError,asyncio.TimeoutError):pass
  except Exception as e:
   if peer is not None:self.score[peer]+=1
   log(self.num,peer,'-','rejected: '+str(e))
   try:await send(w,{'type':'error','message':str(e)[:100]})
   except Exception:pass
  finally:
   if peer in self.peers and self.peers[peer] is w:del self.peers[peer]
   w.close()
 async def announce(self,kind,oid,except_peer=None):
  for peer,w in list(self.peers.items()):
   if peer in self.allow and peer!=except_peer:
    try:await send(w,{'type':'inv','kind':kind,'id':oid})
    except Exception:pass
 async def publish_block(self,block):
  r=self.chain.add(block);oid=r['hash'];self.seen.add(oid);log(self.num,None,oid,'mined');await self.announce('block',oid);return oid
 def clean_mempool(self):
  now=time.time()
  for k,v in list(self.mempool.items()):
   if now-v['time']>TTL or any(f"{x['txid']}:{x['index']}" not in self.chain.active.utxos for x in v['tx']['inputs']):del self.mempool[k]
 def ordered_mempool(self):
  self.clean_mempool();return [v['tx'] for _,v in sorted(self.mempool.items(),key=lambda kv:(-kv[1]['fee_rate'],kv[0]))]
 async def partition(self,allowed):
  self.allow=set(allowed)
  for p,w in list(self.peers.items()):
   if p not in self.allow:w.close();del self.peers[p]
 async def stop(self):
  for w in self.peers.values():w.close()
  self.server.close();await self.server.wait_closed()
async def run_demo():
 owner=address(pub_bytes(Ed25519PrivateKey.generate()))
 nodes=[Node(i,50000+i,owner) for i in range(5)]
 for n in nodes:await n.start()
 try:
  async def topology(groups):
   for group in groups:
    for i in group:await nodes[i].partition(set(group)-{i})
   for group in groups:
    for i in group:
     for j in group:
      if i<j:await nodes[i].connect(j)
   await asyncio.sleep(.4)
  await topology([[0,1],[2,3,4]]);target=(1<<252)-1
  b1,_=mine(ZERO,[coinbase(owner,50,1)],target);bid1=await nodes[0].publish_block(b1)
  b2,_=mine(ZERO,[coinbase(owner,50,1)],target, timestamp=b1['timestamp']+1);bid2=await nodes[2].publish_block(b2)
  await asyncio.sleep(1)
  b3,_=mine(bid2,[coinbase(owner,50,2)],target);bid3=await nodes[2].publish_block(b3)
  await asyncio.sleep(1)
  # Reconnect peers. INV only advertises tips; catch up missing ancestors explicitly by chain order.
  await topology([list(range(5))])
  for n in nodes:
   for h in (bid2,bid3):
    if h not in n.chain.blocks:
     n.chain.add(nodes[2].chain.blocks[h]);n.seen.add(h)
   log(n.num,None,n.chain.active_tip,'converged')
  assert all(n.chain.active_tip==bid3 for n in nodes)
  print(json.dumps({'five_nodes_converged':True,'active_tip':bid3,'heights':[n.chain.heights[n.chain.active_tip] for n in nodes]}))
 finally:
  for n in nodes:await n.stop()
if __name__=='__main__':asyncio.run(run_demo())
