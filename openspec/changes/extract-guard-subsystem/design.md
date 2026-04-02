## Context

IntentGuard currently treats the guard as a distributed mechanism rather than a first-class subsystem. The core runtime wrapper lives in `runtime/modeling.py`, prompt and parser assets live in `runtime/prompts.py` and `runtime/guardian_parser.py`, guard construction lives in `runtime/factory.py`, and secure-agent enforcement logic is duplicated across `agents/sec_react_agent.py`, `agents/sec_planexecute_agent.py`, and `agents/react_firewall_agent.py`. Several non-secure agents also instantiate a guard model even when they do not enforce it directly.

This shape was acceptable for Phase 0 baselines, but it is a poor foundation for the next research stages described in `课题总结.md`: structured intent, cross-validation against intent deception, fine-grained interventions, and trainable guard models. Those future changes need a stable place to live. If the guard remains spread across runtime and agent files, each new experiment will require touching multiple agents and will keep security policy tangled with agent orchestration.

## Goals / Non-Goals

**Goals:**

- Establish Guard as a first-class subsystem with a public interface that agents can call without knowing prompt, parser, or threshold details.
- Normalize guard evaluation input and output across tool-safety and alignment review paths.
- Centralize guard configuration resolution so agents stop duplicating guard wiring logic.
- Migrate secure agents to consume the shared guard interface before executing tools.
- Preserve current repo-root execution and baseline agent entrypoints while refactoring the internals.

**Non-Goals:**

- Rewriting all agents around LangChain or LangGraph.
- Introducing the Phase 1 intent schema, fine-grained rewrite/shrink/confirm actions, or new training pipelines in this change.
- Replacing the underlying model client stack or benchmark processors.
- Changing the external benchmark scope or Phase 0 output contracts.

## Decisions

### 1. Create a dedicated Guard subsystem with a narrow public API

This change will introduce a dedicated guard-owned module boundary, such as `guard/` or an equivalent shared subsystem path. The subsystem will define the public request and decision types used by callers, and it will own the evaluation workflow from request normalization through decision normalization.

Planned public surface:

- A normalized evaluation input type containing the user request, interaction history, current action, and action/tool context.
- A normalized decision type containing at minimum the evaluation mode, allow/block outcome, normalized reason, and raw audit payload.
- Public evaluation entrypoints for tool-safety review and alignment review.

Rationale:

- This makes Guard the primary research object instead of a helper attached to `StandaloneModel`.
- It gives future intent-aware and fine-grained intervention work a stable home.
- It lets agents depend on a security contract instead of runtime internals.

Alternatives considered:

- Move only `StandaloneGuardian` into a new file: improves file organization but does not solve policy and asset fragmentation.
- Keep Guard inside `runtime/modeling.py`: lowest churn, but it preserves the current architectural ambiguity.

### 2. Keep prompt selection, parser selection, and threshold mapping inside the Guard subsystem

The Guard subsystem will internally select prompt templates, parsers, and normalization logic for each evaluation mode. Agents will not inspect raw parser results or apply guard thresholds themselves. Instead, the subsystem will expose an explicit allow/block result plus normalized metadata.

This is especially important because the current code mixes two guard styles:

- risk-rating-based tool safety checks
- pass/fail alignment checks

The subsystem should absorb those differences and return a common contract to callers.

Rationale:

- Agent code should not know whether the guard used a risk score, a boolean, or a parser-specific schema.
- Threshold policy belongs to Guard because it is part of the safety decision, not the agent loop.
- A unified decision contract will simplify future experiments across multiple agents.

Alternatives considered:

- Continue returning raw dictionaries and let each agent interpret them: keeps short-term flexibility but preserves duplicated safety policy.
- Expose separate incompatible return types per guard mode: simpler internally, but it keeps callers coupled to mode-specific behavior.

### 3. Centralize guard configuration resolution while preserving existing environment compatibility

The current agent files duplicate guard-specific environment loading with separate prefixes for each agent. This change will move guard configuration resolution into a shared path while preserving existing environment variable names and fallback behavior where guard settings inherit the primary model configuration if guard-specific overrides are absent.

Rationale:

- Shared configuration resolution reduces duplicated wiring and inconsistent defaults.
- Preserving current environment names avoids unnecessary breakage for local experiments and benchmark scripts.
- A shared configuration path is the right place to standardize errors for missing credentials, unsupported guard model identifiers, and invalid runtime combinations.

Alternatives considered:

- Switch immediately to one global guard config namespace: cleaner long term, but unnecessarily breaking for the current repository.
- Leave config logic duplicated in each agent: simplest short term, but it conflicts with the goal of a true subsystem.

### 4. Migrate security-enforcing agents first and keep non-secure agents behaviorally stable

This change will prioritize the agents that currently enforce guard decisions before tool execution: `sec_react`, `sec_planexecute`, and `react_firewall`. They will be updated to invoke the shared guard interface and obey its normalized allow/block result. Agents that merely construct or expose a guard model without enforcing it can be adapted for consistency, but they should remain behaviorally stable in this change.

Rationale:

- These secure agents are where guard policy currently matters operationally.
- Limiting behavior changes reduces risk to the newly established Phase 0 baselines.
- It preserves a clean experimental distinction between guarded and unguarded agents.

Alternatives considered:

- Migrate every agent simultaneously: more uniform, but higher risk and more surface area than the user request requires.
- Update only one secure agent: lower effort, but it would leave the subsystem boundary half-adopted.

### 5. Preserve raw audit evidence in the normalized decision

The guard decision object will retain the raw model output and normalization metadata in addition to the final allow/block signal. This keeps the subsystem suitable for future auditing, offline replay, and guard-model evaluation without forcing agents to parse raw strings.

Rationale:

- The thesis direction explicitly values explainability and auditable authorization.
- Future training and evaluation work will likely need raw guard traces.
- Agents can remain simple while the subsystem stays research-friendly.

Alternatives considered:

- Return only final allow/block booleans: clean for callers, but loses research-critical evidence.
- Return only raw output plus helper methods: too much burden on callers.

## Risks / Trade-offs

- [The subsystem boundary may initially add adapter code on top of existing runtime objects] -> Mitigation: keep the first public API small and migrate existing wrappers incrementally rather than rebuilding the whole runtime.
- [Normalizing risk-score and alignment-check flows into one decision shape may hide useful mode-specific detail] -> Mitigation: keep explicit `mode` and raw audit fields in the decision payload.
- [Shared configuration resolution could accidentally change existing guard defaults] -> Mitigation: preserve current per-agent environment names and add regression coverage for inherited defaults.
- [Partial migration could leave some agents on old and new patterns at once] -> Mitigation: scope the behavioral contract to secure agents first and document any intentionally unchanged agents.

## Migration Plan

1. Introduce the Guard subsystem package/module boundary and define the normalized request, decision, and configuration types.
2. Move or wrap prompt/template selection, parser selection, and threshold normalization behind the new subsystem interface.
3. Migrate secure agents to use the new interface for pre-execution tool review and alignment review.
4. Adapt shared factories/builders so guard construction flows through the centralized configuration path.
5. Add tests and documentation covering the public Guard contract, secure-agent integration, and configuration compatibility.

Rollback remains straightforward because the change is internal to the repository: restore the previous `StandaloneGuardian`-centric call path and revert secure-agent integrations if the subsystem boundary proves too disruptive.

## Open Questions

- Should the first normalized decision contract expose only allow/block semantics, or also reserve structured fields now for future actions such as rewrite, shrink, confirm, and replace?
- Do we want non-secure agents to keep constructing guard dependencies for prompt compatibility, or should that cleanup wait for a later change once the secure-agent migration is complete?
