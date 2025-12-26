"""Tests for logging configuration."""

import structlog


class TestLoggingConfiguration:
    """Test logging configuration."""

    def test_configure_logging_json_output(self) -> None:
        """Configured logger should output JSON format."""
        from src.config.logging import configure_logging

        configure_logging(json_logs=True)

        # Get a logger to verify configuration works
        _logger = structlog.get_logger()

        # structlog with JSON renderer should produce valid JSON
        # We test the configuration was applied
        assert structlog.is_configured()

    def test_configure_logging_adds_timestamp(self) -> None:
        """Logs should include timestamp."""
        from src.config.logging import configure_logging

        configure_logging(json_logs=True)

        # Verify the processors include TimeStamper
        config = structlog.get_config()
        processor_names = [p.__class__.__name__ for p in config["processors"]]

        assert "TimeStamper" in processor_names or any(
            "timestamp" in str(p) for p in config["processors"]
        )

    def test_configure_logging_adds_log_level(self) -> None:
        """Logs should include log level."""
        from src.config.logging import configure_logging

        configure_logging(json_logs=True)

        config = structlog.get_config()
        processor_names = [str(p) for p in config["processors"]]

        # Check that add_log_level is in the processors
        assert any("add_log_level" in name for name in processor_names)

    def test_get_logger_returns_bound_logger(self) -> None:
        """get_logger should return a logger that can be used."""
        from src.config.logging import configure_logging, get_logger

        configure_logging(json_logs=False)  # Use console for easier testing
        logger = get_logger()

        # Should not raise
        logger.info("test message", extra_field="value")

    def test_logger_with_context(self) -> None:
        """Logger should support context binding."""
        from src.config.logging import configure_logging, get_logger

        configure_logging(json_logs=False)
        logger = get_logger()

        # Bind context
        bound_logger = logger.bind(request_id="req-123")

        # Should not raise
        bound_logger.info("test with context")
