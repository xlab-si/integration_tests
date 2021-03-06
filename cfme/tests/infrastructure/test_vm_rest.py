# -*- coding: utf-8 -*-
from random import choice

import fauxfactory
import pytest
from manageiq_client.filters import Q

from cfme import test_requirements
from cfme.infrastructure.provider import InfraProvider
from cfme.markers.env_markers.provider import ONE
from cfme.rest.gen_data import vm as _vm
from cfme.utils.rest import assert_response
from cfme.utils.rest import delete_resources_from_collection
from cfme.utils.rest import delete_resources_from_detail
from cfme.utils.rest import query_resource_attributes
from cfme.utils.wait import wait_for
from cfme.utils.wait import wait_for_decorator

pytestmark = [
    test_requirements.rest,
    pytest.mark.provider(classes=[InfraProvider], selector=ONE),
    pytest.mark.usefixtures('setup_provider')
]


@pytest.fixture(scope='function')
def vm(request, provider, appliance):
    vm_name = _vm(request, provider, appliance)
    return appliance.rest_api.collections.vms.get(name=vm_name)


@pytest.mark.tier(3)
def test_query_vm_attributes(vm, soft_assert):
    """Tests access to VM attributes using /api/vms.

    Metadata:
        test_flag: rest

    Polarion:
        assignee: pvala
        casecomponent: Infra
        caseimportance: high
        initialEstimate: 1/4h
    """
    outcome = query_resource_attributes(vm)
    for failure in outcome.failed:
        # BZ 1546995
        soft_assert(False, '{0} "{1}": status: {2}, error: `{3}`'.format(
            failure.type, failure.name, failure.response.status_code, failure.error))


@pytest.mark.tier(2)
@pytest.mark.parametrize('from_detail', [True, False], ids=['from_detail', 'from_collection'])
def test_vm_scan(appliance, vm, from_detail):
    """Tests running VM scan using REST API.

    Metadata:
        test_flag: rest

    Polarion:
        assignee: pvala
        casecomponent: Infra
        caseimportance: high
        initialEstimate: 1/3h
    """
    if from_detail:
        response = vm.action.scan()
    else:
        response, = appliance.rest_api.collections.vms.action.scan(vm)
    assert_response(appliance)

    @wait_for_decorator(timeout='5m', delay=5, message='REST running VM scan finishes')
    def _finished():
        response.task.reload()
        if 'error' in response.task.status.lower():
            pytest.fail('Error when running scan vm method: `{}`'.format(response.task.message))
        return response.task.state.lower() == 'finished'


@pytest.mark.tier(3)
@pytest.mark.parametrize(
    'from_detail', [True, False],
    ids=['from_detail', 'from_collection'])
def test_edit_vm(request, vm, appliance, from_detail):
    """Tests edit VMs using REST API.

    Testing BZ 1428250.

    Metadata:
        test_flag: rest

    Polarion:
        assignee: pvala
        casecomponent: Infra
        caseimportance: high
        initialEstimate: 1/4h
    """
    request.addfinalizer(vm.action.delete)
    new_description = 'Test REST VM {}'.format(fauxfactory.gen_alphanumeric(5))
    payload = {'description': new_description}
    if from_detail:
        edited = vm.action.edit(**payload)
        assert_response(appliance)
    else:
        payload.update(vm._ref_repr())
        edited = appliance.rest_api.collections.vms.action.edit(payload)
        assert_response(appliance)
        edited = edited[0]

    record, __ = wait_for(
        lambda: appliance.rest_api.collections.vms.find_by(
            description=new_description) or False,
        num_sec=100,
        delay=5,
    )
    vm.reload()
    assert vm.description == edited.description == record[0].description


@pytest.mark.tier(3)
@pytest.mark.parametrize('method', ['post', 'delete'], ids=['POST', 'DELETE'])
def test_delete_vm_from_detail(vm, method):
    """
    Polarion:
        assignee: pvala
        initialEstimate: 1/4h
        casecomponent: Infra
    """
    delete_resources_from_detail([vm], method=method, num_sec=300, delay=10)


@pytest.mark.tier(3)
def test_delete_vm_from_collection(vm):
    """
    Polarion:
        assignee: pvala
        initialEstimate: 1/4h
        casecomponent: Infra
    """
    delete_resources_from_collection([vm], not_found=True, num_sec=300, delay=10)


@pytest.mark.tier(1)
@pytest.mark.ignore_stream("5.10")
@pytest.mark.meta(automates=[1684681])
@pytest.mark.provider(
    classes=[InfraProvider],
    selector=ONE,
    override=True,
    required_fields=[["cap_and_util", "capandu_vm"]],
)
def test_filtering_vm_with_multiple_ips(appliance, provider):
    """
    Polarion:
        assignee: pvala
        caseimportance: high
        casecomponent: Rest
        initialEstimate: 1/4h
        setup:
            1. Add a provider.
        testSteps:
            1. Select a VM with multiple IP addresses and note one ipaddress.
            2. Send a GET request with the noted ipaddress.
                GET /api/vms?expand=resources&attributes=ipaddresses&filter[]=ipaddresses=':ipaddr'
        expectedResults:
            1.
            2. Selected VM must be present in the resources sent by response.

    Bugzilla:
        1684681
    """
    # 1
    vm = appliance.collections.infra_vms.instantiate(
        provider.data["cap_and_util"]["capandu_vm"], provider
    )
    # 2
    result = appliance.rest_api.collections.vms.filter(
        Q("ipaddresses", "=", choice(vm.all_ip_addresses))
    )
    assert_response(appliance)
    assert vm.name in [resource.name for resource in result.resources]
