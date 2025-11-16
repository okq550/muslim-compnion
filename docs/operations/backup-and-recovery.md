# Backup and Recovery Operations Manual

**Document Version**: 1.0
**Last Updated**: 2025-11-10
**Story**: US-API-006

## Overview

This document describes the backup and recovery procedures for the Muslim Companion API database. Automated daily backups ensure data protection and business continuity.

## Backup System

### Backup Schedule

- **Daily Backups**: Every day at 2:00 AM UTC
- **Automated Process**: Runs via Celery Beat scheduler
- **Non-blocking**: Background execution doesn't affect application performance

### What Gets Backed Up

All PostgreSQL database content including:
- User accounts, profiles, bookmarks, preferences, notes
- Quran text, recitations, translations, Tafseer
- System settings, metadata, application configuration
- Audit logs (authentication events, error logs, rate limit violations)
- Database schema and migration state

### Backup Process

1. **Database Dump**: `pg_dump` creates complete SQL backup
2. **Compression**: Gzip compression reduces size by ~70%
3. **Encryption**: AES-256 encryption via AWS KMS
4. **Upload**: Encrypted backup uploaded to S3
5. **Verification**: SHA-256 checksum validates integrity
6. **Logging**: Success/failure logged to Sentry

### Storage Location

- **S3 Bucket**: `quran-backend-backups-{environment}`
- **Path Structure**: `{environment}/{YYYY-MM-DD}/db_backup.sql.gz.enc`
- **Encryption**: Server-side encryption with KMS
- **Versioning**: Enabled for redundancy

### Retention Policy

- **Daily backups**: 30 days
- **Weekly backups (Sunday)**: 90 days
- **Monthly backups (1st of month)**: 1 year
- **Automated cleanup**: Weekly on Monday at 3:00 AM UTC

## Recovery Procedures

### List Available Backups

```bash
# List backups for past 30 days
python manage.py list_backups --days=30

# List backups for specific period
python manage.py list_backups --days=90
```

### Restore to Staging (Validation)

**ALWAYS restore to staging first for validation**

```bash
# Restore specific backup to staging
python manage.py restore_from_backup \
  --date=2025-11-06 \
  --target=staging \
  --verify

# Verify restoration
python manage.py check_database_integrity --database=staging
```

### Restore to Production

**Requires dual authorization and explicit approval**

```bash
# Restore to production (requires confirmation)
python manage.py restore_from_backup \
  --date=2025-11-06 \
  --target=production \
  --verify

# Skip confirmation (USE WITH CAUTION - requires approval)
python manage.py restore_from_backup \
  --date=2025-11-06 \
  --target=production \
  --verify \
  --skip-confirmation
```

### Recovery Workflow

1. **Identify Backup Date**: Determine which backup to restore
2. **Download from S3**: Backup downloaded and decrypted automatically
3. **Verify Integrity**: SHA-256 checksum validated before restore
4. **Restore to Staging**: Always restore to staging first
5. **Validate Data**: Run integrity checks on staging database
6. **Get Approval**: Obtain dual authorization for production restore
7. **Restore to Production**: Execute production restore with approval
8. **Post-Restore Verification**: Confirm data integrity and application health

## Disaster Recovery Scenarios

### Complete Database Loss

1. List recent backups: `python manage.py list_backups --days=7`
2. Identify last successful backup before incident
3. Restore to staging for validation
4. Obtain approval and restore to production
5. Verify all services operational

**RTO (Recovery Time Objective)**: < 4 hours
**RPO (Recovery Point Objective)**: 24 hours (daily backups)

### Data Corruption

1. Identify corruption scope and timing
2. Find last backup before corruption occurred
3. Restore to staging, verify data integrity
4. Compare staging vs. production to confirm fix
5. Get approval and restore to production

### Accidental Data Deletion

1. Determine deletion timestamp
2. Find backup immediately before deletion
3. Restore to staging
4. Identify and extract deleted records
5. Selectively restore missing data to production

### Point-in-Time Recovery

AWS RDS provides 5-minute granularity point-in-time recovery:

```bash
# RDS point-in-time restore (via AWS CLI)
aws rds restore-db-instance-to-point-in-time \
  --source-db-instance-identifier quran-backend-prod \
  --target-db-instance-identifier quran-backend-recovery \
  --restore-time 2025-11-06T14:30:00Z
```

## Monitoring and Alerts

### Backup Health Dashboard

Monitor backup health via:
- **Last Successful Backup**: Timestamp of most recent success
- **Success Rate**: Percentage of successful backups (last 30 days)
- **Average Duration**: Typical backup completion time
- **Storage Used**: Total S3 storage consumed

### Alert Conditions

**CRITICAL Alerts** (immediate notification):
- Backup fails after all retries
- Integrity check fails (checksum mismatch)
- S3 upload fails repeatedly
- Backup hasn't run in > 36 hours

**WARNING Alerts**:
- Backup duration exceeds 2x average
- Success rate drops below 95%
- S3 storage exceeds budget threshold

### Weekly Health Reports

Automated weekly reports sent to ops team every Monday:
- Backup success count
- Total backups created
- Success rate percentage
- Total storage used
- Any failures or issues

## Troubleshooting

### Backup Fails with Database Connection Error

**Symptoms**: Backup task fails, error mentions "could not connect to database"

**Resolution**:
1. Verify database is accessible: `docker-compose ps postgres`
2. Check database credentials in environment variables
3. Test connection manually: `psql -h localhost -U postgres -d muslim_companion`
4. Review error logs in Sentry for detailed error message

### Backup Fails with S3 Upload Error

**Symptoms**: Backup creates successfully but upload to S3 fails

**Resolution**:
1. Verify S3 bucket exists and is accessible
2. Check IAM role permissions for backup service
3. Verify AWS credentials are valid
4. Check S3 bucket region matches configuration
5. Review CloudTrail logs for access denied errors

### Integrity Check Fails

**Symptoms**: Checksum mismatch detected after upload

**Resolution**:
1. DO NOT use this backup for restoration
2. Check S3 upload logs for corruption during transfer
3. Verify KMS encryption key is correct
4. Re-run backup immediately
5. Alert ops team if issue persists

### Recovery Fails on Staging

**Symptoms**: Database restore to staging fails or produces errors

**Resolution**:
1. Check psql version compatibility
2. Verify staging database exists and is accessible
3. Review error output from psql command
4. Try restoring from different backup date
5. If all backups fail, investigate backup creation process

## Quarterly Disaster Recovery Drill

**Schedule**: First Monday of each quarter at 10:00 AM

**Procedure**:
1. Select backup from previous month
2. Restore to isolated test environment
3. Verify all data integrity checks pass
4. Run sample queries to validate data
5. Measure recovery time and document
6. Generate drill report with findings
7. Update procedures based on learnings

## AWS Infrastructure Configuration

### S3 Bucket Setup

```bash
# Create backup bucket
aws s3api create-bucket \
  --bucket quran-backend-backups-production \
  --region us-east-1

# Enable versioning
aws s3api put-bucket-versioning \
  --bucket quran-backend-backups-production \
  --versioning-configuration Status=Enabled

# Block public access
aws s3api put-public-access-block \
  --bucket quran-backend-backups-production \
  --public-access-block-configuration \
    "BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true"
```

### KMS Key Setup

```bash
# Create KMS key for backups
aws kms create-key \
  --description "Muslim Companion Backup Encryption Key" \
  --key-usage ENCRYPT_DECRYPT \
  --origin AWS_KMS

# Create alias
aws kms create-alias \
  --alias-name alias/quran-backend-backup-key \
  --target-key-id <key-id>

# Enable automatic rotation
aws kms enable-key-rotation \
  --key-id <key-id>
```

### IAM Role Configuration

Required permissions for backup service:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:PutObject",
        "s3:GetObject",
        "s3:ListBucket",
        "s3:DeleteObject"
      ],
      "Resource": [
        "arn:aws:s3:::quran-backend-backups-*",
        "arn:aws:s3:::quran-backend-backups-*/*"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "kms:Encrypt",
        "kms:Decrypt",
        "kms:GenerateDataKey"
      ],
      "Resource": "arn:aws:kms:*:*:key/*",
      "Condition": {
        "StringEquals": {
          "kms:EncryptionContext:purpose": "backup"
        }
      }
    }
  ]
}
```

## Environment Variables

Required environment variables for backup/recovery:

```bash
# S3 Configuration
BACKUP_S3_BUCKET=quran-backend-backups-production
BACKUP_KMS_KEY_ID=alias/quran-backend-backup-key
ENVIRONMENT_NAME=production

# Retention Policy (optional, defaults shown)
BACKUP_RETENTION_DAYS_DAILY=30
BACKUP_RETENTION_DAYS_WEEKLY=90
BACKUP_RETENTION_DAYS_MONTHLY=365
```

## Contact Information

**Backup System Owner**: DevOps Team
**Escalation**: PagerDuty alerts sent to on-call engineer
**Sentry Project**: quran-backend-production
**AWS Account**: Production account (console access required)

---

**For questions or issues, create incident in PagerDuty or contact DevOps team via Slack #ops-alerts**
