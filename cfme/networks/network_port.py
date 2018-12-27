import attr
from navmazing import NavigateToAttribute

from cfme.common import Taggable
from cfme.exceptions import ItemNotFound
from cfme.modeling.base import BaseCollection, BaseEntity, parent_of_type
from cfme.networks import ValidateStatsMixin
from cfme.networks.views import NetworkPortDetailsView, NetworkPortView
from cfme.utils import version
from cfme.utils.appliance.implementations.ui import navigator, CFMENavigateStep, navigate_to


@attr.s
class NetworkPort(Taggable, BaseEntity, ValidateStatsMixin):
    """Class representing network ports in sdn"""
    in_version = ('5.8', version.LATEST)
    category = "networks"
    string_name = 'NetworkPort'
    quad_name = None
    db_types = ['CloudNetworkPort']

    name = attr.ib()

    @property
    def mac_address(self):
        """ Returns mac adress (string) of the port """
        view = navigate_to(self, 'Details')
        return view.entities.properties.get_text_of('Mac address')

    @property
    def network_type(self):
        view = navigate_to(self, 'Details')
        return view.entities.properties.get_text_of('Type')

    @property
    def floating_ips(self):
        """ Returns floating ips (string) of the port """
        view = navigate_to(self, 'Details')
        return view.entities.properties.get_text_of('Floating ip addresses')

    @property
    def fixed_ips(self):
        """ Returns fixed ips (string) of the port """
        view = navigate_to(self, 'Details')
        return view.entities.properties.get_text_of('Fixed ip addresses')

    @property
    def provider(self):
        from cfme.networks.provider import NetworkProvider
        return parent_of_type(self, NetworkProvider)

    @property
    def network_provider(self):
        """ Returns network provider """
        # port collection contains reference to provider
        if self.provider:
            return self.provider
        # otherwise get provider name from ui
        view = navigate_to(self, 'Details')
        try:
            prov_name = view.entities.relationships.get_text_of("Network Manager")
            collection = self.appliance.collections.network_provider
            return collection.instantiate(name=prov_name)
        except ItemNotFound:  # BZ 1480577
            return None


@attr.s
class NetworkPortCollection(BaseCollection):
    """ Collection object for NetworkPort object
        Note: Network providers object are not implemented in mgmt
    """

    ENTITY = NetworkPort

    def all(self):
        if self.filters.get('parent'):
            view = navigate_to(self.filters.get('parent'), 'NetworkPorts')
        else:
            view = navigate_to(self, 'All')
        list_networks_obj = view.entities.get_all(surf_pages=True)
        return [self.instantiate(name=p.name) for p in list_networks_obj]


@navigator.register(NetworkPortCollection, 'All')
class All(CFMENavigateStep):
    VIEW = NetworkPortView
    prerequisite = NavigateToAttribute('appliance.server', 'LoggedIn')

    def step(self):
        self.prerequisite_view.navigation.select('Networks', 'Network Ports')

    def resetter(self):
        """Reset the view"""
        self.view.browser.refresh()


@navigator.register(NetworkPort, 'Details')
class Details(CFMENavigateStep):
    VIEW = NetworkPortDetailsView

    def prerequisite(self, *args, **kwargs):
        """Navigate through filter parent if it exists else navigate through parent object"""
        is_filtered = isinstance(self.obj.parent, BaseCollection) and self.obj.parent.filters
        filter = (self.obj.parent.filters.get('parent') if is_filtered else None)
        if is_filtered:
            return navigate_to(filter, 'NetworkPorts')
        else:
            return navigate_to(self.obj.parent, 'All')

    def step(self):
        self.prerequisite_view.entities.get_entity(name=self.obj.name, surf_pages=True).click()
