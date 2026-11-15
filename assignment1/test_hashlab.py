from hashlab import *
import hashlib, pytest

def test_vector():assert digest(b'abc')['sha256']==hashlib.sha256(b'abc').hexdigest()
def test_newline():assert digest(b'abc')!=digest(b'abc\n')
def test_canonical():assert canonical({'b':2,'a':1})==canonical({'a':1,'b':2})
def test_avalanche():assert 0<avalanche(b'abc',7)['changed_bits_in_digest']<=256
def test_file(tmp_path):
 p=tmp_path/'big';p.write_bytes(b'a'*1000000)
 assert hash_file(p)['sha256']==hashlib.sha256(p.read_bytes()).hexdigest()
