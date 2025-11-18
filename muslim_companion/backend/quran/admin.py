from django.contrib import admin

from .models import Surah, Verse, Juz, Page


@admin.register(Surah)
@admin.register(Verse)
@admin.register(Juz)
@admin.register(Page)
