import asyncio,struct,pytest
from network import send,receive,MAX_FRAME
async def roundtrip():
 q=asyncio.Queue()
 class W:
  def write(self,b):q.put_nowait(b)
  async def drain(self):pass
 class R:
  def __init__(self):self.buf=b''
  async def readexactly(self,n):
   while len(self.buf)<n:self.buf+=await q.get()
   out,self.buf=self.buf[:n],self.buf[n:];return out
 await send(W(),{'type':'ping'});assert (await receive(R()))['type']=='ping'
def test_frames():asyncio.run(roundtrip())
def test_size_limit():
 async def check():
  r=asyncio.StreamReader();r.feed_data(struct.pack('>I',MAX_FRAME+1));r.feed_eof()
  with pytest.raises(ValueError):await receive(r)
 asyncio.run(check())
