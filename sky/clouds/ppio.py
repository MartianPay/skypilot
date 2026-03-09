"""PPIO Cloud implementation."""

import os
import secrets
import typing
from typing import Dict, Iterator, List, Optional, Tuple, Union

from sky import catalog
from sky import clouds
from sky.catalog import ppio_catalog
from sky.utils import registry
from sky.utils import resources_utils

if typing.TYPE_CHECKING:
    from sky import resources as resources_lib
    from sky.utils import volume as volume_lib

_CREDENTIAL_FILE = 'api_key'


@registry.CLOUD_REGISTRY.register
class PPIO(clouds.Cloud):
    """PPIO GPU Cloud.

    PPIO provides GPU container instances that can be controlled via
    the public PPIO OpenAPI.
    """

    _REPR = 'PPIO'

    # yapf: disable
    _CLOUD_UNSUPPORTED_FEATURES = {
        clouds.CloudImplementationFeatures.MULTI_NODE:
            'Multi-node clusters are not yet supported on PPIO.',
        clouds.CloudImplementationFeatures.CUSTOM_DISK_TIER:
            'Custom disk tiers are not supported on PPIO.',
        clouds.CloudImplementationFeatures.CUSTOM_NETWORK_TIER:
            'Custom network tiers are not supported on PPIO.',
        clouds.CloudImplementationFeatures.STORAGE_MOUNTING:
            'Object storage mounting is not supported on PPIO.',
        clouds.CloudImplementationFeatures.HIGH_AVAILABILITY_CONTROLLERS:
            'High availability controllers are not supported.',
        clouds.CloudImplementationFeatures.CUSTOM_MULTI_NETWORK:
            'Custom multiple network interfaces are not supported.',
        clouds.CloudImplementationFeatures.LOCAL_DISK:
            'Local disks are not exposed separately on PPIO.',
    }
    # yapf: enable

    _MAX_CLUSTER_NAME_LEN_LIMIT = 120
    _MAX_VOLUME_NAME_LEN_LIMIT = 30

    _regions: List[clouds.Region] = []

    PROVISIONER_VERSION = clouds.ProvisionerVersion.SKYPILOT
    STATUS_VERSION = clouds.StatusVersion.SKYPILOT
    OPEN_PORTS_VERSION = clouds.OpenPortsVersion.LAUNCH_ONLY

    @classmethod
    def _unsupported_features_for_resources(
        cls,
        resources: 'resources_lib.Resources',
        region: Optional[str] = None,
    ) -> Dict[clouds.CloudImplementationFeatures, str]:
        del resources, region  # unused
        return cls._CLOUD_UNSUPPORTED_FEATURES

    @classmethod
    def _max_cluster_name_length(cls) -> Optional[int]:
        return cls._MAX_CLUSTER_NAME_LEN_LIMIT

    @classmethod
    def regions_with_offering(
        cls,
        instance_type: str,
        accelerators: Optional[Dict[str, int]],
        use_spot: bool,
        region: Optional[str],
        zone: Optional[str],
        resources: Optional['resources_lib.Resources'] = None,
    ) -> List[clouds.Region]:
        del accelerators, resources  # unused
        regions = ppio_catalog.get_region_zones_for_instance_type(
            instance_type, use_spot)

        if region is not None:
            regions = [r for r in regions if r.name == region]

        if zone is not None:
            for r in regions:
                assert r.zones is not None, r
                r.set_zones([z for z in r.zones if z.name == zone])
            regions = [r for r in regions if r.zones]
        return regions

    @classmethod
    def get_vcpus_mem_from_instance_type(
        cls,
        instance_type: str,
    ) -> Tuple[Optional[float], Optional[float]]:
        return catalog.get_vcpus_mem_from_instance_type(instance_type,
                                                        clouds='ppio')

    @classmethod
    def zones_provision_loop(
        cls,
        *,
        region: str,
        num_nodes: int,
        instance_type: str,
        accelerators: Optional[Dict[str, int]] = None,
        use_spot: bool = False,
    ) -> Iterator[Optional[List['clouds.Zone']]]:
        del num_nodes, accelerators  # unused
        regions = cls.regions_with_offering(instance_type,
                                            None,
                                            use_spot,
                                            region=region,
                                            zone=None)
        for r in regions:
            yield r.zones

    def instance_type_to_hourly_cost(self,
                                     instance_type: str,
                                     use_spot: bool,
                                     region: Optional[str] = None,
                                     zone: Optional[str] = None) -> float:
        return catalog.get_hourly_cost(instance_type,
                                       use_spot=use_spot,
                                       region=region,
                                       zone=zone,
                                       clouds='ppio')

    def accelerators_to_hourly_cost(self,
                                    accelerators: Dict[str, int],
                                    use_spot: bool,
                                    region: Optional[str] = None,
                                    zone: Optional[str] = None) -> float:
        del accelerators, use_spot, region, zone
        # Accelerator cost is included in the instance price.
        return 0.0

    def get_egress_cost(self, num_gigabytes: float) -> float:
        del num_gigabytes
        return 0.0

    @classmethod
    def get_default_instance_type(cls,
                                  cpus: Optional[str] = None,
                                  memory: Optional[str] = None,
                                  disk_tier: Optional[
                                      resources_utils.DiskTier] = None,
                                  local_disk: Optional[str] = None,
                                  region: Optional[str] = None,
                                  zone: Optional[str] = None) -> Optional[str]:
        del disk_tier, local_disk
        return catalog.get_default_instance_type(cpus=cpus,
                                                 memory=memory,
                                                 disk_tier=None,
                                                 region=region,
                                                 zone=zone,
                                                 clouds='ppio')

    @classmethod
    def get_accelerators_from_instance_type(
            cls, instance_type: str) -> Optional[Dict[str, Union[int, float]]]:
        return catalog.get_accelerators_from_instance_type(instance_type,
                                                           clouds='ppio')

    @classmethod
    def get_zone_shell_cmd(cls) -> Optional[str]:
        return None

    def make_deploy_resources_variables(
        self,
        resources: 'resources_lib.Resources',
        cluster_name: resources_utils.ClusterName,
        region: 'clouds.Region',
        zones: Optional[List['clouds.Zone']],
        num_nodes: int,
        dryrun: bool = False,
        volume_mounts: Optional[List['volume_lib.VolumeMount']] = None,
    ) -> Dict[str, Optional[Union[str, bool, int]]]:
        del cluster_name, dryrun, volume_mounts  # unused
        assert zones is None or len(zones) <= 1, zones
        resources = resources.assert_launchable()

        instance_type = resources.instance_type
        if instance_type is None:
            raise ValueError('PPIO requires an explicit instance_type')

        docker_image = resources.extract_docker_image()
        image_id = resources.image_id
        if docker_image is not None:
            image_url: Optional[str] = docker_image
        elif image_id is not None:
            image_url = image_id.get(resources.region)
        else:
            raise ValueError('PPIO requires a docker image. Please specify '
                             'Resources(image_id="<docker image>") or use '
                             'a task YAML with docker_image set.')

        # Ports: always ensure SSH is reachable. Convert to comma-separated
        # strings like "22/tcp,8080/tcp" understood by PPIO.
        port_set = {'22/tcp'}
        if resources.ports:
            for port in resources.ports:
                if '/' not in port:
                    port_set.add(f'{port}/tcp')
                else:
                    port_set.add(port)
        ports = ','.join(sorted(port_set))

        billing_method = 'spot' if resources.use_spot else 'onDemand'

        # Generate a deterministic-but-random password to ensure SSH fallback
        # even if the user's account SSH key is not propagated yet.
        ssh_password = secrets.token_urlsafe(12)

        return {
            'instance_type': instance_type,
            'region': region.name,
            'image_url': image_url,
            'ports': ports,
            'use_spot': resources.use_spot,
            'billing_method': billing_method,
            'ssh_password': ssh_password,
            'disk_size': resources.disk_size,  # in GB
            'zone': zones[0].name if zones else None,
            'num_nodes': num_nodes,
        }

    def _get_feasible_launchable_resources(
        self, resources: 'resources_lib.Resources'
    ) -> 'resources_utils.FeasibleResources':
        if resources.instance_type is not None:
            assert resources.is_launchable(), resources
            launchable = resources.copy(accelerators=None)
            return resources_utils.FeasibleResources([launchable], [], None)

        def _make(instance_list):
            resource_list = []
            for instance_type in instance_list:
                r = resources.copy(cloud=PPIO(),
                                   instance_type=instance_type,
                                   accelerators=None,
                                   cpus=None)
                resource_list.append(r)
            return resource_list

        accelerators = resources.accelerators
        if accelerators is None:
            default_instance_type = PPIO.get_default_instance_type(
                cpus=resources.cpus,
                memory=resources.memory,
                disk_tier=resources.disk_tier,
                local_disk=resources.local_disk,
                region=resources.region,
                zone=resources.zone)
            if default_instance_type is None:
                return resources_utils.FeasibleResources([], [], None)
            return resources_utils.FeasibleResources(
                _make([default_instance_type]), [], None)

        assert len(accelerators) == 1, resources
        acc, acc_count = list(accelerators.items())[0]
        (instance_list,
         fuzzy_candidate_list) = catalog.get_instance_type_for_accelerator(
             acc,
             acc_count,
             use_spot=resources.use_spot,
             cpus=resources.cpus,
             local_disk=resources.local_disk,
             region=resources.region,
             zone=resources.zone,
             clouds='ppio')
        if instance_list is None:
            return resources_utils.FeasibleResources([], fuzzy_candidate_list,
                                                     None)
        return resources_utils.FeasibleResources(_make(instance_list),
                                                 fuzzy_candidate_list, None)

    @classmethod
    def _check_compute_credentials(
            cls) -> Tuple[bool, Optional[Union[str, Dict[str, str]]]]:
        return cls._check_credentials()

    @classmethod
    def _check_credentials(cls) -> Tuple[bool, Optional[str]]:
        key_path = os.path.expanduser(f'~/.ppio/{_CREDENTIAL_FILE}')
        if not os.path.exists(key_path):
            hint = (
                'PPIO API key not found. Create ~/.ppio/api_key containing '
                'your PPIO API key. See https://platform.ppinfra.com/settings '
                'for key management.')
            return False, hint
        return True, None

    def get_credential_file_mounts(self) -> Dict[str, str]:
        return {f'~/.ppio/{_CREDENTIAL_FILE}': f'~/.ppio/{_CREDENTIAL_FILE}'}

    @classmethod
    def get_user_identities(cls) -> Optional[List[List[str]]]:
        return None

    def instance_type_exists(self, instance_type: str) -> bool:
        return catalog.instance_type_exists(instance_type, 'ppio')

    def validate_region_zone(self, region: Optional[str], zone: Optional[str]):
        return catalog.validate_region_zone(region, zone, clouds='ppio')

    @classmethod
    def get_image_size(cls, image_id: str, region: Optional[str]) -> float:
        del image_id, region
        # Image size is not known; allow deployment to continue.
        return 0.0

    @classmethod
    def is_volume_name_valid(cls,
                             volume_name: str) -> Tuple[bool, Optional[str]]:
        if len(volume_name) > cls._MAX_VOLUME_NAME_LEN_LIMIT:
            return (False, f'Volume name exceeds the maximum length of '
                    f'{cls._MAX_VOLUME_NAME_LEN_LIMIT} characters.')
        return True, None
