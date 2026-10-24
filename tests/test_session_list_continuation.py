from datetime import date, timedelta
import pytest
from tribunal.models import CouncilSession
from tests.test_core_policy_completion import granted_roles

pytestmark = pytest.mark.django_db


def test_session_pagination_recovers_records_beyond_previous_cap(granted_roles, people, client):
    start = date(2030, 1, 1)
    CouncilSession.objects.bulk_create([CouncilSession(date=start+timedelta(days=i)) for i in range(105)])
    expected = [str(pk) for pk in CouncilSession.objects.order_by('-date','-id').values_list('id',flat=True)]
    client.force_login(people['admin'])
    with granted_roles('ctm_app', session=True):
        first = client.get('/api/sessions/').json()
        last = client.get(f"/api/sessions/?offset={first['next_offset']}").json()
        assert first['limit'] == 100 and first['next_offset'] == 100
        assert last['next_offset'] is None
        assert [row['id'] for row in first['items']+last['items']] == expected
        assert first['items'][0]['date'] == '2030-04-15'
        assert first['items'][0]['reference'] == 'CS20300415'
        assert first['items'][0]['can_manage'] is True


@pytest.mark.parametrize('role',['member','president','admin','secretary'])
def test_session_filters_precede_pagination_and_preserve_authority(granted_roles, people, client, role):
    CouncilSession.objects.bulk_create([
        CouncilSession(date=date(2030,1,i),state='closed' if i%2==0 else 'planned')
        for i in range(1,10)
    ])
    client.force_login(people[role])
    with granted_roles('ctm_app', session=True):
        result = client.get('/api/sessions/?state=closed&date_from=2030-01-02&date_to=2030-01-06&limit=2')
        assert result.status_code == 200, result.content
        first = result.json()
        assert [row['date'] for row in first['items']] == ['2030-01-06','2030-01-04']
        assert first['next_offset'] == 2
        last = client.get('/api/sessions/?state=closed&date_from=2030-01-02&date_to=2030-01-06&limit=2&offset=2').json()
        assert [row['date'] for row in last['items']] == ['2030-01-02']
        assert last['next_offset'] is None
        assert all(row['can_manage'] is False for row in first['items'])
        assert all(row['can_close'] is False for row in first['items'])
        assert client.get('/api/sessions/?state=planned&date_from=2030-01-01&date_to=2030-01-01').json()['items'][0]['can_manage'] is (role in {'admin','secretary'})


@pytest.mark.parametrize('query',[
    'state=unknown','state=','state=closed&state=planned',
    'date_from=2030-02-30','date_to=20300101','date_to=',
    'date_from=2030-02-01&date_to=2030-01-01',
    'date_from=2030-01-01&date_from=2030-01-02',
    'limit=251','offset=-1',
])
def test_invalid_session_filters_are_rejected(granted_roles, people, client, query):
    client.force_login(people['member'])
    with granted_roles('ctm_app', session=True):
        response = client.get('/api/sessions/?'+query)
        assert response.status_code == 422, response.content
        assert response['Cache-Control'] == 'private, no-store'


def test_applicant_cannot_read_session_pages_or_counts(granted_roles, people, client):
    CouncilSession.objects.create(date=date(2030,1,1))
    assert client.get('/api/sessions/?limit=1').status_code == 401
    client.force_login(people['applicant'])
    with granted_roles('ctm_app', session=True):
        response = client.get('/api/sessions/?limit=1&state=planned')
        assert response.status_code == 403
        assert 'items' not in response.json() and 'next_offset' not in response.json()
