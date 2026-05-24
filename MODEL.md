# Breathe ESG — Data Model

## Design Principles

1. **Traceability**: Every computed emission record traces back to a specific row in a specific uploaded file via `RawRecord → EmissionRecord` (OneToOne).
2. **Shared-database multi-tenancy**: A single database with `tenant_id` foreign keys. Chosen over schema-per-tenant because this is a prototype with < 10 tenants. Tradeoff: requires disciplined queryset filtering.
3. **Append-only audit**: The `AuditLog` table is append-only. Records are never deleted or modified. This satisfies GHG Protocol verification requirements.

## Entity Relationship

```
Tenant (1) ──→ (N) User
Tenant (1) ──→ (N) DataIngestion
DataIngestion (1) ──→ (N) RawRecord
RawRecord (1) ──→ (1) EmissionRecord
EmissionRecord (N) ──→ (1) EmissionFactor
EmissionRecord (1) ──→ (N) AuditLog
Tenant (1) ──→ (N) PlantCodeLookup
AirportLookup (global reference)
```

## Tables

### `core.Tenant`
Multi-tenant isolation. Each client organization is a tenant.
- `id` UUID PK
- `name` VARCHAR(255)
- `slug` VARCHAR(100) UNIQUE — used in URLs

### `core.User`
Custom user model extending AbstractUser.
- `tenant` FK → Tenant (nullable for superadmins)
- `role` ENUM(admin, analyst, viewer) — RBAC

### `ingestion.DataIngestion`
Tracks each file upload event.
- `source_type` ENUM(sap_fuel, utility_electricity, travel)
- `file_name`, `file_hash` SHA-256 — dedup check
- `status` ENUM(pending, processing, completed, completed_with_errors, failed)
- `row_count`, `success_count`, `error_count` — processing summary
- `processing_log` JSON — structured errors per row

### `ingestion.RawRecord`
Immutable storage of every CSV row exactly as received.
- `ingestion` FK → DataIngestion
- `row_number` INT — position in source file
- `raw_data` JSON — the exact key-value pairs from the CSV
- `parse_status` ENUM(pending, parsed, failed, skipped)
- `parse_errors` JSON — what went wrong if parsing failed

Design decision: storing raw data as JSON (not re-serialized CSV) preserves the original column names and values without delimiter ambiguity.

### `emissions.EmissionRecord`
The normalized, computation-ready record.
- `raw_record` OneToOne → RawRecord — full traceability
- `scope` ENUM(scope_1, scope_2, scope_3)
- `scope_category` VARCHAR — sub-category (stationary_combustion, purchased_electricity, business_travel_cat6)
- `activity_type` VARCHAR — maps to emission factor (diesel, grid_electricity, flight_long_haul_economy)
- `quantity` DECIMAL — normalized value (e.g., liters after unit conversion)
- `unit` VARCHAR — canonical unit matching the emission factor
- `original_quantity`, `original_unit` — before normalization, for auditor review
- `co2e_kg` DECIMAL — computed CO₂ equivalent
- `emission_factor` FK → EmissionFactor
- `review_status` ENUM(pending, approved, rejected, flagged)
- `flags` JSON — anomalies detected during parsing
- `is_locked` BOOLEAN — once locked, record is immutable for audit

### `emissions.EmissionFactor`
Versioned reference table for emission conversion factors.
- `source_db` VARCHAR — e.g., DEFRA_2024, EPA_2024, CEA_2024
- `activity_type` VARCHAR — matches EmissionRecord.activity_type
- `co2e_per_unit` DECIMAL — kgCO₂e per unit of activity
- `region` VARCHAR — for location-based factors (grid electricity)
- `valid_from`, `valid_to` — temporal validity

### `review.AuditLog`
Append-only audit trail.
- `emission_record` FK → EmissionRecord
- `action` ENUM(created, updated, approved, rejected, flagged, locked, unlocked)
- `field_changed`, `old_value`, `new_value` — field-level tracking
- `performed_by` FK → User
- `ip_address` — for compliance
- `metadata` JSON — contextual info (ingestion_id, batch info)

### `reference.PlantCodeLookup`
Tenant-specific SAP plant code → facility name mapping.

### `reference.AirportLookup`
Global IATA airport codes with coordinates for Haversine distance calculation.
