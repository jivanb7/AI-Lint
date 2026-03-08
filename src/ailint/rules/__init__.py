"""Rule package — importing this module registers all built-in rules."""

from ailint.rules.ail001_prompt_injection import PromptInjectionRule  # noqa: F401
from ailint.rules.ail002_unbounded_tokens import UnboundedTokensRule  # noqa: F401
from ailint.rules.ail003_hardcoded_model import HardcodedModelRule  # noqa: F401
from ailint.rules.ail004_missing_retry import MissingRetryRule  # noqa: F401
from ailint.rules.ail005_exposed_api_key import ExposedAPIKeyRule  # noqa: F401
from ailint.rules.ail006_missing_error_handling import MissingErrorHandlingRule  # noqa: F401
from ailint.rules.ail007_no_input_validation import NoInputValidationRule  # noqa: F401
from ailint.rules.ail008_rag_antipatterns import RAGAntiPatternRule  # noqa: F401
from ailint.rules.ail009_missing_timeout import MissingTimeoutRule  # noqa: F401
from ailint.rules.ail010_sync_in_async import SyncInAsyncRule  # noqa: F401
from ailint.rules.ail011_temperature_not_set import TemperatureNotSetRule  # noqa: F401
from ailint.rules.ail012_no_streaming import NoStreamingRule  # noqa: F401
