# Backup And Restore

GriosAI stores the brain as plain files. The `backup` and `restore` commands
turn that vault into a portable zip archive with a signed-by-hash manifest, then
restore it without allowing path traversal, symlink entries, or accidental
clobbering.

## Create A Backup

```bash
griosai backup --vault ~/GriosAI-vault --output ~/Backups
```

If `--output` is a directory, GriosAI writes a timestamped
`griosai-vault-<timestamp>.zip` inside it. If the exact output file already
exists, the command allocates a unique filename unless `--overwrite` is set.

The archive includes files under the standard vault directories:

- `notes/`
- `dashboards/`
- `images/`
- `inbox/`
- `notebook-packets/`

Symlinks are skipped so a backup cannot silently capture files outside the
selected vault.

## Restore A Backup

```bash
griosai restore ~/Backups/griosai-vault-20260530T120000Z.zip \
  --vault ~/GriosAI-vault-restored
```

Restore fails if a target file already exists. To replace existing files:

```bash
griosai restore ~/Backups/griosai-vault-20260530T120000Z.zip \
  --vault ~/GriosAI-vault-restored \
  --overwrite
```

## Safety Checks

During restore, GriosAI verifies:

- the backup manifest schema
- every file path is relative and inside the expected vault layout
- no zip entry is a symlink
- no unexpected zip entries exist
- every file size matches the manifest
- every file SHA-256 digest matches the manifest
- existing files are not replaced unless `--overwrite` is set

Backups can contain private notes, images, and dashboards. Keep backup archives
out of git, cloud sync folders, and public issue attachments unless they are
explicitly reviewed and sanitized.
