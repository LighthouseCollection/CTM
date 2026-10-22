"""A generic browser entry cannot disclose a request or change capability APIs."""
import uuid
import pytest
from tests.test_core_policy_completion import granted_roles
from tests.test_external_link_projection import priest_request

pytestmark = pytest.mark.django_db


@pytest.mark.parametrize('accept', [
    'text/html',
    'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'application/json;q=0.2,text/html;q=0.9',
])
def test_html_navigation_redirects_without_request_lookup(granted_roles, client, accept):
    target=uuid.uuid4()
    from django.db import connection
    from django.test.utils import CaptureQueriesContext
    with granted_roles('ctm_app', session=True), CaptureQueriesContext(connection) as captured:
        response=client.get(f'/external/reports/{target}/', HTTP_ACCEPT=accept)
    assert not any('tribunal_reportrequest' in query['sql'] for query in captured.captured_queries)
    assert response.status_code==302
    assert response['Location']=='/static/ctm/external-report.html'
    assert response['Cache-Control']=='private, no-store'
    assert response['Referrer-Policy']=='no-referrer'
    assert response['X-Content-Type-Options']=='nosniff'
    assert {'Accept','Authorization'} <= set(response['Vary'].split(', '))
    assert str(target) not in response.content.decode()
    assert not response.cookies


@pytest.mark.parametrize('accept', [None, '*/*', 'application/json', 'text/html;q=0,application/json',
    'application/json;q=1,text/html;q=0.1'])
def test_api_negotiation_stays_fail_closed_without_capability(granted_roles, client, accept):
    headers={} if accept is None else {'HTTP_ACCEPT':accept}
    with granted_roles('ctm_app', session=True):
        response=client.get(f'/external/reports/{uuid.uuid4()}/', **headers)
    assert response.status_code==403 and response.json()=={'error':'link_unavailable'}
    assert {'Accept','Authorization'} <= set(response['Vary'].split(', '))


@pytest.mark.parametrize('authorization', ['', 'Bearer wrong', 'Basic wrong'])
def test_authorization_always_uses_json_even_with_html_accept(granted_roles, client, authorization):
    with granted_roles('ctm_app', session=True):
        response=client.get(f'/external/reports/{uuid.uuid4()}/',
            HTTP_ACCEPT='text/html', HTTP_AUTHORIZATION=authorization)
    assert response.status_code==403 and response.json()=={'error':'link_unavailable'}
    assert 'Location' not in response


@pytest.mark.parametrize('method', ['post','head','put'])
def test_browser_entry_does_not_redirect_other_methods(granted_roles,client,method):
    with granted_roles('ctm_app',session=True):
        response=getattr(client,method)(f'/external/reports/{uuid.uuid4()}/', HTTP_ACCEPT='text/html')
    assert response.status_code==(403 if method=='post' else 405)
    assert 'Location' not in response


def test_redirect_does_not_forward_query_credentials_or_content(granted_roles,client):
    with granted_roles('ctm_app',session=True):
        response=client.get(f'/external/reports/{uuid.uuid4()}/?token=private-query&next=https://invalid.example',HTTP_ACCEPT='text/html')
    assert response.status_code==302
    assert response['Location']=='/static/ctm/external-report.html'
    assert b'private-query' not in response.content


def test_valid_bearer_preserves_json_payload_even_for_html_accept(granted_roles,priest_request,people,client):
    from tribunal.services.reports import send_request
    app,row=priest_request
    token=send_request(people['admin'],row.pk,'Synthetic Priest')
    with granted_roles('ctm_app',session=True):
        response=client.get(f'/external/reports/{row.pk}/',HTTP_ACCEPT='text/html',HTTP_AUTHORIZATION=f'Bearer {token}')
    assert response.status_code==200
    assert response.json()['id']==str(row.pk)
    assert response.json()['title']==row.title
    assert token not in response.content.decode()
    assert 'Location' not in response
