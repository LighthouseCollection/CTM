"""Administrative status projections and frozen applicant notice configuration."""
from django.core.exceptions import ValidationError
from django.db.models import Count, OuterRef, Subquery, IntegerField, Value
from django.db.models.functions import Coalesce
from tribunal.models import Account, AuditEvent, SettingRevision, Notification, Outbox
from tribunal.policy import administrator
from tribunal.validation import validate_json_value
from .common import lock_key

STATUS_ACTIONS = ('account_suspended', 'account_reactivated')


def status_events(account_id):
    return AuditEvent.objects.filter(source='tribunal.account',source_id=account_id,action__in=STATUS_ACTIONS)


def status_version(account_id):
    return status_events(account_id).count()


def account_queryset():
    counts=status_events(OuterRef('pk')).order_by().values('source_id').annotate(n=Count('pk')).values('n')
    return Account.objects.annotate(_status_version=Coalesce(Subquery(counts,output_field=IntegerField()),Value(0)))


def account_data(actor, account, *, active_admin_count=None):
    administrator(actor)
    if active_admin_count is None:
        active_admin_count=Account.objects.filter(role='admin',is_active=True).count()
    last_admin=account.role=='admin' and account.is_active and active_admin_count<=1
    version=getattr(account,'_status_version',None)
    if version is None:
        version=status_version(account.pk)
    return {'id':str(account.pk),'name':f'{account.first_name} {account.last_name}'.strip(),
        'email':account.email,'role':account.role,'active':account.is_active,
        'email_verified':account.email_verified,'ui_language':account.ui_language,
        'notification_language':account.notification_language,
        'created_at':account.created_at.isoformat(),
        'status_version':version,
        'can_suspend':account.is_active and account.pk!=actor.pk and not last_admin,
        'can_reactivate':not account.is_active,
        'status_history_url':f'/api/system/accounts/{account.pk}/status-history/'}


def notice_template(account, action):
    from .configuration import safe_configuration
    from .setting_schemas import validate_setting_value
    lock_key('setting:email_templates')
    latest=SettingRevision.objects.filter(key='email_templates').order_by('-number').first()
    if latest is None:
        raise ValidationError('Configure the approved account-status email template before changing an applicant status.')
    validate_json_value(latest.value,maximum=100_000)
    safe_configuration(latest.value)
    validate_setting_value('email_templates',latest.value)
    language=account.notification_language
    if language not in {'en','ar'}:
        raise ValidationError('Applicant notification language requires review.')
    template=next((row for row in latest.value['templates'] if row['code']==action),None)
    if template is None:
        raise ValidationError('Configure the approved account-status email template before changing an applicant status.')
    return {'language':language,'template_version':latest.number,
            'subject':template[f'subject_{language}'],'body':template[f'body_{language}']}


def queue_status_notice(account, event, template):
    payload={**template,'account_event':str(event.pk)}
    key=f'{event.action}:{event.pk}:{account.pk}'
    Notification.objects.bulk_create([Notification(recipient=account,key=key,kind=event.action,payload=payload)],ignore_conflicts=True)
    Outbox.objects.get_or_create(key=key,defaults={'recipient':account,'queued_by':event.actor,'kind':event.action,'payload':payload})


def sqlite_status_destination(event):
    """Owner-mode fallback; PostgreSQL uses the narrowly scoped definer helper."""
    from .configuration import safe_configuration
    from .setting_schemas import validate_setting_value
    try:
        source=status_events(event.recipient_id).get(pk=event.payload['account_event'])
        account=Account.objects.get(pk=event.recipient_id,role='applicant')
        template=SettingRevision.objects.get(key='email_templates',number=event.payload['template_version'])
        validate_json_value(template.value,maximum=100_000)
        safe_configuration(template.value)
        validate_setting_value('email_templates',template.value)
        language=event.payload['language']
        row=next(item for item in template.value['templates'] if item['code']==event.kind)
        expected={'account_event':str(source.pk),'language':language,'template_version':template.number,
                  'subject':row[f'subject_{language}'],'body':row[f'body_{language}']}
        if (source.action!=event.kind or source.case_id or event.case_id
                or source.metadata.get('status_version')!=status_version(account.pk)
                or source.metadata.get('before')==source.metadata.get('after')
                or source.metadata.get('after') is not account.is_active
                or account.is_active!=(event.kind=='account_reactivated')
                or source.metadata.get('notification_language')!=language
                or source.metadata.get('template_version')!=template.number
                or source.actor_id!=event.queued_by_id or event.payload!=expected
                or event.key!=f'{event.kind}:{source.pk}:{account.pk}'):
            return None
    except (Account.DoesNotExist,AuditEvent.DoesNotExist,SettingRevision.DoesNotExist,KeyError,ValueError,TypeError,StopIteration,ValidationError):
        return None
    return {'email':account.email,'is_active':account.is_active,'email_verified':account.email_verified,
            'role':account.role,'status_notice':True,'subject':expected['subject'],'body':expected['body']}
