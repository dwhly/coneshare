import os,sys
from itertools import product
from unittest.mock import Mock,patch
sys.dont_write_bytecode=True
sys.path.insert(0,'backend')
for k in ['OPENROUTER_API_KEY','PLACE_MODEL']:os.environ.pop(k,None)
from dealroom_sign import placement
from dealroom_sign.tests import placement_r21_review_cases as rc
from dealroom_sign.tests.test_placement_r17 import signers
from dealroom_sign.tests.test_placement_r14 import in_process
hla=rc.RECITALS['parsed']; nw=[(y,t.replace('HARBOR LIGHT ANALYTICS, INC.','NORTHWIND TRADERS LLC'),r,x) for y,t,r,x in hla]
with patch('httpx.Client.send',Mock(side_effect=AssertionError('http'))):
 for layout,heading,extra,both in product(('same','guarantor','split'),('RECIPIENT:','THE RECIPIENT','Recipient'),('none','placeholders'),(False,True)):
  pages,allowed=rc.layout_pages(layout,'none',heading,extra,'group')
  pages=[hla,nw]+pages[1:];allowed={k:(p+1,x,y,e) for k,(p,x,y,e) in allowed.items()}
  result=in_process(placement,rc.pages_pdf(pages),signers(both),Mock())
  print(layout,heading,extra,both,result['status'],bool(rc.wrong_fields(result,allowed)))
