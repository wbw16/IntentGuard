## ADDED Requirements

### Requirement: Dimension profiles configurable in training_config.yaml
`configs/training_config.yaml` SHALL contain a `dimension_profiles` section that maps each `attack_type` to per-dimension weight coefficients (`w`). Each profile MUST define weights for `intent_vs_params`, `intent_vs_user_query`, `intent_vs_history`, and `holistic`. A `default` profile MUST exist as fallback.

#### Scenario: Config contains dimension profiles
- **WHEN** reading `configs/training_config.yaml`
- **THEN** a `dimension_profiles` key exists with entries for `OPI`, `DPI`, `harmful`, `injection`, `deception`, and `default`

#### Scenario: Each profile has four dimension weights
- **WHEN** reading any profile under `dimension_profiles`
- **THEN** it contains `intent_vs_params`, `intent_vs_user_query`, `intent_vs_history`, and `holistic` keys, each with a float value between 0.0 and 1.0

### Requirement: SFT scores differ by dimension based on attack type
`prepare_sft_data()` SHALL compute each dimension's score as `1.0 - risk_level * w` where `w` is the weight from the matching dimension profile. Different attack types MUST produce different score distributions across the four dimensions.

#### Scenario: OPI attack produces high contradiction in params and history
- **WHEN** generating SFT data for a sample with `attack_type=OPI` and `risk_level=1.0`
- **THEN** `intent_vs_params.score` and `intent_vs_history.score` are low (< 0.3)
- **THEN** `intent_vs_user_query.score` is high (> 0.7)

#### Scenario: DPI attack produces high contradiction in user query
- **WHEN** generating SFT data for a sample with `attack_type=DPI` and `risk_level=1.0`
- **THEN** `intent_vs_user_query.score` is low (< 0.3)
- **THEN** `intent_vs_params.score` is high (> 0.5)

#### Scenario: Deceptive intent produces high contradiction in params
- **WHEN** generating SFT data for a sample with `is_deceptive_intent=True` and `risk_level=1.0`
- **THEN** `intent_vs_params.score` is low (< 0.3)
- **THEN** `intent_vs_user_query.score` is high (> 0.7)

#### Scenario: Benign sample has uniformly high scores
- **WHEN** generating SFT data for a sample with `attack_type=none` and `risk_level=0.0`
- **THEN** all four dimension scores are 1.0

#### Scenario: Unknown attack type falls back to default profile
- **WHEN** generating SFT data for a sample with an unrecognized `attack_type`
- **THEN** the `default` profile is used (all weights = 1.0)

### Requirement: Contradictions are dimension-specific
The `contradictions` field in each dimension's SFT label SHALL contain a description specific to that dimension and attack type, not a copy of the generic `reason`. Contradictions SHALL only be populated when the dimension score is below 0.5.

#### Scenario: Low-score dimension has specific contradiction
- **WHEN** a dimension score is below 0.5 for an OPI attack
- **THEN** the `contradictions` list contains a description mentioning the specific dimension mismatch (e.g., "Tool parameters suggest injected instruction, not declared intent")

#### Scenario: High-score dimension has empty contradictions
- **WHEN** a dimension score is 0.5 or above
- **THEN** the `contradictions` list is empty

### Requirement: Existing tests updated for differentiated scores
`test_prepare_sft_data` in `tests/test_training.py` SHALL verify that SFT output contains differentiated scores across dimensions, not uniform values.

#### Scenario: Test validates score differentiation
- **WHEN** running `python -m unittest tests.test_training -v`
- **THEN** all tests pass including updated `test_prepare_sft_data`
