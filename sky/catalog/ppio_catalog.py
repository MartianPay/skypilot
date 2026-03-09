"""PPIO | Catalog

This module loads pricing and instance information for PPIO.
It mirrors the minimal catalog interface expected by sky.catalog.*
helpers. For now it reads a static CSV from ~/.sky/catalogs if present,
falling back to an empty DataFrame so core logic continues to work even
when pricing is unavailable.
"""

import typing
from typing import Dict, List, Optional, Tuple, Union

from sky.adaptors import common as adaptors_common
from sky.catalog import common

if typing.TYPE_CHECKING:
    import pandas as pd

    from sky.clouds import cloud
else:
    pd = adaptors_common.LazyImport('pandas')

_df = None


def _get_df():
    """Lazily load catalog data."""
    global _df
    if _df is None:
        try:
            df = common.read_catalog('ppio/vms.csv')
        except FileNotFoundError:
            _df = pd.DataFrame(columns=[
                'InstanceType', 'AcceleratorName', 'AcceleratorCount', 'vCPUs',
                'MemoryGiB', 'Price', 'Region', 'GpuInfo', 'SpotPrice'
            ])
        else:
            df = df[df['InstanceType'].notna()]
            if 'AcceleratorName' in df.columns:
                df = df[df['AcceleratorName'].notna()]
                df = df.assign(AcceleratorName=df['AcceleratorName'].astype(
                    str).str.strip())
            _df = df.reset_index(drop=True)
    return _df


def _call_or_default(func, default):
    try:
        return func()
    except ValueError:
        return default


def instance_type_exists(instance_type: str) -> bool:
    df = _get_df()
    if df.empty:
        return True
    return common.instance_type_exists_impl(df, instance_type)


def validate_region_zone(
        region: Optional[str],
        zone: Optional[str]) -> Tuple[Optional[str], Optional[str]]:
    df = _get_df()
    if df.empty:
        return region, zone
    return common.validate_region_zone_impl('ppio', df, region, zone)


def get_hourly_cost(instance_type: str,
                    use_spot: bool = False,
                    region: Optional[str] = None,
                    zone: Optional[str] = None) -> float:
    df = _get_df()
    if df.empty:
        return 0.0
    return common.get_hourly_cost_impl(df, instance_type, use_spot, region,
                                       zone)


def get_vcpus_mem_from_instance_type(
        instance_type: str) -> Tuple[Optional[float], Optional[float]]:
    return _call_or_default(
        lambda: common.get_vcpus_mem_from_instance_type_impl(
            _get_df(), instance_type), (None, None))


def get_default_instance_type(cpus: Optional[str] = None,
                              memory: Optional[str] = None,
                              disk_tier: Optional[str] = None,
                              local_disk: Optional[str] = None,
                              region: Optional[str] = None,
                              zone: Optional[str] = None) -> Optional[str]:
    del disk_tier, local_disk
    return _call_or_default(
        lambda: common.get_instance_type_for_cpus_mem_impl(
            _get_df(), cpus, memory, region, zone), None)


def get_accelerators_from_instance_type(
        instance_type: str) -> Optional[Dict[str, Union[int, float]]]:
    return _call_or_default(
        lambda: common.get_accelerators_from_instance_type_impl(
            _get_df(), instance_type), None)


def get_instance_type_for_accelerator(
        acc_name: str,
        acc_count: int,
        cpus: Optional[str] = None,
        memory: Optional[str] = None,
        use_spot: bool = False,
        local_disk: Optional[str] = None,
        region: Optional[str] = None,
        zone: Optional[str] = None) -> Tuple[Optional[List[str]], List[str]]:
    del local_disk, use_spot  # Spot support TBD; treat as on-demand only.
    return _call_or_default(
        lambda: common.get_instance_type_for_accelerator_impl(
            df=_get_df(),
            acc_name=acc_name,
            acc_count=acc_count,
            cpus=cpus,
            memory=memory,
            use_spot=False,
            region=region,
            zone=zone), (None, []))


def get_region_zones_for_instance_type(instance_type: str,
                                       use_spot: bool) -> List['cloud.Region']:
    del use_spot  # PPIO spot mapping handled via billing method flag
    df = _get_df()
    if df.empty:
        return []
    df_filtered = df[df['InstanceType'] == instance_type]
    regions = _call_or_default(
        lambda: common.get_region_zones(df_filtered, False), [])
    if not regions:
        # Provide a permissive default if catalog is missing entry.
        regions = []
    return regions


def list_accelerators(
        gpus_only: bool,
        name_filter: Optional[str],
        region_filter: Optional[str],
        quantity_filter: Optional[int],
        case_sensitive: bool = True,
        all_regions: bool = False,
        require_price: bool = True) -> Dict[str, List[common.InstanceTypeInfo]]:
    del require_price  # Prices may be missing; still list shapes
    return common.list_accelerators_impl('PPIO', _get_df(), gpus_only,
                                         name_filter, region_filter,
                                         quantity_filter, case_sensitive,
                                         all_regions)
