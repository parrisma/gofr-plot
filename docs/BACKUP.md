# gofr-plot Backup System

Automated, zero-downtime backup solution for gofr-plot services running as a sidecar container.

## Overview

The backup system provides:
- ✅ **Zero Downtime** - Backups run without stopping services
- ✅ **Automated Scheduling** - Configurable cron-based scheduling
- ✅ **Retention Policies** - Age and count-based cleanup
- ✅ **Verification** - Automatic integrity checking
- ✅ **Compression** - Configurable compression (gzip/bzip2/xz)
- ✅ **Tiered Storage** - Daily/weekly/monthly retention tiers
- ✅ **100% Configurable** - All settings via environment variables

## Architecture

### Components

1. **Backup Sidecar Container** - Runs alongside main services
2. **Docker Volumes**:
   - `gofr-plot_data` - Main application data (read-only mount)
   - `gofr-plot_backups` - Backup storage (read-write mount)
3. **Backup Service** - Python-based scheduler and orchestrator
4. **Shell Scripts** - Manual backup, restore, and list operations

### What Gets Backed Up

- **Storage** (`/data/storage/`) - Generated charts, images, metadata, blobs
- **Auth** (`/data/auth/`) - Token stores, credentials
- **Logs** (`/logs/`) - Application logs, session data
- **Metadata** - Storage metadata files

All components are individually configurable.

## Quick Start

### 1. Build Backup Image

```bash
cd /home/parris3142/devroot/gofr-plot/docker
docker build -f Dockerfile.backup -t gofr-plot_backup:latest ..
```

### 2. Start Backup Service

```bash
# Start with default configuration (daily at 2 AM)
docker-compose up -d backup

# View logs
docker-compose logs -f backup
```

### 3. Verify Backup Service

```bash
# Check service status
docker-compose ps backup

# View current backup statistics
./scripts/list_backups.sh
```

## Configuration

All settings are configured via environment variables in `docker-compose.yml` or a `.env` file.

### Scheduling

```bash
# Enable/disable backups
GOFR_PLOT_BACKUP_ENABLED=true

# Backup schedule (cron format: minute hour day month weekday)
GOFR_PLOT_BACKUP_SCHEDULE="0 2 * * *"  # Daily at 2 AM
```

**Common Schedules:**
- Daily at 2 AM: `0 2 * * *`
- Every 6 hours: `0 */6 * * *`
- Weekly on Sunday at 3 AM: `0 3 * * 0`
- Twice daily (2 AM and 2 PM): `0 2,14 * * *`

### Retention Policies

```bash
# Keep backups for 30 days
GOFR_PLOT_BACKUP_RETENTION_DAYS=30

# Keep maximum of 90 backups
GOFR_PLOT_BACKUP_MAX_COUNT=90
```

### What to Backup

```bash
GOFR_PLOT_BACKUP_INCLUDE_STORAGE=true
GOFR_PLOT_BACKUP_INCLUDE_AUTH=true
GOFR_PLOT_BACKUP_INCLUDE_LOGS=true
GOFR_PLOT_BACKUP_INCLUDE_METADATA=true
```

### Compression

```bash
# Compression algorithm: gzip, bzip2, xz, or none
GOFR_PLOT_BACKUP_COMPRESSION=gzip

# Compression level (1-9, higher = better compression but slower)
GOFR_PLOT_BACKUP_COMPRESSION_LEVEL=6
```

**Compression Comparison:**
- `gzip` - Fast, good compression, widely compatible (recommended)
- `bzip2` - Slower, better compression
- `xz` - Slowest, best compression
- `none` - No compression, fastest

### Housekeeping

```bash
# Run cleanup on service startup
GOFR_PLOT_BACKUP_CLEANUP_ON_START=true

# Verify backups after creation
GOFR_PLOT_BACKUP_VERIFY_AFTER_BACKUP=true
```

### Tiered Retention (Optional)

```bash
# Enable weekly backups (keep one per week)
GOFR_PLOT_BACKUP_ENABLE_WEEKLY=true
GOFR_PLOT_BACKUP_WEEKLY_RETENTION_WEEKS=8

# Enable monthly backups (keep one per month)
GOFR_PLOT_BACKUP_ENABLE_MONTHLY=true
GOFR_PLOT_BACKUP_MONTHLY_RETENTION_MONTHS=12
```

## Usage

### Manual Backup

Create an immediate backup:

```bash
cd /home/parris3142/devroot/gofr-plot
./scripts/backup_now.sh
```

### List Backups

View all available backups:

```bash
./scripts/list_backups.sh
```

Output example:
```
DAILY BACKUPS (5):
--------------------------------------------------------------------------------
  gofr-plot_daily_20251213_020000.tar.gz
    Size: 15.32 MB | Age: 0 days | Verified: ✓
    Created: 2025-12-13 02:00:00

  gofr-plot_daily_20251212_020000.tar.gz
    Size: 14.87 MB | Age: 1 days | Verified: ✓
    Created: 2025-12-12 02:00:00

SUMMARY:
--------------------------------------------------------------------------------
Total Backups: 5
Total Size: 73.45 MB
Oldest: 2025-12-09T02:00:00
Newest: 2025-12-13T02:00:00
```

### Restore from Backup

Restore data from a backup:

```bash
# Interactive mode (select from list)
./scripts/restore_backup.sh --interactive

# Restore specific backup
./scripts/restore_backup.sh gofr-plot_daily_20251213_020000.tar.gz

# Restore latest backup
./scripts/restore_backup.sh --latest
```

**Important:** The restore script will:
1. Verify backup integrity before restoring
2. Prompt for confirmation
3. Overwrite current data with backup contents
4. Recommend stopping services before restore

### Recommended Restore Workflow

```bash
# 1. Stop services
docker-compose stop mcp mcpo web

# 2. Create safety backup of current state (optional)
./scripts/backup_now.sh

# 3. Restore from backup
./scripts/restore_backup.sh --interactive

# 4. Restart services
docker-compose restart mcp mcpo web

# 5. Verify functionality
curl http://localhost:8012/health
```

## Backup File Structure

```
/backups/
├── daily/
│   ├── gofr-plot_daily_20251213_020000.tar.gz
│   ├── gofr-plot_daily_20251213_020000.tar.gz.sha256
│   ├── gofr-plot_daily_20251212_020000.tar.gz
│   └── gofr-plot_daily_20251212_020000.tar.gz.sha256
├── weekly/
│   └── gofr-plot_weekly_20251207_020000.tar.gz
├── monthly/
│   └── gofr-plot_monthly_20251201_020000.tar.gz
└── manifest.json
```

- **Backup files** - Compressed tar archives with timestamps
- **Checksum files** (.sha256) - SHA256 checksums for verification
- **manifest.json** - Catalog of all backups with metadata

## Monitoring

### View Backup Service Logs

```bash
# Real-time logs
docker-compose logs -f backup

# Last 100 lines
docker-compose logs --tail=100 backup
```

### Check Backup Service Status

```bash
docker-compose ps backup
```

### Backup Statistics

The `list_backups.sh` script provides comprehensive statistics:
- Total number of backups
- Total storage used
- Backup counts by tier
- Oldest and newest backups
- Individual backup details

## Troubleshooting

### Backup Service Not Starting

1. Check logs: `docker-compose logs backup`
2. Verify Docker volumes exist: `docker volume ls | grep gofr-plot`
3. Check configuration: `docker exec gofr-plot-backup env | grep GOFR_PLOT_BACKUP`

### Backups Not Running

1. Verify service is enabled: `GOFR_PLOT_BACKUP_ENABLED=true`
2. Check schedule syntax: Must be valid cron format
3. View next scheduled run in logs
4. Test manual backup: `./scripts/backup_now.sh`

### Restore Fails

1. Verify backup integrity first
2. Check available disk space
3. Ensure services are stopped during restore
4. Review restore script logs

### Disk Space Issues

1. Check backup volume usage: `docker system df -v`
2. Reduce retention settings:
   - Lower `GOFR_PLOT_BACKUP_RETENTION_DAYS`
   - Lower `GOFR_PLOT_BACKUP_MAX_COUNT`
3. Run manual cleanup: Service will cleanup on next scheduled run
4. Increase compression level (slower but smaller backups)

## Advanced Configuration

### Custom Backup Schedule Examples

```bash
# Every hour
GOFR_PLOT_BACKUP_SCHEDULE="0 * * * *"

# Every 4 hours
GOFR_PLOT_BACKUP_SCHEDULE="0 */4 * * *"

# Weekdays only at 2 AM
GOFR_PLOT_BACKUP_SCHEDULE="0 2 * * 1-5"

# First day of month at midnight
GOFR_PLOT_BACKUP_SCHEDULE="0 0 1 * *"
```

### Environment-Specific Configuration

Create a `.env` file in the docker directory:

```bash
# Production - frequent backups, longer retention
GOFR_PLOT_BACKUP_SCHEDULE="0 */6 * * *"
GOFR_PLOT_BACKUP_RETENTION_DAYS=90
GOFR_PLOT_BACKUP_COMPRESSION=xz
GOFR_PLOT_BACKUP_ENABLE_WEEKLY=true
GOFR_PLOT_BACKUP_ENABLE_MONTHLY=true

# Development - daily backups, short retention
GOFR_PLOT_BACKUP_SCHEDULE="0 2 * * *"
GOFR_PLOT_BACKUP_RETENTION_DAYS=7
GOFR_PLOT_BACKUP_MAX_COUNT=10
GOFR_PLOT_BACKUP_COMPRESSION=gzip
```

### Disable Backups Temporarily

```bash
# Set in docker-compose.yml or .env
GOFR_PLOT_BACKUP_ENABLED=false

# Restart backup service
docker-compose restart backup
```

## Backup Best Practices

1. **Test Restores Regularly** - Verify backups can be restored successfully
2. **Monitor Disk Usage** - Ensure adequate space for backups
3. **Off-Site Backups** - Copy backup volume to external storage periodically
4. **Verify After Creation** - Keep `GOFR_PLOT_BACKUP_VERIFY_AFTER_BACKUP=true`
5. **Document Recovery** - Keep restore procedures documented and tested
6. **Alert on Failures** - Monitor backup service logs for errors

## File Manifest

- `docker/Dockerfile.backup` - Backup container image
- `docker/backup/backup_service.py` - Main orchestrator
- `docker/backup/backup_config.py` - Configuration management
- `docker/backup/housekeeping.py` - Retention and cleanup logic
- `docker/backup/verify.py` - Backup verification
- `scripts/backup_now.sh` - Manual backup trigger
- `scripts/list_backups.sh` - List all backups
- `scripts/restore_backup.sh` - Restore from backup
- `docker/docker-compose.yml` - Updated with backup service

## Security Considerations

- Backup service runs as non-privileged `gofr-plot` user
- Read-only mount of application data prevents accidental modification
- Checksums ensure backup integrity
- Backups stored in separate Docker volume
- No network ports exposed (internal service only)

## Performance Impact

- **Minimal** - Backups run during low-usage hours (default 2 AM)
- **Read-only access** - No locking or service interruption
- **Configurable compression** - Balance speed vs. size
- **Background operation** - No blocking of main services

## Support

For issues or questions:
1. Check logs: `docker-compose logs backup`
2. Verify configuration with `list_backups.sh`
3. Test manual operations: `backup_now.sh`
4. Review this documentation
