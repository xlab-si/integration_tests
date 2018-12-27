import pytest

from cfme.utils.log import logger
from cfme.utils.wait import wait_for
from wrapanapi.utils.random import random_name
from cfme.networks.provider.nuage import NuageProvider

pytestmark = [
    pytest.mark.provider([NuageProvider])
]


def test_router_add_subnet(provider, with_nuage_sandbox):
    """
    Ensure that subnet is added on network router

    We navigate to router through Provider > Tenant > Network Router
    """
    sandbox = with_nuage_sandbox
    tenant_name = sandbox['enterprise'].name
    router_name = sandbox['domain'].name
    tenant = provider.collections.cloud_tenants.instantiate(name=tenant_name, provider=provider)
    router = tenant.collections.routers.instantiate(name=router_name)
    subnet_name = random_name()
    router.add_subnet(subnet_name, '100.100.100.0', '255.255.255.0', '100.100.100.1')
    subnet = get_object_from_db_with_timeout(provider.appliance, 'cloud_subnets', subnet_name)

    assert subnet is not None


def get_object_from_db_with_timeout(appliance, table_name, object_name):
    def get_object():
        logger.info('Looking for %s with name %s in the VMDB...', table_name, object_name)
        table = appliance.db.client[table_name]
        return (appliance.db.client.session.query(table.name)
                .filter(table.name == object_name).first())

    obj, _ = wait_for(get_object, num_sec=60, delay=5, fail_condition=None)
    return obj
