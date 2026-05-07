# Terraform foundation (Azure Canada Central)

This directory provides a Phase-1 Terraform skeleton for the Brightspace AI integration.

## Included modules

- `modules/resource_group`: resource group in `canadacentral` by default.
- `modules/container_apps`: Azure Container Apps environment + placeholder app endpoint.
- `modules/postgres`: PostgreSQL Flexible Server (private by default; public access disabled).
- `modules/redis`: Azure Cache for Redis.
- `modules/key_vault`: Key Vault for secrets.
- `modules/log_analytics`: Log Analytics workspace.
- `modules/identities`: User-assigned managed identities.

## Remote state (Azure Storage)

Remote-state scaffold is provided via `backend.hcl.example`.

1. Copy `backend.hcl.example` to `backend.hcl` and fill actual values.
2. Initialize with:

```bash
terraform init -backend-config=backend.hcl
```

If you only need local validation, run:

```bash
terraform init -backend=false
```

## Usage

```bash
cp terraform.tfvars.example terraform.tfvars
export TF_VAR_postgres_administrator_password='use-a-secure-value'
terraform init -backend=false
terraform validate
terraform plan -var-file=terraform.tfvars
```

## pgvector enablement path

Azure PostgreSQL Flexible Server does not expose a Terraform-native pgvector toggle.
After server provisioning, connect as an admin and run:

```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

The output `pgvector_enablement_sql` contains this command for deployment runbooks.

## Required outputs

- `app_endpoint`
- `database_host`
- `redis_host`
- `key_vault_name`
- `managed_identity_ids`
