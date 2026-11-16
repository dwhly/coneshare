from django import template

from dealroom_sign.tenant_brand import TenantBrand, get_tenant_brand

register = template.Library()


@register.simple_tag(takes_context=True)
def tenant_brand(context):
    return TenantBrand() if context.get('staff_shell') else get_tenant_brand()


@register.simple_tag(takes_context=True)
def tenant_product(context):
    state = context.get('state')
    access = context.get('access')
    if state and not (state == 'signed' and access and access.workflow.state == 'done'):
        return 'Sign'
    return 'Dealroom'
