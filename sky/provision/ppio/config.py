"""PPIO configuration bootstrapping."""

from sky.provision import common


def bootstrap_instances(
        region: str, cluster_name: str,
        config: common.ProvisionConfig) -> common.ProvisionConfig:
    del region, cluster_name  # unused
    # PPIO currently requires no extra bootstrap resources.
    return config
