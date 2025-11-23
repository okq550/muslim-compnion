"""Management command to import Quran text from Tanzil XML file.

Implements AC #3: Quran Text Import Command Works Correctly
- Parses docs/Data/quran-uthmani.xml using ElementTree
- Creates/updates all 6,236 Verse records with Uthmani text
- Handles idempotent re-runs (updates existing, creates new)
- Logs progress and errors to console and logging system
- Transaction-safe (rollback on error)
"""

import logging
import xml.etree.ElementTree as ET
from pathlib import Path

from django.core.management.base import BaseCommand
from django.db import transaction

from backend.quran.models import Surah
from backend.quran.models import Verse

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    """Import Quran verse text from Tanzil Uthmani XML file."""

    help = "Import Quran text from docs/Data/quran-uthmani.xml"

    def add_arguments(self, parser):
        """Add command arguments."""
        parser.add_argument(
            "--file",
            type=str,
            default="docs/Data/quran-uthmani.xml",
            help="Path to quran-uthmani.xml file (default: docs/Data/quran-uthmani.xml)",
        )

    def handle(self, *args, **options):
        """Execute the import command."""
        xml_path = Path(options["file"])

        if not xml_path.exists():
            self.stderr.write(
                self.style.ERROR(f"XML file not found: {xml_path}"),
            )
            logger.error(
                "Quran text import failed: file not found",
                extra={"path": str(xml_path)},
            )
            return

        self.stdout.write(f"Importing Quran text from {xml_path}")
        logger.info("Starting Quran text import", extra={"path": str(xml_path)})

        try:
            with transaction.atomic():
                stats = self._import_verses(xml_path)

            self.stdout.write(
                self.style.SUCCESS(
                    f"\nImport complete:\n"
                    f"  Total verses: {stats['total']}\n"
                    f"  Created: {stats['created']}\n"
                    f"  Updated: {stats['updated']}\n"
                    f"  Surahs processed: {stats['surahs']}",
                ),
            )
            logger.info(
                "Quran text import completed successfully",
                extra={
                    "total_verses": stats["total"],
                    "verses_created": stats["created"],
                    "verses_updated": stats["updated"],
                    "surahs_count": stats["surahs"],
                },
            )

        except Exception as e:
            self.stderr.write(
                self.style.ERROR(f"Import failed: {e}"),
            )
            logger.exception("Quran text import failed", extra={"error": str(e)})
            raise

    def _import_verses(self, xml_path):
        """Parse XML and import verses.

        Args:
            xml_path: Path to the XML file

        Returns:
            dict: Import statistics
        """
        tree = ET.parse(xml_path)
        root = tree.getroot()

        stats = {
            "total": 0,
            "created": 0,
            "updated": 0,
            "surahs": 0,
        }

        for sura_elem in root.findall("sura"):
            surah_index = int(sura_elem.get("index"))
            stats["surahs"] += 1

            # Get or create Surah (metadata will be filled by import_quran_metadata)
            try:
                surah = Surah.objects.get(id=surah_index)
            except Surah.DoesNotExist:
                # Create placeholder Surah - metadata will be updated later
                surah = Surah.objects.create(
                    id=surah_index,
                    name_arabic=sura_elem.get("name", ""),
                    name_english="",
                    name_transliteration="",
                    revelation_type="Meccan",  # Placeholder
                    revelation_order=surah_index,  # Placeholder
                    total_verses=0,  # Will be calculated
                    mushaf_page_start=1,  # Placeholder
                    juz_start=1,  # Placeholder
                )

            for aya_elem in sura_elem.findall("aya"):
                verse_number = int(aya_elem.get("index"))
                text_uthmani = aya_elem.get("text", "")

                # Include bismillah if present (for first verse of Surahs)
                bismillah = aya_elem.get("bismillah", "")
                if bismillah and verse_number == 1:
                    # Prepend bismillah for first verse (except Al-Fatiha)
                    if surah_index != 1:  # Al-Fatiha has bismillah as verse 1
                        text_uthmani = f"{bismillah} {text_uthmani}"

                verse, created = Verse.objects.update_or_create(
                    surah=surah,
                    verse_number=verse_number,
                    defaults={
                        "text_uthmani": text_uthmani,
                        "text_simple": text_uthmani,  # Will be populated later
                        "juz_number": 1,  # Updated by metadata import
                        "mushaf_page": 1,  # Updated by metadata import
                        "hizb_quarter": 1,  # Updated by metadata import
                    },
                )

                stats["total"] += 1
                if created:
                    stats["created"] += 1
                else:
                    stats["updated"] += 1

                # Log progress every 1000 verses
                if stats["total"] % 1000 == 0:
                    self.stdout.write(f"Processed {stats['total']} verses...")
                    logger.info(
                        "Import progress",
                        extra={"verses_processed": stats["total"]},
                    )

        return stats
