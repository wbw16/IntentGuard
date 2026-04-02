## 1. Guard Subsystem Foundation

- [x] 1.1 Create the dedicated Guard subsystem module boundary and define shared request, decision, and configuration types.
- [x] 1.2 Move or wrap guard prompt selection, parser selection, and mode-specific normalization behind the Guard subsystem internals.
- [x] 1.3 Implement structured degraded-decision handling that preserves raw audit output when guard evaluation cannot be fully normalized.

## 2. Shared Configuration Path

- [x] 2.1 Add a shared Guard configuration resolver that preserves current per-agent environment variable names and default inheritance behavior.
- [x] 2.2 Update shared factories/builders so Guard dependencies are constructed through the shared configuration path.
- [x] 2.3 Migrate remaining guard-aware agents that are not security-enforcing to use the shared Guard construction path without changing their runtime behavior.

## 3. Secure Agent Integration

- [x] 3.1 Update `sec_react` to invoke the Guard subsystem before tool execution and enforce the normalized allow/block decision.
- [x] 3.2 Update `sec_planexecute` to invoke the Guard subsystem before planned tool execution and enforce the normalized allow/block decision.
- [x] 3.3 Update `react_firewall` to perform alignment review through the Guard subsystem and enforce the normalized allow/block decision.
- [x] 3.4 Remove direct secure-agent reliance on raw guard parser fields, prompt registries, and ad hoc threshold handling.

## 4. Verification And Documentation

- [x] 4.1 Add regression tests for Guard decision normalization, degraded evaluations, and shared configuration compatibility.
- [x] 4.2 Add integration tests covering allowed and blocked execution paths for secure agents using the shared Guard interface.
- [x] 4.3 Update project documentation to describe the Guard subsystem boundary, shared configuration flow, and agent integration expectations.
