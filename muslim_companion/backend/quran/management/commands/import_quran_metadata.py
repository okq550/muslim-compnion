"""Management command to import Quran metadata from Tanzil XML file.

Implements AC #4: Surah Metadata Import Command Works Correctly
- Parses docs/Data/quran-data.xml
- Creates/updates all 114 Surah records with complete metadata
- Updates Verse records with Juz/Page/Hizb positional data
- Imports revelation_order and revelation_note for each Surah
- Logs progress and errors
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
    """Import Quran Surah metadata and verse positional data from Tanzil XML."""

    help = "Import Quran metadata from docs/Data/quran-data.xml"

    def add_arguments(self, parser):
        """Add command arguments."""
        parser.add_argument(
            "--file",
            type=str,
            default="docs/Data/quran-data.xml",
            help="Path to quran-data.xml file (default: docs/Data/quran-data.xml)",
        )

    def handle(self, *args, **options):
        """Execute the import command."""
        xml_path = Path(options["file"])

        if not xml_path.exists():
            self.stderr.write(
                self.style.ERROR(f"XML file not found: {xml_path}"),
            )
            logger.error(
                "Quran metadata import failed: file not found",
                extra={"path": str(xml_path)},
            )
            return

        self.stdout.write(f"Importing Quran metadata from {xml_path}")
        logger.info("Starting Quran metadata import", extra={"path": str(xml_path)})

        try:
            with transaction.atomic():
                stats = self._import_metadata(xml_path)

            self.stdout.write(
                self.style.SUCCESS(
                    f"\nImport complete:\n"
                    f"  Surahs: {stats['surahs_created']} created, "
                    f"{stats['surahs_updated']} updated\n"
                    f"  Verses updated with Juz data: {stats['verses_juz']}\n"
                    f"  Verses updated with Page data: {stats['verses_page']}\n"
                    f"  Verses updated with Hizb data: {stats['verses_hizb']}",
                ),
            )
            logger.info(
                "Quran metadata import completed successfully",
                extra={
                    "surahs_created": stats["surahs_created"],
                    "surahs_updated": stats["surahs_updated"],
                    "verses_juz": stats["verses_juz"],
                    "verses_page": stats["verses_page"],
                    "verses_hizb": stats["verses_hizb"],
                },
            )

        except Exception as e:
            self.stderr.write(
                self.style.ERROR(f"Import failed: {e}"),
            )
            logger.exception("Quran metadata import failed", extra={"error": str(e)})
            raise

    def _import_metadata(self, xml_path):
        """Parse XML and import metadata.

        Args:
            xml_path: Path to the XML file

        Returns:
            dict: Import statistics
        """
        tree = ET.parse(xml_path)
        root = tree.getroot()

        stats = {
            "surahs_created": 0,
            "surahs_updated": 0,
            "verses_juz": 0,
            "verses_page": 0,
            "verses_hizb": 0,
        }

        # Import Surah metadata
        suras_elem = root.find("suras")
        if suras_elem is not None:
            self._import_surahs(suras_elem, stats)

        # Import Juz data
        juzs_elem = root.find("juzs")
        if juzs_elem is not None:
            self._import_juz_data(juzs_elem, stats)

        # Import Page data
        pages_elem = root.find("pages")
        if pages_elem is not None:
            self._import_page_data(pages_elem, stats)

        # Import Hizb quarter data
        hizbs_elem = root.find("hizbs")
        if hizbs_elem is not None:
            self._import_hizb_data(hizbs_elem, stats)

        return stats

    def _import_surahs(self, suras_elem, stats):
        """Import Surah metadata."""
        self.stdout.write("Importing Surah metadata...")

        for sura_elem in suras_elem.findall("sura"):
            surah_id = int(sura_elem.get("index"))

            surah_data = {
                "name_arabic": sura_elem.get("name", ""),
                "name_english": sura_elem.get("ename", ""),
                "name_transliteration": sura_elem.get("tname", ""),
                "revelation_type": sura_elem.get("type", "Meccan"),
                "revelation_order": int(sura_elem.get("order", surah_id)),
                "total_verses": int(sura_elem.get("ayas", 0)),
                "mushaf_page_start": 1,  # Will be calculated from pages
                "juz_start": 1,  # Will be calculated from juzs
            }

            surah, created = Surah.objects.update_or_create(
                id=surah_id,
                defaults=surah_data,
            )

            if created:
                stats["surahs_created"] += 1
            else:
                stats["surahs_updated"] += 1

        self.stdout.write(f"  Processed {stats['surahs_created'] + stats['surahs_updated']} Surahs")

    def _import_juz_data(self, juzs_elem, stats):
        """Import Juz data and update verses."""
        self.stdout.write("Importing Juz data...")

        # Build juz boundaries: list of (juz_num, surah_id, verse_num)
        juz_boundaries = []
        for juz_elem in juzs_elem.findall("juz"):
            juz_num = int(juz_elem.get("index"))
            surah_id = int(juz_elem.get("sura"))
            verse_num = int(juz_elem.get("aya"))
            juz_boundaries.append((juz_num, surah_id, verse_num))

        # Update Surah juz_start values
        for juz_num, surah_id, verse_num in juz_boundaries:
            if verse_num == 1:  # Juz starts at first verse of Surah
                Surah.objects.filter(id=surah_id).update(juz_start=juz_num)

        # Calculate juz_number for each verse
        # Sort boundaries by surah, verse to process in order
        juz_boundaries.sort(key=lambda x: (x[1], x[2]))

        # Create a mapping of (surah_id, verse_num) -> juz_num
        all_verses = Verse.objects.all().order_by("surah_id", "verse_number")

        current_juz = 1
        juz_idx = 0

        for verse in all_verses:
            # Check if we've reached the next juz boundary
            while juz_idx < len(juz_boundaries):
                next_juz, next_surah, next_verse = juz_boundaries[juz_idx]
                if (verse.surah_id, verse.verse_number) >= (next_surah, next_verse):
                    current_juz = next_juz
                    juz_idx += 1
                else:
                    break

            if verse.juz_number != current_juz:
                verse.juz_number = current_juz
                verse.save(update_fields=["juz_number"])
                stats["verses_juz"] += 1

        self.stdout.write(f"  Updated {stats['verses_juz']} verses with Juz data")

    def _import_page_data(self, pages_elem, stats):
        """Import Mushaf page data and update verses."""
        self.stdout.write("Importing Page data...")

        # Build page boundaries
        page_boundaries = []
        for page_elem in pages_elem.findall("page"):
            page_num = int(page_elem.get("index"))
            surah_id = int(page_elem.get("sura"))
            verse_num = int(page_elem.get("aya"))
            page_boundaries.append((page_num, surah_id, verse_num))

        # Update Surah mushaf_page_start values
        surah_first_pages = {}
        for page_num, surah_id, verse_num in page_boundaries:
            if surah_id not in surah_first_pages:
                surah_first_pages[surah_id] = page_num

        for surah_id, first_page in surah_first_pages.items():
            Surah.objects.filter(id=surah_id).update(mushaf_page_start=first_page)

        # Calculate mushaf_page for each verse
        page_boundaries.sort(key=lambda x: (x[1], x[2]))

        all_verses = Verse.objects.all().order_by("surah_id", "verse_number")

        current_page = 1
        page_idx = 0

        for verse in all_verses:
            # Check if we've reached the next page boundary
            while page_idx < len(page_boundaries):
                next_page, next_surah, next_verse = page_boundaries[page_idx]
                if (verse.surah_id, verse.verse_number) >= (next_surah, next_verse):
                    current_page = next_page
                    page_idx += 1
                else:
                    break

            if verse.mushaf_page != current_page:
                verse.mushaf_page = current_page
                verse.save(update_fields=["mushaf_page"])
                stats["verses_page"] += 1

        self.stdout.write(f"  Updated {stats['verses_page']} verses with Page data")

    def _import_hizb_data(self, hizbs_elem, stats):
        """Import Hizb quarter data and update verses."""
        self.stdout.write("Importing Hizb quarter data...")

        # Build hizb quarter boundaries
        hizb_boundaries = []
        for quarter_elem in hizbs_elem.findall("quarter"):
            quarter_num = int(quarter_elem.get("index"))
            surah_id = int(quarter_elem.get("sura"))
            verse_num = int(quarter_elem.get("aya"))
            hizb_boundaries.append((quarter_num, surah_id, verse_num))

        # Calculate hizb_quarter for each verse
        hizb_boundaries.sort(key=lambda x: (x[1], x[2]))

        all_verses = Verse.objects.all().order_by("surah_id", "verse_number")

        current_hizb = 1
        hizb_idx = 0

        for verse in all_verses:
            # Check if we've reached the next hizb boundary
            while hizb_idx < len(hizb_boundaries):
                next_hizb, next_surah, next_verse = hizb_boundaries[hizb_idx]
                if (verse.surah_id, verse.verse_number) >= (next_surah, next_verse):
                    current_hizb = next_hizb
                    hizb_idx += 1
                else:
                    break

            if verse.hizb_quarter != current_hizb:
                verse.hizb_quarter = current_hizb
                verse.save(update_fields=["hizb_quarter"])
                stats["verses_hizb"] += 1

        self.stdout.write(f"  Updated {stats['verses_hizb']} verses with Hizb data")
