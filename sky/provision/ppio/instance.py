"""PPIO instance provisioning stub."""

import logging
from typing import Any, Dict, Optional, Tuple, TYPE_CHECKING

from sky.provision import common

if TYPE_CHECKING:
    from sky.utils import status_lib

logger = logging.getLogger(__name__)


def run_instances(region: str, cluster_name: str, cluster_name_on_cloud: str,
                  config: common.ProvisionConfig) -> common.ProvisionRecord:
    raise NotImplementedError(
        'PPIO provisioning is not implemented yet. Please use another cloud.')


def wait_instances(region: str, cluster_name: str, cluster_name_on_cloud: str,
                   config: common.ProvisionConfig,
                   record: common.ProvisionRecord) -> None:
    del region, cluster_name, cluster_name_on_cloud, config, record
    raise NotImplementedError('PPIO wait not implemented.')


def stop_instances(region: str, cluster_name: str, cluster_name_on_cloud: str,
                   config: common.ProvisionConfig,
                   record: common.ProvisionRecord) -> common.ProvisionRecord:
    del region, cluster_name, cluster_name_on_cloud, config, record
    raise NotImplementedError('PPIO stop not implemented.')


def terminate_instances(region: str, cluster_name: str,
                        cluster_name_on_cloud: str,
                        config: common.ProvisionConfig,
                        record: common.ProvisionRecord) -> None:
    del region, cluster_name, cluster_name_on_cloud, config, record
    raise NotImplementedError('PPIO terminate not implemented.')


def query_instances(
    region: str,
    cluster_name: str,
    cluster_name_on_cloud: str,
    provider_config: Optional[Dict[str, Any]] = None,
    non_terminated_only: bool = True,
    retry_if_missing: bool = False,
) -> Dict[str, Tuple[Optional['status_lib.ClusterStatus'], Optional[str]]]:
    del region, cluster_name, cluster_name_on_cloud
    del provider_config, non_terminated_only, retry_if_missing
    # Returning empty dict indicates no instances found.
    return {}


def get_cluster_info(provider_name: str, cluster_name_on_cloud: str,
                     region: str,
                     record: common.ProvisionRecord) -> common.ClusterInfo:
    raise NotImplementedError('PPIO get_cluster_info not implemented.')


def open_ports(region: str, cluster_name: str, cluster_name_on_cloud: str,
               config: common.ProvisionConfig,
               record: common.ProvisionRecord) -> None:
    del region, cluster_name, cluster_name_on_cloud, config, record
    logger.warning('PPIO open_ports is not implemented; skipping.')


def cleanup_ports(region: str, cluster_name: str, cluster_name_on_cloud: str,
                  config: common.ProvisionConfig,
                  record: common.ProvisionRecord) -> None:
    del region, cluster_name, cluster_name_on_cloud, config, record
    logger.warning('PPIO cleanup_ports is not implemented; skipping.')
