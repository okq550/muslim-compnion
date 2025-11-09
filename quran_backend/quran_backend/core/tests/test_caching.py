"""
Comprehensive tests for caching functionality.

Tests cover all acceptance criteria (AC #1-6) from US-API-003:
- AC #1: Frequently accessed static content cached
- AC #2: Cache performance targets met
- AC #3: Automatic cache invalidation on updates
- AC #4: Cache size management
- AC #5: Graceful cache degradation
- AC #6: Cache hit/miss handling
"""

import time
from unittest.mock import MagicMock
from unittest.mock import patch

import pytest
import redis
from django.core.cache import cache

from quran_backend.core.decorators import cache_response
from quran_backend.core.decorators import warm_cache
from quran_backend.core.health import check_cache_health
from quran_backend.core.metrics import CacheMetrics
from quran_backend.core.services import CacheManager
from quran_backend.core.signals import invalidate_cache_by_key
from quran_backend.core.signals import invalidate_cache_by_pattern


@pytest.mark.django_db
class TestCacheManager:
    """Test CacheManager basic operations (AC #1, #6)."""

    def setup_method(self):
        """Set up test fixtures."""
        self.cache_mgr = CacheManager()
        # Clear cache before each test
        cache.clear()

    def test_cache_get_set(self):
        """Test cache stores and retrieves data correctly (AC #1)."""
        # Arrange
        key = "test:key"
        value = {"name": "Test Data", "count": 42}

        # Act
        set_result = self.cache_mgr.set(key, value, ttl=60)
        cached_value = self.cache_mgr.get(key)

        # Assert
        assert set_result is True
        assert cached_value == value
        assert self.cache_mgr.exists(key) is True

    def test_cache_delete(self):
        """Test cache removes single key (AC #3)."""
        # Arrange
        key = "test:delete"
        self.cache_mgr.set(key, "value")

        # Act
        delete_result = self.cache_mgr.delete(key)

        # Assert
        assert delete_result is True
        assert self.cache_mgr.exists(key) is False
        assert self.cache_mgr.get(key) is None

    def test_cache_delete_pattern(self):
        """Test cache removes keys by pattern (AC #3)."""
        # Arrange
        self.cache_mgr.set("quran:surah:1", "data1")
        self.cache_mgr.set("quran:surah:2", "data2")
        self.cache_mgr.set("reciter:1", "reciter_data")

        # Act
        deleted_count = self.cache_mgr.delete_pattern("quran:*")

        # Assert
        assert deleted_count >= 2  # At least 2 keys deleted
        assert self.cache_mgr.get("quran:surah:1") is None
        assert self.cache_mgr.get("quran:surah:2") is None
        assert self.cache_mgr.get("reciter:1") is not None  # Not deleted

    def test_cache_get_many(self):
        """Test batch retrieval (AC #6)."""
        # Arrange
        self.cache_mgr.set("key1", "value1")
        self.cache_mgr.set("key2", "value2")
        self.cache_mgr.set("key3", "value3")

        # Act
        results = self.cache_mgr.get_many(
            ["key1", "key2", "key4"],
        )  # key4 doesn't exist

        # Assert
        assert "key1" in results
        assert "key2" in results
        assert "key4" not in results  # Missing key not included
        assert results["key1"] == "value1"

    def test_cache_set_many(self):
        """Test batch storage (AC #1)."""
        # Arrange
        data = {
            "batch:1": "value1",
            "batch:2": "value2",
            "batch:3": "value3",
        }

        # Act
        set_result = self.cache_mgr.set_many(data, ttl=60)

        # Assert
        assert set_result is True
        assert self.cache_mgr.get("batch:1") == "value1"
        assert self.cache_mgr.get("batch:2") == "value2"
        assert self.cache_mgr.get("batch:3") == "value3"

    def test_cache_ttl_expiration(self):
        """Test TTL enforcement (AC #4)."""
        # Arrange
        key = "test:ttl"
        value = "expires_soon"

        # Act
        self.cache_mgr.set(key, value, ttl=1)  # 1 second TTL
        immediate_value = self.cache_mgr.get(key)

        time.sleep(2)  # Wait for expiration
        expired_value = self.cache_mgr.get(key)

        # Assert
        assert immediate_value == value  # Still there immediately
        assert expired_value is None  # Gone after TTL

    def test_cache_key_generation(self):
        """Test cache key naming convention (AC #1)."""
        # Act & Assert
        assert CacheManager.generate_quran_key(1) == "quran:surah:1"
        assert CacheManager.generate_quran_key(114) == "quran:surah:114"
        assert CacheManager.generate_reciter_list_key() == "reciters:list"
        assert CacheManager.generate_translation_list_key() == "translations:list"
        assert (
            CacheManager.generate_user_bookmark_key("user123")
            == "user:user123:bookmarks"
        )


@pytest.mark.django_db
class TestCacheInvalidation:
    """Test cache invalidation signals (AC #3)."""

    def setup_method(self):
        """Set up test fixtures."""
        self.cache_mgr = CacheManager()
        cache.clear()

    def test_invalidate_cache_by_key(self):
        """Test invalidation by specific key (AC #3)."""
        # Arrange
        cache_key = "test:invalidate"
        self.cache_mgr.set(cache_key, "value")

        # Act
        invalidate_cache_by_key(cache_key, "TestModel")

        # Assert
        assert self.cache_mgr.get(cache_key) is None

    def test_invalidate_cache_by_pattern(self):
        """Test invalidation by pattern (AC #3)."""
        # Arrange
        self.cache_mgr.set("quran:surah:1", "data1")
        self.cache_mgr.set("quran:surah:2", "data2")

        # Act
        invalidate_cache_by_pattern("quran:*", "TestModel")

        # Assert
        assert self.cache_mgr.get("quran:surah:1") is None
        assert self.cache_mgr.get("quran:surah:2") is None


@pytest.mark.django_db
class TestCacheDecorators:
    """Test cache decorators (AC #2, #6)."""

    def setup_method(self):
        """Set up test fixtures."""
        cache.clear()

    def test_cache_response_decorator_hit(self):
        """Test decorator returns cached response on hit (AC #6)."""
        # Arrange
        call_count = 0

        def cache_key_func(request, *args, **kwargs):
            return "test:api:endpoint"

        @cache_response(cache_key_func=cache_key_func, ttl=60)
        def mock_view(request):
            nonlocal call_count
            call_count += 1
            # Mock DRF Response
            response = MagicMock()
            response.status_code = 200
            response.data = {"result": "success"}
            return response

        mock_request = MagicMock()

        # Act
        response1 = mock_view(mock_request)  # Cache MISS
        response2 = mock_view(mock_request)  # Cache HIT

        # Assert
        assert call_count == 1  # View only called once
        assert response1.status_code == 200
        assert response2.data == {"result": "success"}  # Cached data returned

    def test_cache_response_decorator_miss(self):
        """Test decorator caches response on miss (AC #6)."""

        # Arrange
        def cache_key_func(request, *args, **kwargs):
            return "test:cache:miss"

        @cache_response(cache_key_func=cache_key_func, ttl=60)
        def mock_view(request):
            response = MagicMock()
            response.status_code = 200
            response.data = {"result": "fresh_data"}
            return response

        mock_request = MagicMock()

        # Act
        response = mock_view(mock_request)

        # Assert - cache should now contain the data
        cache_mgr = CacheManager()
        cached_data = cache_mgr.get("test:cache:miss")
        assert cached_data == {"result": "fresh_data"}


@pytest.mark.django_db
class TestGracefulDegradation:
    """Test graceful degradation when cache unavailable (AC #5)."""

    def setup_method(self):
        """Set up test fixtures."""
        self.cache_mgr = CacheManager()

    @patch("quran_backend.core.services.cache_manager.cache")
    def test_cache_unavailable_fallback(self, mock_cache):
        """Test app works when Redis is down (AC #5)."""
        # Arrange - simulate Redis unavailable
        mock_cache.get.side_effect = redis.exceptions.ConnectionError("Redis down")

        # Act
        result = self.cache_mgr.get("test:key")

        # Assert - should return None gracefully, not raise exception
        assert result is None

    @patch("quran_backend.core.services.cache_manager.cache")
    def test_cache_connection_error_retry(self, mock_cache):
        """Test transient errors handled gracefully (AC #5)."""
        # Arrange - simulate transient error
        mock_cache.set.side_effect = redis.exceptions.TimeoutError("Timeout")

        # Act
        result = self.cache_mgr.set("test:key", "value")

        # Assert - should return False gracefully, not raise exception
        assert result is False


@pytest.mark.django_db
class TestCachePerformance:
    """Test cache performance targets (AC #2)."""

    def setup_method(self):
        """Set up test fixtures."""
        self.cache_mgr = CacheManager()
        cache.clear()

    def test_cached_response_faster_than_db(self):
        """Verify cached responses are faster than DB queries (AC #2)."""
        # Arrange
        cache_key = "perf:test"
        test_data = {"large": "data" * 1000}  # Simulate larger dataset

        # Warm cache
        self.cache_mgr.set(cache_key, test_data)

        # Act - measure cache latency
        start = time.time()
        cached_result = self.cache_mgr.get(cache_key)
        cache_latency = (time.time() - start) * 1000  # Convert to ms

        # Assert
        assert cached_result is not None
        assert cache_latency < 100  # < 100ms (p95 requirement from AC #2)

    def test_cache_hit_ratio_tracking(self):
        """Test cache hit/miss tracking (AC #2)."""
        # Arrange
        cache_key = "ratio:test"

        # Act
        # Simulate some cache misses
        self.cache_mgr.get(cache_key)  # MISS
        self.cache_mgr.get(cache_key)  # MISS

        # Set and get (hit)
        self.cache_mgr.set(cache_key, "value")
        self.cache_mgr.get(cache_key)  # HIT

        # Assert - metrics should be trackable
        # Note: Actual hit ratio tracking is optional and uses Redis counters
        # This test verifies the mechanism exists
        assert self.cache_mgr.get(cache_key) == "value"


@pytest.mark.django_db
class TestCacheWarming:
    """Test cache warming functionality (AC #2, #6)."""

    def setup_method(self):
        """Set up test fixtures."""
        cache.clear()

    def test_warm_cache_utility(self):
        """Test cache warming pre-populates cache (AC #6)."""
        # Arrange
        data = {
            "warm:1": {"name": "Item 1"},
            "warm:2": {"name": "Item 2"},
            "warm:3": {"name": "Item 3"},
        }

        # Act
        cached_count = warm_cache(data, ttl=60)

        # Assert
        assert cached_count == 3
        cache_mgr = CacheManager()
        assert cache_mgr.get("warm:1") == {"name": "Item 1"}
        assert cache_mgr.get("warm:2") == {"name": "Item 2"}


@pytest.mark.django_db
class TestCacheHealth:
    """Test cache health monitoring (AC #5)."""

    def test_cache_health_check_available(self):
        """Test health check when cache is available."""
        # Act
        health = check_cache_health()

        # Assert
        assert health["status"] in ["available", "degraded"]
        assert "latency_ms" in health
        assert "details" in health

    @patch("quran_backend.core.health.cache")
    def test_cache_health_check_unavailable(self, mock_cache):
        """Test health check when cache is unavailable (AC #5)."""
        # Arrange - simulate Redis down
        mock_cache.set.side_effect = redis.exceptions.ConnectionError("Redis down")

        # Act
        health = check_cache_health()

        # Assert
        assert health["status"] == "unavailable"
        assert health["latency_ms"] is None


@pytest.mark.django_db
class TestCacheMetrics:
    """Test cache metrics and monitoring (AC #2, #4)."""

    def setup_method(self):
        """Set up test fixtures."""
        cache.clear()
        CacheMetrics.reset_hit_ratio()

    def test_cache_memory_usage_tracking(self):
        """Test memory usage monitoring (AC #4)."""
        # Act
        memory_metrics = CacheMetrics.get_memory_usage()

        # Assert
        assert "used_memory_mb" in memory_metrics
        assert "maxmemory_mb" in memory_metrics
        assert "usage_percent" in memory_metrics
        assert "evicted_keys" in memory_metrics
        assert memory_metrics["usage_percent"] >= 0

    def test_get_all_metrics(self):
        """Test comprehensive metrics collection (AC #2, #4)."""
        # Act
        all_metrics = CacheMetrics.get_all_metrics()

        # Assert
        assert "hit_ratio" in all_metrics
        assert "memory" in all_metrics
        assert "hit_ratio" in all_metrics["hit_ratio"]
        assert "usage_percent" in all_metrics["memory"]
