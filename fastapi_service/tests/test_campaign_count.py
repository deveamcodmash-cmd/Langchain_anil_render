from app.graph import requested_count, search_catalogue

def test_exact_counts():
    assert requested_count('Give me 1 campaign',3,20) == 1
    assert requested_count('Show one campaign',3,20) == 1
    assert requested_count('Show 5 campaigns',3,20) == 5
    assert requested_count('Show all campaigns',3,20) == 20
    assert requested_count('Show all campaigns',3,20,plan=True) == 10
    assert requested_count('Show 8 campaigns',3,4) == 4

def test_search_returns_exact_requested_max():
    c=[{'id':i,'title':f'Campaign {i}','category':'Education','location':'Nigeria','summary':''} for i in range(1,15)]
    assert len(search_catalogue(c,[],[],'Show one campaign',1))==1
    assert len(search_catalogue(c,[],[],'Show all campaigns',14))==14
