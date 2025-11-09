"""
Django management command for database restoration from backups.

Implements AC #5 from US-API-006 - provides CLI wrapper for RecoveryService.
"""

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from quran_backend.core.services.recovery import RecoveryService


class Command(BaseCommand):
    help = 'Restore database from backup stored in S3'

    def add_arguments(self, parser):
        parser.add_argument(
            '--date',
            type=str,
            required=True,
            help='Backup date in YYYY-MM-DD format'
        )
        parser.add_argument(
            '--target',
            type=str,
            choices=['staging', 'production'],
            default='staging',
            help='Target database (staging or production, default: staging)'
        )
        parser.add_argument(
            '--verify',
            action='store_true',
            help='Verify backup integrity before restoration'
        )
        parser.add_argument(
            '--skip-confirmation',
            action='store_true',
            help='Skip confirmation prompt for production restore (USE WITH CAUTION)'
        )
        parser.add_argument(
            '--list',
            action='store_true',
            help='List available backups instead of restoring'
        )
        parser.add_argument(
            '--days',
            type=int,
            default=30,
            help='Number of days to look back when listing backups (default: 30)'
        )

    def handle(self, *args, **options):
        recovery_service = RecoveryService()

        # Handle --list flag
        if options['list']:
            self.stdout.write(self.style.SUCCESS('Listing available backups...'))
            backups = recovery_service.list_available_backups(days=options['days'])

            if not backups:
                self.stdout.write(self.style.WARNING('No backups found'))
                return

            self.stdout.write(f"\nFound {len(backups)} backups:\n")
            for backup in backups:
                self.stdout.write(
                    f"  • {backup['date']} - {backup['size_mb']:.2f} MB "
                    f"({backup['age_days']} days old)"
                )
            return

        # Validate date format
        backup_date = options['date']
        try:
            from datetime import datetime
            datetime.strptime(backup_date, '%Y-%m-%d')
        except ValueError:
            raise CommandError('Invalid date format. Use YYYY-MM-DD')

        target = options['target']
        verify = options['verify']
        skip_confirmation = options['skip_confirmation']

        # Safety check for production restore
        if target == 'production' and not skip_confirmation:
            self.stdout.write(
                self.style.ERROR(
                    '\n⚠️  WARNING: Production database restore requested\n'
                )
            )
            self.stdout.write(
                'This operation will OVERWRITE the production database.\n'
                'Ensure you have:\n'
                '  1. Verified the backup in staging\n'
                '  2. Obtained dual authorization\n'
                '  3. Notified all stakeholders\n'
            )

            confirm = input('\nType "RESTORE PRODUCTION" to proceed: ')
            if confirm != 'RESTORE PRODUCTION':
                self.stdout.write(self.style.ERROR('Restore cancelled'))
                return

        # Execute restoration
        self.stdout.write(
            self.style.SUCCESS(
                f'\nStarting database restore from {backup_date} to {target}...'
            )
        )

        try:
            result = recovery_service.full_recovery_workflow(
                backup_date=backup_date,
                target_db=target,
                skip_confirmation=skip_confirmation
            )

            if result['success']:
                self.stdout.write(
                    self.style.SUCCESS(
                        f'\n✅ {result["message"]}\n'
                        f'Target: {result["target_db"]}\n'
                        f'Backup Date: {result["backup_date"]}'
                    )
                )
            else:
                raise CommandError(f'Restore failed: {result.get("message", "Unknown error")}')

        except Exception as e:
            raise CommandError(f'Restore failed: {str(e)}')
