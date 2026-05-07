# Terraform providers

Provider-specific Terraform stacks live under this directory so additional clouds can be added without mixing provider resources.

- `azure/` — Azure Canada Central foundation for this project.

## Azure usage

```bash
cd infra/terraform/azure
cp terraform.tfvars.example terraform.tfvars
export TF_VAR_postgres_administrator_password='use-a-secure-value'
terraform init -backend=false
terraform validate
terraform plan -var-file=terraform.tfvars
```
