# Config Identifiers

When adding, removing, or renaming a configuration field in any feature plugin under `skills/configurator/configurator-cli/src/configurator/features/`:

1. Update the feature's `config_identifiers()` method to reflect the change.
2. Update `skills/configurator/references/config-identifiers.md` to keep the reference table in sync.
3. Run `configurator --schema` to verify the full identifier list is correct.
