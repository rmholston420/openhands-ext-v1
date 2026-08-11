# planner-medium-07-add-observability

## Task summary
Plan the addition of OpenTelemetry-based observability (traces + metrics) to an existing Python microservice, exporting to an OTLP collector.

## Reference plan (gold)

```json
{
  "steps": [
    {"id": "s1", "desc": "Add opentelemetry-api, opentelemetry-sdk, opentelemetry-exporter-otlp, and the framework instrumentation package (opentelemetry-instrumentation-fastapi or similar) to project dependencies.", "deps": []},
    {"id": "s2", "desc": "Configure the OTLP exporter endpoint via an OTEL_EXPORTER_OTLP_ENDPOINT environment variable; default to http://localhost:4317 for local dev.", "deps": ["s1"]},
    {"id": "s3", "desc": "Initialize a TracerProvider at application startup with the configured OTLP exporter and a service.name resource attribute.", "deps": ["s2"]},
    {"id": "s4", "desc": "Enable auto-instrumentation for the web framework, HTTP client, and database driver so spans are created without touching endpoint code.", "deps": ["s3"]},
    {"id": "s5", "desc": "Add custom application spans in critical business-logic paths using tracer.start_as_current_span, with meaningful span attributes for business context (user_id, operation, resource_id).", "deps": ["s4"]},
    {"id": "s6", "desc": "Initialize a MeterProvider with counters/histograms for domain-specific metrics (request_count, request_duration, error_count) alongside the framework's auto-metrics.", "deps": ["s3"]},
    {"id": "s7", "desc": "Add pytest coverage using the OpenTelemetry InMemorySpanExporter to verify spans are created and carry the expected attributes.", "deps": ["s5", "s6"]}
  ]
}
```

## Scoring rubric (0-100)

| Band | Criteria |
|---|---|
| 90-100 | 5-7 steps: dependencies → config → TracerProvider init → auto-instrumentation → custom spans → metrics → tests. Config uses environment variable (not hardcoded endpoint). |
| 70-89 | Traces covered but metrics missed OR auto-instrumentation missed (agent would hand-instrument every handler). |
| 40-69 | Instrumentation added but no test coverage (traces exist but no way to verify correctness). |
| 10-39 | Traces mentioned but no config strategy — hardcoded endpoint would break in production. |
| 0-9 | <3 steps or invalid schema. |

## Notes
Tests planner's understanding of OTel patterns. Key discriminator: does the plan use auto-instrumentation for framework code (correct) or propose adding decorators/spans to every handler (verbose, error-prone)?
