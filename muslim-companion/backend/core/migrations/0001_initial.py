# Generated migration for BackupStatus model (US-API-006)

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='BackupStatus',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('backup_date', models.DateTimeField(help_text='Date/time when backup was initiated')),
                ('status', models.CharField(choices=[('success', 'Success'), ('failed', 'Failed'), ('in_progress', 'In Progress')], help_text='Backup execution status', max_length=20)),
                ('file_size_mb', models.DecimalField(decimal_places=2, help_text='Backup file size in megabytes', max_digits=10)),
                ('duration_seconds', models.IntegerField(help_text='Backup duration in seconds')),
                ('checksum', models.CharField(help_text='SHA-256 checksum of backup file', max_length=64)),
                ('s3_key', models.CharField(help_text='S3 object key where backup is stored', max_length=500)),
                ('error_message', models.TextField(blank=True, help_text='Error message if backup failed', null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True, help_text='Timestamp when record was created')),
            ],
            options={
                'verbose_name': 'Backup Status',
                'verbose_name_plural': 'Backup Statuses',
                'db_table': 'core_backup_status',
                'ordering': ['-backup_date'],
            },
        ),
        migrations.AddIndex(
            model_name='backupstatus',
            index=models.Index(fields=['-backup_date'], name='idx_backup_date'),
        ),
        migrations.AddIndex(
            model_name='backupstatus',
            index=models.Index(fields=['status'], name='idx_backup_status'),
        ),
    ]
