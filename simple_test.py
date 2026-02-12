#!/usr/bin/env python3
"""Simple NetSuite API test."""

from netsuite_shim import NetSuiteClient, NetSuiteConfig

# Load config from .env
config = NetSuiteConfig(timeout=60.0)
print(f"Account ID: {config.account_id}")
print(f"Base URL: {config.computed_base_url}")
print(f"Using TBA auth: {config.tba is not None}")
print()

# Create client and make a request
with NetSuiteClient(config) as client:
    try:
        # Try metadata catalog
        result = client.metadata.list_record_types()
        items = result.get('items', [])
        print(f"Metadata catalog has {len(items)} record types")
        print("\nFirst 10 record types:")
        for item in items[:10]:
            print(f"  - {item.get('name')}: {item.get('label')}")
    except Exception as e:
        print(f"Error: {e}")
        if hasattr(e, 'error_details'):
            print(f"Details: {e.error_details}")
