## Summary

-

## Privacy / Safety Boundary

- What data is read or written?
- Does anything leave the local vault or localhost?
- Are any optional adapters, network exposure, or raw-content exports involved?

## Validation

- [ ] `./scripts/validate.sh`
- [ ] Focused tests added or updated for behavior changes.
- [ ] Docs updated for any command, config, API, adapter, or operator-risk change.

## Safety

- [ ] No real credentials, vault contents, private screenshots, raw logs, or `.env` files are included.
- [ ] New network exposure remains localhost/private by default or is explicitly justified.
- [ ] New exports/adapters document what data leaves the local vault.
- [ ] New filesystem writes have path-safety and non-clobbering coverage.
- [ ] Public exposure, cloud usage, or raw-content tracking received explicit review.
