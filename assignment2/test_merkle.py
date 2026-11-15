from merkle import *
import pytest

def test_sizes():
 for n in (0,1,2,3,5,8,100):
  items=[str(i).encode() for i in range(n)];r=root(items)
  for i in range(n):assert verify(items[i],prove(items,i),r)
def test_tamper():
 data=[b'a',b'b',b'c',b'd',b'e'];p=prove(data,2)
 assert not verify(b'nope',p,root(data))
 assert not verify(data[2],{**p,'leaf_index':3},root(data))
 assert not verify(data[2],{**p,'siblings':p['siblings']+p['siblings']},root(data))
