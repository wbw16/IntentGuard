## Why

IntentGuard's current guard logic is spread across agent files, runtime wrappers, prompt registries, and parser maps, which makes the guard difficult to evolve as the project's primary research object. Before adding intent schemas, fine-grained interventions, or trained guard models, we need a first-class guard subsystem with a stable interface that agents can depend on without knowing its internal prompting and parsing details.

## What Changes

- Introduce a dedicated guard subsystem that owns guard request construction, model invocation, parsing, fallback behavior, and decision formatting behind a shared public interface.
- Define a common guard decision contract that can represent both tool-safety review and alignment review, including pass/block signals, normalized reasons, and raw audit payloads.
- Move secure agent integrations to the guard subsystem interface so agent code no longer calls guard prompt registries, parser maps, or ad hoc guard decision thresholds directly.
- Centralize guard configuration resolution and failure handling so secure agents construct guard dependencies consistently and surface the same runtime errors when guard setup is incomplete.
- Add verification coverage for shared guard decisions, integration behavior in secure agents, and regression protection for repo-root execution paths.

## Capabilities

### New Capabilities
- `guard-subsystem-interface`: Provide a first-class Guard API that accepts normalized evaluation input and returns normalized guard decisions for safety and alignment checks.
- `guard-agent-preexecution-gating`: Require secure agents to perform pre-execution guard review through the shared Guard API and consume a common decision result before any tool call is executed.
- `guard-configuration-resolution`: Resolve guard model settings, defaults, and setup failures through a shared configuration path instead of duplicating guard wiring per agent.

### Modified Capabilities
- None.

## Impact

- Affected code and modules: `agents/`, `runtime/`, potential new `guard/` package or equivalent shared subsystem path, shared tests, and project documentation
- Affected runtime behavior: pre-execution tool safety review, alignment review, guard setup failures, and audit-friendly decision reporting
- Affected research workflow: future intent-schema, intervention-policy, and guard-training changes will be able to build on a stable subsystem instead of editing each agent independently
