class CloudShortenerError(Exception):
    """Base exception for all application-specific errors."""

    error_code = 'app:cloudshortener_error'


class MalformedResponseError(CloudShortenerError):
    """Raised when a response is malformed."""

    error_code = 'app:malformed_response_error'


class ConfigurationError(CloudShortenerError):
    """Base exception for all configuration errors."""

    error_code = 'config:configuration_error'


class MissingEnvironmentVariableError(ConfigurationError):
    """Raised when a required environment variable is missing."""

    error_code = 'config:missing_environment_variable_error'


class BadConfigurationError(ConfigurationError):
    """Raised when the application is configured with invalid parameters."""

    error_code = 'config:bad_configuration_error'


class InfrastructureError(CloudShortenerError):
    """Base exception for all infrastructure (AWS) errors."""

    error_code = 'infra:infrastructure_error'


class AppConfigError(InfrastructureError):
    """Raised when AppConfig responds with erroneous data."""

    error_code = 'infra:appconfig_error'
