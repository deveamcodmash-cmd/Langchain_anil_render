import hashlib
import hmac
import json
import os
import time
import uuid

from fastapi.testclient import TestClient
from app.main import app
from app.graph import allocate_equal, search_catalogue


client=TestClient(app)
SECRET='testing-secret-that-is-longer-than-32-characters'
os.environ['FILANTROPHY_SHARED_SECRET']=SECRET


def signature(body: bytes, nonce: str, stamp: str) -> dict:
    mac=hmac.new(SECRET.encode(),stamp.encode()+b'.'+nonce.encode()+b'.'+body,hashlib.sha256).hexdigest()
    return {'X-Filantrophy-Timestamp':stamp, 'X-Filantrophy-Nonce':nonce,'X-Filantrophy-Signature':'sha256='+mac}


def test_public_health():
    assert client.get('/health').json()['status']=='ok'


def test_secret_required():
    assert client.post('/v1/health',json={}).status_code==401


def test_signed_health_and_replay():
    body=b'{}'; nonce=uuid.uuid4().hex;stamp=str(int(time.time()));headers=signature(body,nonce,stamp)
    a=client.post('/v1/health',content=body,headers=headers)
    assert a.status_code==200
    assert client.post('/v1/health',content=body,headers=headers).status_code==401


def test_expired_rejected():
    body=b'{}'; stamp=str(int(time.time())-999)
    assert client.post('/v1/health',content=body,headers=signature(body,uuid.uuid4().hex,stamp)).status_code==401


def test_invalid_chat_body():
    body=json.dumps({'message':'hi','campaigns':[{'id':0,'title':'bad'}]}).encode()
    resp=client.post('/v1/chat',content=body,headers=signature(body,uuid.uuid4().hex,str(int(time.time()))))
    assert resp.status_code==422


def test_balanced_allocation():
    campaigns=[{'id':1,'currency':'NGN'},{'id':2,'currency':'NGN'},{'id':3,'currency':'NGN'}]
    plan=allocate_equal(3000,campaigns,'NGN')
    assert sum(i.amount for i in plan.items)==3000
    assert [i.amount for i in plan.items]==[1000,1000,1000]


def test_discovery_filters():
    c=[{'id':1,'title':'School Supplies','category':'Education','location':'Lagos','summary':''},
       {'id':2,'title':'Water Project','category':'Water','location':'Abuja','summary':''}]
    assert [x['id'] for x in search_catalogue(c,['water'],[],'help',2)]==[2]


def test_signed_chat_contract(monkeypatch):
    from app import graph
    from app.schemas import ChatResponse, SuggestedPlan, SuggestedAllocation
    monkeypatch.setattr(graph, 'run_workflow', lambda req: ChatResponse(
        reply='Draft prepared for your approval.', campaign_ids=[1,2,3],
        plan_proposal=SuggestedPlan(currency='NGN',budget=3000,
            items=[SuggestedAllocation(id=i,amount=1000) for i in [1,2,3]]),
        agents_run=['Supervisor','Discovery','Recommendation','Giving Plan']
    ))
    payload={'message':'Split 3000 across 3 campaigns','campaigns':[
        {'id':i,'title':f'Campaign {i}','currency':'NGN'} for i in [1,2,3]]}
    body=json.dumps(payload).encode(); headers=signature(body,uuid.uuid4().hex,str(int(time.time())))
    result=client.post('/v1/chat',content=body,headers=headers)
    assert result.status_code==200,result.text
    assert [x['amount'] for x in result.json()['plan_proposal']['items']]==[1000,1000,1000]
    assert result.json()['agents_run'][-1]=='Giving Plan'


def test_public_brand_normalization():
    from app.graph import normalize_public_reply
    result=normalize_public_reply('Philanthropy uses a Joomla server. Ask Joomla about philanthropy.')
    assert 'Philanthropy' not in result
    assert 'Joomla' not in result
    assert 'Filantrophy' in result
    assert normalize_public_reply('Filantrophy supports NGN 3,000') == 'Filantrophy supports NGN 3,000'
