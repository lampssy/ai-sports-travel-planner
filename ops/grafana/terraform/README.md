# Terraform Migration Notes

Snowcast starts with Python scripts for Grafana dashboard deployment to avoid
introducing Terraform state before it is needed. The directory layout is still
Terraform-friendly.

Future Terraform migration should reuse:

```text
ops/grafana/dashboards/*.dashboard.json
ops/grafana/dashboards.manifest.json
```

Recommended future scope:

- dashboard resources
- folders
- alert rules
- contact points and notification policies
- synthetic checks if Snowcast adds them

State guidance:

- Do not store Terraform state in git.
- Prefer a managed remote backend if Grafana provisioning grows beyond one or
  two dashboards.
- Keep the Grafana service account token in GitHub secrets or a local secret
  manager, not in Terraform files.

Migration target:

- Keep dashboard JSON as the canonical source.
- Have Terraform read the same files instead of embedding dashboard JSON in HCL.
- Preserve stable dashboard names such as `snowcast-production-overview` so
  migration does not create duplicate dashboards.
