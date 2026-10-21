"""Deterministic demo data (catalogs, data sheets, images, feeds) for the two fictional demo tenants."""

from .generator import TenantDataset, build_tenant, write_all, write_tenant

__all__ = ["TenantDataset", "build_tenant", "write_all", "write_tenant"]
