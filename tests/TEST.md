# Test inventory and review

[← Documentation home](../docs/README.md) · [Testing strategy and gates](../docs/maintainers/engineering/testing.md) · [Security policy](../SECURITY.md)

This inventory explains every test in `tests/` and `site/tests/`. Keep tests that protect publication accuracy, canonical state, source-access safety, recovery, privacy, or a usable product journey. Small tests can protect important boundaries; size and test count are not measures of value.

Each table row identifies a test function or website test title. A parameterized row covers **all** its cases; its explanation identifies the varied evidence or failure paths. Helpers, fixtures, optional benchmarks, and the gated live test are listed separately. Update this inventory whenever a test's purpose or location changes.

Before consolidating or removing a test, compare its setup, assertions, and protected behavior with the implementation and neighboring coverage. Preserve source-access interlocks, coverage thresholds, and lifecycle rules. The [testing guide](../docs/maintainers/engineering/testing.md#what-earns-a-test) owns test strategy, layer selection, execution commands, and platform requirements.

## Contents

- [Python integration tests](#python-integration-tests)
- [Python unit and tooling tests](#python-unit-and-tooling-tests)
- [Website unit tests](#website-unit-tests)
- [Website HTTP and browser tests](#website-http-and-browser-tests)
- [Fixtures and optional checks](#fixtures-and-optional-checks)

## Python integration tests

### Availability

Source: [integration/test_availability.py](integration/test_availability.py).

| Test | Behavior protected |
|---|---|
| `test_availability_audit_checks_every_row_deletes_only_explicit_unavailability` | Audit open and closed rows; reopen explicit availability, delete explicit absence, preserve inconclusive rows and their provenance |
| `test_availability_audit_includes_manual_jobs_without_provenance` | Manual listings are audited even without a search association |
| `test_delayed_audit_cannot_delete_newer_rediscovery` | A delayed audit cannot delete a newer observation or reopen a later closure; stale absence still advances scheduling |
| `test_availability_distinguishes_public_listing_301s_from_source_stops` | Public 301 is inconclusive and permits unrelated work; detail redirects, denials, and challenges stop subsequent requests without mutating unchecked rows |
| `test_concurrent_audit_keeps_inflight_evidence_but_stops_new_requests_after_denial` | Already-started 200/404 evidence is preserved while a sibling denial stops queued work |
| `test_availability_errors_are_not_closure_evidence_except_not_found_or_gone` | At either endpoint, only 404/410 deletes; other statuses and unexpected failures preserve state |

Source: [integration/test_availability_schedule.py](integration/test_availability_schedule.py).

| Test | Behavior protected |
|---|---|
| `test_700_jobs_rotate_across_20_daily_runs` | A 700-row backlog rotates completely in 14 days at 50 jobs per run, resumes oldest-first on day 15, and respects minimum intervals across 20 runs |
| `test_new_jobs_and_deferred_denials_recover_without_starvation` | Denials leave blocked/deferred rows eligible; new jobs outrank checked rows and inconclusive checks drain the growing backlog without lifecycle changes |
| `test_interrupted_audit_does_not_stamp_completed_or_unprocessed_jobs` | Cancellation before the atomic write leaves all audit timestamps and lifecycle state unchanged |
| `test_verified_snapshot_restores_audit_rotation` | A verified SQLite snapshot retains timestamps and restores the exact next batch and backlog |
| `test_due_boundary_and_ordering_do_not_use_discovery_timestamps` | Never-checked and oldest-checked rows take priority; the five-day boundary is inclusive and discovery does not postpone the audit |
| `test_attempts_rotate_without_changing_inconclusive_lifecycle_or_stamping_denials` | Inconclusive attempts advance only scheduling metadata; denials and deferred rows do not advance |
| `test_inconclusive_and_confirmed_outcomes_cannot_overlap` | Contradictory evidence fails before lifecycle or scheduling writes |
| `test_no_due_jobs_produces_no_requests_and_audit_timestamps_are_monotonic` | No due work issues no requests; stale attempts cannot move the schedule backwards |

### CLI

Source: [integration/test_cli.py](integration/test_cli.py).

| Test | Behavior protected |
|---|---|
| `test_scrape_quality_gate_end_to_end` | Full, warning, blocking, timeout-partial, HTTP 429 partial (including completed empty searches and blocking drift), source-denied, failed, and selected-search runs produce distinct exits, sanitized reports, uncontaminated baselines, and safe publication decisions |
| `test_rate_limited_partial_requires_quality_gate` | HTTP 429 completed work cannot render without the mandatory quality report |
| `test_validation_rejects_foreign_key_inconsistency_without_private_diagnostics` | A synthetic broken run-to-search reference blocks validation without exposing private diagnostic values |
| `test_requested_quality_gate_fails_closed_on_local_errors` | Baseline read, analysis, report write, and persistence errors stop publication and do not disclose private diagnostics |
| `test_availability_source_block_fails_closed_without_rendering` | Source blocks and `--no-render` preserve projections; inconclusive nonblocked audits may render with a partial-success exit |
| `test_availability_public_listing_301_returns_partial_success_and_continues` | Full CLI/transport/repository path preserves the redirected row, continues other checks, sanitizes output, and validates projections |
| `test_availability_denial_preserves_confirmed_state_but_never_refreshes_existing_projections` | A denial, including failing stream cleanup, preserves earlier confirmed changes but withholds all publication and leaves inconclusive provenance untouched |
| `test_database_render_stats_and_validate_commands` | Unmigrated state is rejected; upgrade/render/export/stats/validate cooperate; stale registry counts and metadata fail validation without silent repair |
| `test_controlled_insertion_and_removal_require_projection_regeneration` | Repository lifecycle changes make projections stale until the renderer refreshes them |
| `test_searches_works_without_database` | Configuration discovery is usable without creating SQLite |
| `test_database_engine_is_disposed_when_migration_check_fails` | Every database command releases its engine and preserves migration exit status even if cleanup fails |
| `test_scrape_preserves_unexpected_migration_error` | Unexpected migration errors remain diagnosable and still release the engine |
| `test_searches_disposes_engine_when_database_inspection_fails` | The optional database-inspection path releases resources without replacing its failure |
| `test_repository_construction_failure_disposes_engine` | Session-factory construction failures cannot leak an engine or be hidden by cleanup |
| `test_disposal_failure_does_not_replace_command_error` | The operational error survives a second cleanup failure |
| `test_collection_commands_require_permission_even_when_dotenv_enables_it` | An explicit false environment authorization defeats dotenv and stops all collection entry points before database creation |
| `test_configuration_errors_are_sanitized_before_database_access` | Invalid SQLite/non-SQLite settings produce a safe configuration error, not credentials or a traceback |
| `test_unknown_search_is_rejected_without_network` | Mistyped/disabled search selection fails before source access |
| `test_add_job_persists_and_renders_without_authorization_or_network` | Offline manual insertion validates identity and offset timestamps, renders public projections, and invents no collection history |
| `test_add_job_reports_persisted_changes_without_rendering` | Added, updated, and unchanged messages agree with real persisted rows; repeated writes keep one identity and create no projections or collection runs |
| `test_add_job_rejects_invalid_input` | Unsafe URLs, unsupported values, policy conflicts, ambiguous/future timestamps, and oversized text fail before writes without echoing private input |
| `test_add_jobs_persists_three_and_renders_without_network` | A reviewed batch is persisted and published offline with correct counts and no invented collection history |
| `test_add_jobs_no_render_only_updates_sqlite` | Batch insertion honors the SQLite-only mode |
| `test_add_jobs_rejects_bad_batch_before_writing` | Empty/oversized batches, invalid later rows, unknown/missing fields, duplicate IDs/JSON keys, types, timestamps, nesting, and size limits reject the whole input without writes |

### README projection

Source: [integration/test_readme.py](integration/test_readme.py).

| Test | Behavior protected |
|---|---|
| `test_readme_contains_type_sections_and_escapes_values` | Counts, collection time, both employment sections, escaped table values, rendering, and validation agree |
| `test_readme_preview_is_bounded_to_five_opportunities_per_type` | Only the five newest rows of each type appear, with truthful full counts |
| `test_review_seal_detects_changes_beyond_preview_and_exact_timestamps` | Off-preview public edits and microsecond changes alter the seal; private lifecycle-only edits do not; malformed seals fail |
| `test_readme_rejects_reversed_generated_markers` | Invalid region ownership fails before rendering can overwrite the document |
| `test_empty_database_still_renders_both_table_headers` | An empty projection remains a valid two-section table with zero counts and no invented collection time |

### Repository

Source: [integration/test_repository.py](integration/test_repository.py). All cases use migrated disposable SQLite.

| Test | Behavior protected |
|---|---|
| `test_overlapping_search_timestamps_remain_monotonic` | Older observations cannot regress first/last/updated timestamps or erase optional metadata; both searches retain health records |
| `test_newer_rediscovery_updates_fields_and_preserves_missing_optional_metadata` | New evidence updates changed fields; missing optional values preserve known facts; unchanged rediscovery advances last-seen but not updated-at |
| `test_overlapping_search_404_cannot_override_a_newer_valid_observation` | A late-finishing search's older absence cannot accumulate closure evidence against fresher availability |
| `test_slow_search_early_valid_detail_cannot_reopen_after_later_404` | Search start, not finish time, governs reopening; stale discoveries create no new provenance |
| `test_stale_observations_cannot_overwrite_metadata_or_newer_closure` | Older same-search metadata/absence cannot change current facts or undo confirmed closure |
| `test_distinct_linkedin_ids_are_not_fuzzy_merged_and_explicit_404s_close` | Identical display fields with different IDs remain separate; confirmations close only the referenced ID |
| `test_open_jobs_with_identical_display_fields_use_identifier_order` | Open-row order is deterministic regardless of insertion order |
| `test_manual_upsert_preserves_lifecycle_metadata_and_adds_no_provenance` | Manual writes preserve immutable/monotonic timestamps and optional facts, cannot reopen closed rows, and do not invent search history |
| `test_manual_insert_bounds_future_posting_time_by_observation` | Future posting evidence cannot make first-seen later than observation |
| `test_manual_batch_rolls_back_when_later_job_is_closed` | A later forbidden reopening rolls back earlier valid inserts in the same batch |
| `test_manual_batch_rejects_duplicate_identity_without_writing` | Duplicate IDs fail before any batch row is persisted |
| `test_repository_persists_run_and_provenance_timestamps_in_utc` | Positive/negative timezone offsets normalize across search definitions, runs, provenance, stats, and closure |
| `test_absence_and_one_closed_search_cannot_close_another_search_active_job` | Search associations isolate closure; disappearance is not evidence, rediscovery resets confirmations, and reopening preserves first-seen |
| `test_search_sync_preserves_retired_history_without_closing_jobs` | Renamed/retired search definitions update configuration without deleting history or closing jobs |
| `test_failed_search_transaction_rolls_back_earlier_job_and_provenance_writes` | A real SQLite failure rolls back earlier updates, inserts, run history, and provenance; subsequent writes still work |
| `test_contradictory_availability_evidence_fails_without_writes` | The same ID cannot be simultaneously available and unavailable |
| `test_manual_batch_bounds_fail_before_any_write` | Zero and eleven rows are rejected at the repository boundary, independently of the CLI |
| `test_data_quality_baseline_rejects_non_integer_schema_versions` | Boolean/float schema versions cannot enter persisted baseline history |
| `test_data_quality_baselines_are_aggregate_bounded_and_newest_first` | History retains 90 observations, reads five newest with stable ties, rejects oversized payloads, and cannot be displaced by late old writes |

### Collection pipeline

Source: [integration/test_runner.py](integration/test_runner.py).

| Test | Behavior protected |
|---|---|
| `test_pipeline_filters_persists_and_isolates_failed_searches` | Valid sibling work commits while timeout, source denial, malformed, or unexpected search failures leave prior jobs and near-closure provenance untouched; diagnostics are sanitized |
| `test_collection_uses_explicit_cycle_when_posting_age_is_missing` | Real parsing/classification persists explicit-cycle roles but rejects yearless roles without date evidence |
| `test_malformed_detail_does_not_publish_a_current_search_card` | A plausible card cannot substitute for missing detail identity or produce a successful collection |
| `test_concurrent_search_outcomes_apply_in_observation_order` | Reversed fetched outcomes still persist the newest metadata and both search associations |
| `test_equal_finish_times_keep_configured_search_order` | Equal timestamps are deterministic by configured order, not random run IDs |
| `test_targeted_run_keeps_full_registry_enabled` | Selecting one search does not retire its configured siblings |
| `test_search_preview_classifies_without_persisting` | Injected and owned-fetcher preview paths classify but leave jobs, stats, and provenance unchanged |
| `test_empty_search_selection_fails_before_persistence` | Empty collection input cannot silently succeed or change state |
| `test_normalized_oversize_location_is_excluded_without_losing_valid_jobs` | Normalization overflow excludes only the invalid candidate, not the valid search results |

### Partial collection and search rotation

Source: [integration/test_partial_collection.py](integration/test_partial_collection.py).

| Test | Behavior protected |
|---|---|
| `test_early_mid_late_source_stop_retains_only_completed_searches` | Early/mid/late search/detail 429, 401, 403, redirect, and challenge responses stop without retries or subsequent requests; only completed searches persist, and only qualifying 429 results are eligible with no baseline |
| `test_mixed_inflight_denials_never_qualify_for_partial_publication` | Concurrent HTTP 429 cannot mask challenge, authentication, or redirect denials, including failed stream cleanup; completed siblings remain in SQLite but publication and baselines stay blocked without subsequent requests |
| `test_multi_day_rotation_survives_snapshots_and_discarded_interruptions` | Fourteen daily partial runs cover seven searches fairly across verified snapshots; cancelled disposable executions cannot advance durable rotation |
| `test_rotation_handles_registry_changes_and_full_recovery` | New/removed/disabled/re-enabled/modified searches and editorial edits compose deterministically with rotation and later full success |

## Python unit and tooling tests

Some historically named `unit/` files exercise real files, migrations, or shell processes. Their scope remains the named subsystem, not necessarily an in-memory unit.

### Classification

Source: [unit/test_classification.py](unit/test_classification.py).

| Test | Behavior protected |
|---|---|
| `test_explicit_2027_software_internship_is_accepted` | Clear internship evidence produces the expected type and technical category |
| `test_cycle_must_be_explicit_and_not_only_graduation_year` | Internship eligibility years in titles or descriptions are not programme-cycle evidence |
| `test_new_grad_graduation_year_is_cycle_evidence` | New Grad eligibility has different semantics: an explicit wrong graduation cycle defeats recent posting evidence |
| `test_missing_cycle_is_accepted_for_recent_posting` | Yearless New Grad roles may qualify at the exact posting-date floor |
| `test_wrong_cycle_is_excluded` | Wrong-cycle internships and New Grad roles remain excluded despite recent posting |
| `test_conflicting_cycle_evidence_is_rejected` | Multiple conflicting title or contextual body years cannot be guessed into the target cycle |
| `test_program_year_is_not_mistaken_for_graduation_eligibility` | Programme start years remain authoritative negative evidence |
| `test_canonical_2025_2026_graduate_listing_is_rejected` | A representative multi-year graduate description rejects the old cycle even with a recent posting |
| `test_full_time_title_is_rejected_even_if_description_mentions_internships` | Company internship boilerplate cannot turn a full-time title into an opportunity |
| `test_explicit_2027_new_grad_role_is_accepted` | University Graduate title evidence produces New Grad and the expected category |
| `test_title_with_both_types_is_categorized_as_internship` | Internship evidence takes precedence over the word graduate |
| `test_senior_opportunity_title_is_excluded` | Explicit seniority disqualifies both internship and New Grad titles |
| `test_non_technology_title_cannot_be_rescued_by_technical_description` | Technical team mentions cannot reclassify an explicitly unrelated finance title |
| `test_employment_type_requires_whole_word_evidence` | “International” and “Internal” do not count as “intern” |
| `test_explicit_non_european_locations_prevent_city_fallback` | Country names/codes, regional abbreviations, city namesakes, and explicit non-European remote evidence defeat European-city fallback |
| `test_explicit_european_locations_remain_eligible` | European codes, recognized cities, and explicit European entries within mixed/EMEA locations remain eligible |
| `test_description_can_classify_generic_technical_internship` | A generic technical title may use explicit description evidence for its category |
| `test_conflicting_years_cannot_fall_back_to_recent_posting_dates` | Past/future years across title/body evidence and both types cannot disappear into the date fallback |
| `test_title_precedence_and_internship_eligibility_remain_distinct` | Target-cycle titles beat historical body mentions; distant eligibility years do not override valid internship evidence |
| `test_supported_target_cycles_need_no_posting_date` | Boundary target cycles throughout the supported range work with explicit title evidence |
| `test_posting_floor_uses_the_utc_instant` | Both types respect the exact UTC cutoff, including equivalent positive/negative offsets and adjacent microseconds |
| `test_explicit_separate_european_location_survives_a_mixed_country_list` | Separate European and non-European locations do not incorrectly qualify each other |
| `test_missing_or_ambiguous_geography_is_not_assumed_european` | Empty locations, Remote, and EMEA alone fail with the stable ambiguity reason |

### Configuration and domain inputs

Sources: [unit/test_config.py](unit/test_config.py), [unit/test_models.py](unit/test_models.py), [unit/test_url.py](unit/test_url.py), and [unit/test_paths.py](unit/test_paths.py).

| Test | Behavior protected |
|---|---|
| `test_production_search_registry_is_bounded_and_scope_specific` | Checked-in role/company/country searches preserve query scope, date windows, allowlists, geo IDs, and request/recheck bounds |
| `test_dotenv_loads_automatically_and_process_environment_wins` | Local dotenv defaults load while explicit environment settings win, including relative export paths |
| `test_availability_environment_overrides_and_defaults` | Operator caps of 50, 100, and legacy 250 override defaults; absent settings retain the five-day interval and 50-job cap |
| `test_availability_limits_reject_unbounded_values` | Invalid intervals and batch limits fail before collection |
| `test_search_text_normalization_includes_optional_notes` | Whitespace-normalized search inputs are stable instead of changing queries or recorded scope accidentally |
| `test_trailing_environment_whitespace_is_ignored` | Trailing deployment-setting whitespace does not misparse an explicit authorization value |
| `test_global_search_limits_override_yaml_values` | Operator page/result/recheck bounds override per-search configuration |
| `test_invalid_search_and_duplicate_query_are_rejected` | Invalid slugs and duplicate effective queries fail before collection |
| `test_duplicate_query_identity_ignores_company_allowlist_order` | Reordering a company allowlist cannot bypass duplicate detection |
| `test_settings_and_classification_yaml_fail_closed` | Malformed YAML and invalid rule-list shapes are rejected, not defaulted silently |
| `test_settings_require_sqlite_and_safe_header_values` | Non-SQLite storage and header-control injection cannot enter settings |
| `test_configuration_errors_do_not_echo_invalid_values` | Validation errors omit credentials embedded in invalid database URLs |
| `test_settings_precedence_is_defaults_dotenv_yaml_then_environment` | All four settings layers compose correctly and leave source authorization false unless explicitly enabled |
| `test_false_authorization_values_never_enable_source_access` | Supported false spellings remain false |
| `test_discovered_job_rejects_non_string_text_fields` | Canonical job input rejects null/non-string required text |
| `test_raw_job_rejects_non_string_locations` | Malformed location items cannot cross the parser-model boundary |
| `test_job_models_canonicalize_listing_urls_consistently` | Raw and discovered models strip tracking and normalize the same identity URL |
| `test_job_models_normalize_naive_timestamps_to_utc` | Raw, discovered, and stored model boundaries consistently interpret naive timestamps as UTC |
| `test_public_url_canonicalization_removes_tracking_and_normalizes_host` | Tracking/fragments/default ports are removed while meaningful query parameters retain deterministic order |
| `test_public_url_canonicalization_rejects_unsafe_targets` | Non-HTTPS, local/internal, malformed-host, and script URLs are rejected |
| `test_linkedin_listing_url_must_match_the_canonical_job_id` | Safe-looking links with another job's ID cannot be persisted as the listing URL |
| `test_linkedin_job_id_is_extracted_only_from_a_valid_listing_url` | IDs are extracted from actual listing URLs, not arbitrary company paths |
| `test_find_project_root_is_independent_of_directory_depth` | Resource discovery survives repository renaming and deeper module layouts |

### Concurrency and logging

Sources: [unit/test_concurrency.py](unit/test_concurrency.py) and [unit/test_logging.py](unit/test_logging.py).

| Test | Behavior protected |
|---|---|
| `test_concurrent_map_bounds_workers_and_preserves_input_order` | Active workers never exceed the configured bound and output follows input order |
| `test_concurrent_map_rejects_an_invalid_limit` | Zero/negative concurrency fails rather than hanging or spawning unbounded work |
| `test_concurrent_map_cleans_up_running_workers_after_failure_or_cancellation` | Failure/cancellation drains running work and does not start queued items; event handshakes avoid timing guesses |
| `test_concurrent_map_handles_empty_input_and_none_results` | Empty work invokes nothing; valid `None` results are not mistaken for missing outputs |
| `test_json_formatter_emits_only_approved_structured_fields` | Structured logging drops unapproved response-body fields |
| `test_json_formatter_does_not_emit_exception_messages_or_tracebacks` | Logs identify exception type without leaking sensitive exception detail |

### HTTP transport

Source: [unit/test_http.py](unit/test_http.py). All requests use mocks or the offline guard.

| Test | Behavior protected |
|---|---|
| `test_linkedin_http_is_blocked_without_explicit_authorization` | Default settings cannot issue source requests |
| `test_http_fetcher_rejects_non_linkedin_or_non_https_urls_without_network` | Host, scheme, userinfo, port, identity, path, query, and fragment boundaries reject unapproved endpoints before transport |
| `test_http_fetcher_disables_redirects_on_an_injected_client` | Even a redirect-following injected client cannot leave the approved endpoint |
| `test_public_listing_301_is_inconclusive_without_following_reading_or_retrying` | Missing/malformed/untrusted destinations and stream-cleanup failures stay inconclusive, sanitized, unread, unretried, and do not block unrelated requests |
| `test_public_listing_301_exception_does_not_relax_other_source_stops` | The narrow public-301 exception never applies to guest endpoints, other redirects, authentication denials, or rate limits |
| `test_http_fetcher_retries_transient_linkedin_response` | A transient 503 can recover within the configured retry budget |
| `test_http_fetcher_caps_exponential_backoff` | Repeated transient failures use bounded attempts and capped delays |
| `test_http_fetcher_stops_on_429_without_reading_response_body` | Retry-After does not authorize retrying a source rate-limit denial or reading its body |
| `test_response_cleanup_cannot_hide_a_detected_source_denial` | Timeout/transport/unexpected close errors cannot replace denial classification, cause retries, or leak detail, including after exhausted transient retries |
| `test_unexpected_client_failure_without_a_denial_is_preserved` | Unexpected client failures are not mislabeled as denial evidence |
| `test_redirect_or_access_denial_stops_queued_and_later_requests` | A denial stops already-pacing and future requests, not just the caller that observed it |
| `test_challenge_page_stops_queued_and_later_requests` | HTTP-success challenge HTML enforces the same stop boundary |
| `test_http_fetcher_never_retains_or_sends_source_cookies` | Response cookies cannot create an authenticated follow-up request |
| `test_http_fetcher_rejects_preconfigured_cookie_header` | Injected session cookies are rejected before use |
| `test_owned_http_client_ignores_ambient_https_proxy` | Owned clients disable ambient transport configuration and still discard cookies |
| `test_http_fetcher_rejects_non_html_response` | JSON responses cannot silently become guest HTML evidence |
| `test_http_fetcher_enforces_response_size_limit` | Declared oversized bodies fail the response limit |
| `test_http_fetcher_stops_streaming_at_response_size_limit` | Undeclared oversized streams stop at the bound and close without consuming later chunks |
| `test_injected_http_clients_must_remain_unauthenticated` | Authorization headers, proxy authorization, and client auth are rejected without requests |
| `test_response_bounds_apply_before_decompression` | Gzip/deflate/unknown encodings are rejected before decoding; identity remains usable and explicitly requested |
| `test_transport_failures_have_bounded_retries_and_sanitized_errors` | Timeout/connect failures exhaust bounded retries with stable safe diagnostics |

### LinkedIn parsing and bounded discovery

Source: [unit/test_linkedin.py](unit/test_linkedin.py).

| Test | Behavior protected |
|---|---|
| `test_linkedin_search_page_parser_extracts_stable_cards` | Guest cards yield numeric identities, company evidence, and canonical links |
| `test_search_page_accepts_empty_guest_fragments` | Legitimate empty fragments are distinguished from malformed nonempty responses |
| `test_search_page_rejects_unrecognized_nonempty_documents` | Sign-in/generic documents cannot masquerade as successful empty searches |
| `test_linkedin_search_page_rejects_more_than_one_page_of_cards` | An oversized page cannot evade the 25-card bound |
| `test_closed_application_notice_uses_semantic_alert_instead_of_hashed_classes` | Explicit semantic closure alerts survive unstable source class names |
| `test_closed_application_notice_supports_guest_page_markup` | Guest closure markup remains recognized independently of the public-page form |
| `test_closed_application_words_outside_an_alert_do_not_close_job` | Description text mentioning closure is not closure evidence |
| `test_linkedin_job_detail_parser_extracts_description` | Detail identity, description, start date, and explicit industries survive parsing |
| `test_current_search_card_cannot_supply_missing_detail_identity` | Empty/partial detail pages cannot borrow title or company from a current card |
| `test_linkedin_job_detail_infers_posted_at_from_relative_age` | Relative posting age is anchored to the injected observation clock |
| `test_lower_bound_posting_age_is_not_treated_as_exact_recency` | “30+ days” cannot invent a precise eligible date |
| `test_unbounded_relative_posting_age_is_not_treated_as_exact_evidence` | Huge relative ages cannot overflow or become trusted dates |
| `test_linkedin_job_detail_extracts_criteria_without_linkedin_classes` | Semantic criteria labels work without source-specific CSS classes |
| `test_linkedin_job_detail_does_not_infer_industries_from_description` | Unstructured prose cannot invent structured industry metadata |
| `test_linkedin_job_detail_does_not_treat_graduation_date_as_start_date` | Candidate graduation dates are not advertised start dates |
| `test_linkedin_scraper_paginates_and_deduplicates_job_ids` | Bounded pages deduplicate identity/detail requests, prefilter unrelated titles, and distinguish workplace type from industries |
| `test_concurrent_searches_share_an_inflight_detail_request` | Overlapping searches do not duplicate simultaneous detail traffic |
| `test_completed_detail_requests_are_not_retained_between_scrapes` | Later scrapes fetch fresh evidence instead of reusing completed response bodies |
| `test_cycle_search_url_covers_every_posting_since_may_cutoff` | Search URL date windows cover the full eligible posting interval |
| `test_title_prefilter_selects_new_grad_cards` | New Grad titles reach detail fetching rather than being lost by an internship-only prefilter |
| `test_title_prefilter_continues_to_later_search_pages` | A page of unrelated titles does not prematurely end bounded discovery |
| `test_linkedin_scraper_leaves_cycle_and_posting_evidence_to_classifier` | The scraper forwards candidates on both sides of the posting floor instead of duplicating acceptance policy |
| `test_linkedin_company_filter_is_applied_before_detail_fetch` | Company scope prevents unnecessary detail requests |
| `test_stale_search_card_detail_404_confirms_known_job_unavailability` | A stale visible card does not negate explicit known-job absence |
| `test_known_job_recheck_requires_identity_in_the_detail_response` | Malformed rechecks remain inconclusive and cannot synthesize availability from stored identity |
| `test_known_job_404_is_reported_as_confirmed_unavailable` | Bounded rechecks report explicit absence even when the job is not on the search page |
| `test_linkedin_access_challenge_is_rejected` | Parser-level challenge detection cannot become valid search results |
| `test_detail_challenge_stops_later_details_and_searches` | A real fetcher/parser combination propagates a detail challenge across the remaining source work |
| `test_cancelled_search_does_not_leave_unhandled_detail_failures` | Abandoned shared detail failures are retrieved instead of becoming unhandled task errors |
| `test_cancelling_one_search_preserves_the_other_shared_detail_waiter` | Cancelling one waiter does not cancel another's successful or failed shared request |

### Collection quality

Source: [unit/test_data_quality.py](unit/test_data_quality.py).

| Test | Behavior protected |
|---|---|
| `test_first_observation_builds_a_sanitized_baseline_without_false_alerts` | Warm-up produces aggregate-only history, no raw listings, and no invented drift |
| `test_report_identifies_partial_registry_scope` | Partial registry observations are labeled and cannot become full baselines |
| `test_acceptance_rate_uses_classified_records_not_search_card_count` | Rechecks do not distort the acceptance-rate denominator |
| `test_eighty_percent_candidate_volume_drop_warns_but_does_not_block` | A large volume drop warns without being confused with acceptance drift |
| `test_all_searches_returning_zero_after_a_productive_baseline_blocks` | A productive registry becoming empty blocks publication |
| `test_search_configuration_change_resets_its_drift_baseline` | Changed effective queries do not compare with incompatible prior evidence |
| `test_extreme_acceptance_and_parser_field_missingness_are_reported` | Severe acceptance and parser regressions trigger the appropriate findings/block |
| `test_category_country_and_optional_field_distribution_shifts_are_reported` | Disappearing categories, changed geography, and lost optional metadata remain visible |
| `test_country_distribution_warns_when_country_codes_disappear` | Losing all concrete country evidence is not treated as a stable distribution |
| `test_moderate_optional_field_missing_jump_is_reported_against_baseline` | Relative missingness drift is detected below the absolute high threshold |
| `test_moderate_parser_field_missing_jump_is_reported_against_baseline` | Parser-field drift uses comparable history even below the high threshold |
| `test_stable_absolute_field_missingness_does_not_repeat_alerts` | A stable known absence of optional/parser fields does not generate perpetual alarms |
| `test_missing_field_comparisons_require_sampled_history` | Empty historical samples cannot establish misleading missingness baselines |
| `test_malformed_snapshots_are_ignored_and_reported` | Unreadable history produces a safe finding without a false publication block |
| `test_acceptance_thresholds_in_both_directions` | Adjacent warning/block thresholds apply to rises and drops, and blocking observations do not become baselines |
| `test_empty_search_warms_up_without_premature_blocking` | Zero, one, and two historical observations are insufficient to condemn an empty search |
| `test_candidate_volume_above_drop_threshold_does_not_warn` | The adjacent safe boundary and stable/growing volumes remain quiet |
| `test_small_acceptance_samples_do_not_trigger_a_block` | Too-small current or historical populations cannot justify acceptance drift |
| `test_scraper_warning_frequency_is_bounded_and_sanitized` | Warning thresholds and rates remain bounded and exclude raw warning text |
| `test_editorial_search_changes_preserve_drift_detection` | Renaming/describing a search cannot reset its substantive quality history |
| `test_partial_and_failed_searches_do_not_create_baselines_or_fake_zero_metrics` | Failure is not zero discovery; partial populations never compare as complete-registry samples |
| `test_changed_registry_does_not_compare_incompatible_profiles` | Registry geography changes reset incompatible aggregate comparisons |
| `test_only_recent_nonfuture_baselines_can_block` | Thirty-day boundary, expired history, and future snapshots are handled conservatively |
| `test_invalid_baselines_cannot_influence_or_leak_into_reports` | Invalid versions, timestamps, counts, categories, countries, shapes, and extra fields fail validation without leaking their contents |
| `test_baseline_parsing_is_bounded` | Deep nesting, excess bytes, null, and array roots cannot enter baseline analysis |
| `test_report_and_snapshot_are_deterministic_and_history_is_bounded` | Input row order does not affect output and history inspection stops at five payloads |

### Migrations and public exports

Sources: [unit/test_migrations.py](unit/test_migrations.py) and [unit/test_public_exports.py](unit/test_public_exports.py).

| Test | Behavior protected |
|---|---|
| `test_repeated_upgrade_preserves_schema_and_existing_data` | Reapplying head is byte-preserving and retains configured state |
| `test_upgrade_database_creates_a_missing_sqlite_parent` | Fresh setup can initialize nested database paths |
| `test_employment_type_migration_backfills_existing_jobs` | Historical employment types migrate to valid nonnullable values |
| `test_canonical_state_migration_preserves_rows_and_rejects_invalid_state` | Historical jobs/runs/provenance survive constraints and the additive quality revision; invalid lifecycle/count/time updates fail and foreign keys remain valid |
| `test_search_rotation_migration_preserves_history_and_round_trips` | Additive scheduling migration preserves search state, initializes null timestamps, and upgrades/downgrades without foreign-key damage |
| `test_availability_migration_preserves_prior_rows_and_round_trips` | Existing jobs survive upgrade/downgrade, scheduling starts null, and foreign keys remain valid |
| `test_public_exports_include_only_approved_fields_in_stable_order` | Open-only ordered CSV/JSON, Unicode, metadata allowlists/counts/hashes, and shared schemas agree; missing files are reported |
| `test_public_csv_neutralizes_formulas_and_validation_detects_stale_files` | Every spreadsheet-dangerous prefix in every free-text column is neutralized without altering JSON; stale exports invalidate both content and metadata |
| `test_export_schema_and_metadata_validation_rejects_tampering` | Wrong counts, non-UTC time, extra private fields, CSV headers, and stale totals fail; an empty dataset still validates |
| `test_api_timestamp_contract_rejects_trailing_whitespace` | Python JSON Schema rejects newline/space/Unicode-line suffixes in API/status timestamps despite regex end-anchor differences |
| `test_documented_examples_match_all_public_v1_contracts` | Checked-in and documented CSV/JSON/API/status examples conform and agree on identities, counts, dates, and download hashes |

### Snapshots and bootstrap

Sources: [unit/test_snapshots.py](unit/test_snapshots.py) and [unit/test_bootstrap_sqlite.py](unit/test_bootstrap_sqlite.py).

| Test | Behavior protected |
|---|---|
| `test_snapshot_manifest_captures_recovery_metadata` | Verified bundles describe schema, collection time, immutable key, size, hash, and retention accurately |
| `test_snapshot_from_live_wal_is_cold_and_sidecar_free` | Committed WAL-only rows survive backup into a standalone rollback-journal database |
| `test_snapshot_links_to_previous_immutable_objects` | Recovery lineage refers to the previous verified immutable bundle |
| `test_snapshot_creation_rejects_a_missing_previous_manifest` | Missing lineage is not silently discarded |
| `test_snapshot_verification_rejects_tampered_database` | Both size-changing and same-size corruption fail verification |
| `test_snapshot_manifest_requires_timezone_aware_timestamps` | Ambiguous manifest time cannot enter recovery state |
| `test_snapshot_manifest_rejects_unknown_fields` | Unapproved manifest metadata is rejected rather than silently trusted |
| `test_snapshot_never_deletes_source_matching_old_staging_names` | A source named like a historical temporary file remains untouched |
| `test_snapshot_preserves_other_operations_staging_files` | Another operation's temporary files are not owned by this snapshot |
| `test_failed_snapshot_preserves_outputs_it_did_not_publish` | Failure after preflight cannot delete output claimed by another operation |
| `test_partial_snapshot_promotion_cleans_only_owned_files` | Interrupted manifest promotion cleans this operation's files, never the source |
| `test_snapshot_rejects_source_sidecar_outputs` | Neither database nor manifest output may overwrite source WAL/SHM/journal paths |
| `test_snapshot_validates_manifest_limits_before_writing` | Boolean/fractional counts, oversized keys, and retention overflow fail before touching source/output |
| `test_manifest_read_rejects_oversized_bytes` | Manifest input obeys its byte bound |
| `test_manifest_rejects_duplicate_root_and_nested_fields` | Duplicate JSON keys cannot create ambiguous manifest meaning |
| `test_manifest_timestamp_overflow_is_a_validation_error` | Extreme timestamp/offset arithmetic fails safely |
| `test_snapshot_rejects_dangling_output_symlinks` | A dangling output alias is preserved and never followed/overwritten |
| `test_bootstrap_fails_when_source_is_missing` | Bootstrap fails without creating a source or emitting fake database bytes |
| `test_bootstrap_stream_includes_committed_wal_rows` | The actual bootstrap subprocess streams a complete cold backup, including live WAL rows |

### Deployment, restore, and snapshot publication

Sources: [unit/test_activate_release.py](unit/test_activate_release.py), [unit/test_deploy_shell.py](unit/test_deploy_shell.py), [unit/test_restore_shell.py](unit/test_restore_shell.py), [unit/test_snapshot_store_shell.py](unit/test_snapshot_store_shell.py), and [unit/test_sftp_publication.py](unit/test_sftp_publication.py). These execute checked-in shell code with disposable files and fake transports, not a VPS. Publication reconciliation and validation-gate tests also support Git Bash on Windows; the existing deployment and restore suites require Linux.

| Test | Behavior protected |
|---|---|
| `test_single_cutover_retains_active_reader_and_legacy_paths` | One atomic release switch serves new readers while old readers/files remain valid; checksums and read-only modes survive |
| `test_failure_preserves_active_release` | Missing payloads, corrupt hashes, sidecars, invalid pointers, and duplicate releases cannot replace active state |
| `test_lock_contention_and_interrupted_pointer_promotion` | An acquired lock blocks competing activation; failed final pointer replacement preserves current and removes only owned staging |
| `test_missing_local_file_fails_before_network` | Every required deployment payload is checked before credentials or transport |
| `test_stale_bundle_fails_validation_before_network` | Invalid projections cannot reach the deployment transport |
| `test_validation_creating_wal_fails_before_network` | Sidecars appearing during validation are detected before upload |
| `test_local_wal_fails_without_removing_sidecar` | Uncheckpointed local data is preserved, not deleted to make deployment pass |
| `test_partial_upload_aborts_and_requests_staging_cleanup` | Interrupted SCP prevents activation, requests remote staging cleanup, removes temporary credentials, and preserves the local database |
| `test_default_ssh_directory_preserves_existing_home_credentials` in `test_deploy_shell.py` | Deployment cleanup cannot delete preexisting home SSH material |
| `test_unreferenced_local_state_is_preserved_without_snapshot` | Restore cannot replace unverified local canonical state merely because no durable snapshot is available |
| `test_unreferenced_dangling_symlink_is_preserved_without_snapshot` | Dangling local canonical aliases are not treated as permission to bootstrap |
| `test_default_ssh_directory_preserves_existing_home_credentials` in `test_restore_shell.py` | Restore cleanup cannot delete preexisting backup/deployment SSH material |
| `test_preexisting_bootstrap_candidate_is_not_deleted` | An existing recovery candidate belongs to its prior operation |
| `test_invalid_restored_candidate_stops_without_bootstrap` | Invalid restored state remains for diagnosis rather than triggering a legacy fallback |
| `test_no_snapshot_and_no_local_state_must_pass_legacy_guard` | Failed SSH/legacy guards cannot authorize bootstrap |
| `test_snapshot_store_preserves_a_mismatched_local_database` | Durable/local mismatch stops before downloading over unsnapshotted state |
| `test_snapshot_store_rejects_sidecars_before_transfer` | Restore and publish both reject live sidecars without transfer or deletion |
| `test_snapshot_absence_requires_successful_listing` | Only proven empty/missing stores permit absence; listing failures, malformed stores, missing pointers, and failed/empty manifest downloads stop |
| `test_publication_reconciles_transport` | Immutable objects and the latest pointer resume after disconnects before, during, or after upload, after rename, and during download; reruns do not repeat completed writes, retries are bounded, and permission errors, conflicting bytes, or unexpected pointer changes fail closed |
| `test_latest_requires_round_trip_validation` | The actual publication function advances latest only after round-trip verification and application statistics succeed; checksum and statistics failures stop without transport retries |

### Workflow safety

Sources: [unit/test_readme_validation_workflow.py](unit/test_readme_validation_workflow.py) and [unit/test_state_review_workflow.py](unit/test_state_review_workflow.py). Configuration assertions here protect permissions and failure dependencies that local shell execution cannot emulate; dispatch/merge scripts also run against fake GitHub responses.

| Test | Behavior protected |
|---|---|
| `test_dependency_review_preserves_real_action_and_pull_request_validation` | Dependency review retains read-only permissions, real pinned action, mandatory dispatch input, correct comparison refs, and unsuppressed high-severity failure |
| `test_dispatch_resolves_real_pr_base_and_binds_head_to_workflow_commit` | Dispatch resolves the PR's actual base and binds its head to the workflow commit |
| `test_dependency_dispatch_rejects_untrusted_scope_or_comparison` | Closed/foreign/wrong-base/mismatched-head/non-README PRs and malformed/injected SHAs fail without output refs |
| `test_dependency_dispatch_rejects_invalid_inputs_before_api_access` | Invalid PR numbers, branch refs, and SHAs fail before even the fake API is called |
| `test_dependency_dispatch_fails_closed_on_unavailable_metadata` | API failure, malformed JSON, and absent metadata cannot authorize review |
| `test_readme_dispatch_waits_for_dependency_review_before_merge` | Dispatch and await every required check for the exact fresh head; missing/stale/failed runs and changed scope prevent merge |
| `test_all_readme_validation_workflows_accept_explicit_dispatch` | Every workflow in the required validation set supports the dispatch path |
| `test_matching_reviewed_state_passes` | Normal, seal-adoption, and recovery modes accept an exact reviewed projection |
| `test_only_explicit_recovery_can_propose_unmerged_state` | Even microsecond seal drift blocks normal/adoption runs; only explicit recovery may propose it while retaining reviewed evidence |
| `test_seal_adoption_still_accepts_only_the_initial_seal` | Initial seal adoption cannot also approve content/date drift |
| `test_render_failure_cannot_be_recovered` | Recovery/adoption flags cannot convert renderer failure into success |
| `test_collection_quality_gate_propagates_blocking_failures` | Workflow accepts only scrape exits 0/4 with explicit full/partial outputs; blocking, configuration, and migration exits cannot publish |
| `test_availability_denial_stops_workflow_before_follow_on_scrape` | Audit exit handling and step dependency stop subsequent collection after denial |
| `test_readme_merge_respects_repository_policy_and_validated_head` | Merge uses the validated head, respects auto-merge policy/manual mode, rechecks scope, and fails closed on policy or merge errors |
| `test_partial_proposals_force_manual_review_independently_of_caller` | Executed proposal guard forces partial/manual labeling and disables merging even when the caller asks for auto-merge; invalid outcomes fail closed |
| `test_processor_uses_repository_request_and_availability_settings` | Request pacing, concurrency, and interval come from Actions variables; the cap preserves overrides with a 50-job fallback; bounded timeout and authorization remain intact |
| `test_nightly_supports_manual_and_scheduled_full_updates` | Scheduled/manual work uses a noncancelling shared lock, audit/collection, and explicit authorization input |
| `test_availability_failure_prevents_readme_handoff_to_mutation_job` | Both audit workflows retain success-dependent handoff to the README-writing job |
| `test_collection_retains_only_the_quality_report_even_on_blocking_failure` | Failed quality checks retain aggregate evidence, not publication artifacts; source-free recovery cannot upload stale reports |
| `test_recovery_mode_guard_precedes_restore_and_forbids_side_effects` | Recovery-mode combinations fail before restore and cannot publish snapshots or bypass validation before handoff |
| `test_recovery_requires_explicit_dispatch_and_manual_readme_only_review` | Recovery is opt-in, read-only, serialized, without collection/deployment flags or automatic merging |

### Documentation and public links

Sources: [unit/test_docs.py](unit/test_docs.py), [unit/test_docs_lint.py](unit/test_docs_lint.py), [unit/test_docs_site.py](unit/test_docs_site.py), [unit/test_coverage_docs.py](unit/test_coverage_docs.py), and [unit/test_public_domain.py](unit/test_public_domain.py).

| Test | Behavior protected |
|---|---|
| `test_local_workflow_references_use_self_repository_syntax_and_exist` | Local workflow/action references use the repository's supported syntax and resolve to existing files |
| `test_source_checker_validates_inventories_and_local_workflow_overview` | Broken script/test-inventory links and actual workflow-table references fail; unrelated example filenames do not cause false failures |
| `test_source_links_cover_images_video_and_agent_guidance` | Agent guidance, images, video sources, and posters participate in local-link validation |
| `test_external_link_scope_keeps_authored_diagram_markdown` | POSIX/Windows paths include authored diagram Markdown while excluding generated media from external-link crawling |
| `test_documentation_linters_use_the_same_curated_read_only_inputs` | Both pinned linters receive the same maintained files, including this inventory, with read-only mounts/no network and no generated/vendor/private authoring trees |
| `test_documentation_lint_stops_after_failed_markdownlint` | A failed first linter stops the gate instead of being masked by a later success |
| `test_documentation_lint_preflight_fails_without_starting_a_process` | Missing Docker or a maintained document fails before launching containers |
| `test_github_alerts_render_as_material_admonitions_without_changing_other_text` | Publication translates real alerts without corrupting ordinary prose |
| `test_rendered_link_check_detects_missing_images_and_anchors` | Rendered anchors/media, favicon fidelity, and private-file leaks fail validation |
| `test_rendered_soundtrack_links_and_exact_publication_boundary` | Only the cataloged soundtrack path may publish, and missing linked audio still fails |
| `test_legacy_redirects_require_a_real_canonical_destination` | Redirects cannot be generated without real destination pages and point correctly across directories |
| `test_legacy_redirects_point_directly_to_current_topic_guides` | Legacy mappings resolve directly to current guides, never redirect chains or overwritten canonical pages |
| `test_public_staging_publishes_media_but_not_private_root_files` | Approved media/policies/favicon reach strict staging while private root files do not |
| `test_public_staging_rejects_unapproved_files` | Databases, environment files, uncataloged audio, and promotional implementation files fail the publication allowlist |
| `test_public_staging_rejects_symlinked_media` | Allowed extensions cannot smuggle private files through symlinks |
| `test_renders_table_and_then_passes_check` | Stale check mode does not write; rendering updates measured values and subsequent checking passes without altering unrelated content |
| `test_default_document_targets_nested_guide_independently_of_working_directory` | Default coverage updates target the canonical nested guide, not the README or a caller-relative path |
| `test_invalid_report_fails_cleanly_without_rewriting_readme` | Invalid measurement data leaves the target untouched with a sanitized error |
| `test_rejects_duplicate_generated_regions` | Ambiguous coverage-region ownership cannot trigger a rewrite |
| `test_legacy_hostname_only_in_redirect_and_migration_material` | New retired-host references outside the approved migration/redirect material are detected without requiring obsolete references to remain |

### Test isolation and website fixtures

Sources: [unit/test_test_environment.py](unit/test_test_environment.py) and [unit/test_site_fixture.py](unit/test_site_fixture.py).

| Test | Behavior protected |
|---|---|
| `test_live_gate_requires_explicit_selection_and_both_flags` | All marker/opt-in/permission combinations require exact live selection plus both flags; the test never enables real access |
| `test_default_test_environment_is_disposable_and_unauthorized` | Tests start outside operator paths/settings with temporary home and authorization off |
| `test_offline_http_guard_blocks_sync_and_async_default_transports` | Real HTTPX calls fail even through application exception-catching paths |
| `test_offline_http_guard_preserves_injected_mock_transports` | The guard permits synthetic transports needed to test the real policy layer |
| `test_shell_subprocesses_get_only_isolated_settings` | Subprocesses drop operator settings and use temporary homes, offline uv, and blocking transport fallbacks |
| `test_fixture_matches_migrated_repository_and_exports` | Browser/demo fixtures use current migrations and exports, deterministic relative dates, correct successful-collection time, and no invented provenance |
| `test_fixture_refuses_to_replace_state_with_sidecars` | Fixture regeneration cannot discard WAL/SHM/journal state |

## Website unit tests

These run in Bun without a browser or a running site.

### HTTP cache and safe URLs

Sources: [http-cache.test.ts](../site/tests/unit/http-cache.test.ts), [listing-url.test.ts](../site/tests/unit/listing-url.test.ts), and [site-url-value.test.ts](../site/tests/unit/site-url-value.test.ts).

| Test title | Behavior protected |
|---|---|
| `matches If-None-Match %j: %j` | Missing, empty, nonmatching, wildcard, strong, weak, and list validators follow conditional-GET semantics |
| `accepts only the canonical HTTPS LinkedIn listing matching the job ID` | Stored links cannot use another ID, unsafe/noncanonical URL spellings, credentials, tracking, control characters, or invalid IDs |
| `accepts canonical HTTP and HTTPS origins` | Local default and production origin are parsed as origins |
| `rejects values that are unsafe or are not origins` | Userinfo, paths, queries, fragments, retired host, insecure production scheme, and alternate production ports fail |

### Browser-local state

Source: [local-opportunity-state.test.ts](../site/tests/unit/local-opportunity-state.test.ts).

| Test title | Behavior protected |
|---|---|
| `first visit, corrupt, unknown version and future visit reset safely` | Unsupported/untrusted stored state resets instead of inventing lists or visit history |
| `retains only current IDs and deduplicates all local lists` | Stale/duplicate IDs are pruned and toggles preserve the intended list membership |
| `counts only rows first seen strictly after the previous visit` | First visits have no new baseline; equal/older rows are not new |
| `SQLite timestamps are UTC and compare consistently with ISO offsets` | Equivalent database/ISO instants produce consistent new-row membership |
| `visit baseline survives reloads and advances after inactivity` | Reloads preserve the previous visit; the 30-minute boundary advances it without losing saved IDs |

### API contracts

Source: [opportunity-api.test.ts](../site/tests/unit/opportunity-api.test.ts).

| Test title | Behavior protected |
|---|---|
| `v1 schema rejects private fields, invalid envelopes and noncanonical timestamps` | The shared schema accepts actual payloads/errors but rejects private fields, invalid pagination, timestamp spellings, and incomplete downloads |
| `filters combined search and exact country/company/category/type and snapshot recency` | Filters combine with AND semantics, search normalizes case/spacing, and recency uses snapshot evidence |
| `stable sorting, numeric ID ties, bounded pagination and empty/out-of-range pages` | API ordering/pagination is deterministic, numeric ties are stable, and empty/out-of-range envelopes remain truthful |
| `orders distinct microseconds chronologically before applying numeric ID ties` | Submillisecond differences and equivalent offset/SQLite instants sort correctly without mutating inputs |
| `publishes UTC RFC 3339 first-seen timestamps without losing microseconds` | API serialization normalizes valid storage timestamps and rejects unreadable values |
| `invalid snapshot timestamps cannot turn recency results into a successful empty list` | Bad first-seen or collection dates fail rather than silently filtering every row out |
| `stable explicit public field allowlist` | Extra lifecycle/path fields on incoming rows cannot leak through the API envelope |
| `bounded property fuzzing preserves encoded queries and rejects duplicate keys` | Seeded encoded-query cases round-trip within bounds, remain order-independent, and reject duplicate keys |
| `rejects malformed, duplicate, unknown and excessive input` | Empty invalid filters, unsupported enums, invalid page numbers, controls, encodings, duplicates, and length limits fail closed |

### Feeds, filtering, and presentation

Sources: [opportunity-feed.test.ts](../site/tests/unit/opportunity-feed.test.ts), [opportunity-filter.test.ts](../site/tests/unit/opportunity-filter.test.ts), [opportunity-presentation.test.ts](../site/tests/unit/opportunity-presentation.test.ts), [opportunity-list.test.tsx](../site/tests/unit/opportunity-list.test.tsx), and [structured-data.test.ts](../site/tests/unit/structured-data.test.ts).

| Test title | Behavior protected |
|---|---|
| `parses only bounded, single type, country, and category filters` | Feed inputs reject unknown/repeated/unsafe/oversized values |
| `filters exact employment type, country, and category with combined AND semantics` | Feed membership and self-links agree with the requested scope |
| `renders escaped RSS and Atom with listing dates and canonical links` | Hostile text stays XML text while identities and publication dates remain valid |
| `removes XML-invalid code points and caps results at the newest 50` | Invalid Unicode cannot break XML and feed size stays bounded |
| `canonicalizes filter order and returns a valid empty feed` | Equivalent filters serialize identically; empty feeds retain a deterministic timestamp |
| `uses the latest successful collection timestamp for empty Atom feeds` | An empty selection can still report real dataset freshness |
| `empty filters preserve every row and its order without mutating the input` | Filtering cannot drop/reorder/alter the unfiltered dataset; allocation identity is deliberately not tested |
| `search spans nonempty fields with normalized case and surrounding whitespace` | Search includes category/type/optional industries and handles absent values |
| `recency includes both boundaries and excludes old, future, and invalid timestamps` | Recency's inclusive bounds reject future/invalid evidence without hiding rows when no recency filter is set |
| `extracts every unique country from a multi-location value` | Multi-country roles remain discoverable under each country without duplicate options |
| `rejects invalid calendar or out-of-range UTC evidence: %s` | Month/day/leap-year/time/UTC-range failures cannot normalize into a different valid instant |
| `normalizes valid leap days, UTC offsets and fractional seconds` | Legitimate boundary dates and fractions survive normalization |
| `formats offset and SQLite timestamps consistently in UTC` | Visible dates follow UTC even when an offset crosses midnight |
| `rendered %s rows preserve microseconds and numeric ID ties` | Both first-seen directions render independently expected IDs and normalized machine-readable timestamps; this checks row semantics, not button markup |
| `publishes a timezone-explicit date or omits invalid evidence: %s` | JSON-LD dateModified is normalized or omitted for absent/impossible timestamps |
| `escapes markup that could terminate the JSON-LD script` | Script-closing text is safely escaped while preserving JSON meaning |

### Status, releases, and startup

Sources: [opportunity-status.test.ts](../site/tests/unit/opportunity-status.test.ts), [release-path.test.ts](../site/tests/unit/release-path.test.ts), [start.test.ts](../site/tests/unit/start.test.ts), and [tooling-dependencies.test.ts](../site/tests/unit/tooling-dependencies.test.ts).

| Test title | Behavior protected |
|---|---|
| `publishes only explicit public fields with UTC timestamps and no private metadata` | Status strips unknown metadata and exposes only the five approved fields |
| `an empty, never-collected legacy dataset is valid but not invented on errors` | Genuine empty state is distinct from missing metadata |
| `preserves generation microseconds from %s independently of collection time` | Export and collection clocks remain distinct and precise |
| `rejects metadata: %s` | Invalid root/version/counts/timestamps/hashes fail rather than reporting misleading health |
| `rejects a different download hash, invalid database aggregates, and unsafe release IDs` | Content mismatch, impossible aggregates, invalid collection time, and path-like release identifiers cannot publish |
| `the shared schema validates status and rejects extra fields or invalid values` | Status schema enforces allowlists, nullability, counts, hashes, UTC timestamps, and opaque release identifiers |
| `always rereads status without caching or conditional 304 responses` | Repeated conditional requests still read current state and return no-store responses |
| `sanitizes %s errors and rejects queries before reading state` | GET/HEAD reject query input before I/O and sanitize failed reads with correct empty HEAD bodies |
| `legacy publication paths preserve defaults and explicit overrides without inventing a release` | Fixed-path mode keeps configured paths and returns no fictitious release ID |
| `an invalid release root never falls back to legacy database or export paths` | A configured but broken versioned publication fails closed |
| `pins a real release directory even when the pointer changes` | Linux readers retain one database/export release selection across cutover |
| `fails closed for missing, invalid, and escaping pointers` | Linux release resolution rejects traversal, missing pointers, and symlink escapes |
| `does not expose a non-public directory name through a release alias` | A numeric alias cannot leak a private resolved directory name |
| `standalone startup preserves %s data paths after Next changes directory` | Default/relative/absolute runtime paths remain correct after standalone chdir and static assets remain available |
| `Lighthouse's FTP dependency keeps its CommonJS API and bounds malformed listing parsing` | The pinned security override stays compatible and rejects pathological synthetic listings within a subprocess timeout, without FTP access |

## Website HTTP and browser tests

Playwright uses synthetic migrated SQLite/exports. HTTP contracts do not open a browser unless XML parsing or an actual user journey requires one. Keyboard/focus and storage tests protect real interactions rather than the presence of controls.

### Directory URLs and navigation

Source: [directory.spec.ts](../site/tests/e2e/directory.spec.ts).

| Test title | Behavior protected |
|---|---|
| `filters opportunities and writes shareable URL parameters` | Company/category controls change actual rows and shareable public state |
| `filters one employment type at a time` | Switching type replaces rather than combines mutually exclusive selections |
| `filters opportunities by when they were first seen` | Each recency window changes counts correctly and Reset clears it |
| `restores filters from a shared URL and browser history` | Deep-linked search/type/country/recency and browser Back restore the same results |
| `composes search, country, category, first-seen filtering, and company sorting` | Combined filters and sorting agree on visible row order |
| `restores sorting, page, and page size from a shared URL` | Deep-linked pagination survives history; a sort change resets to page one |
| `falls back safely for unsupported directory view parameters` | Browser inputs constrain invalid recency/sort/page/page-size values rather than applying API-style rejection |
| `search, reset, keyboard focus, and sorting remain interactive` | Search shortcut works; reset preserves unrelated query/sort/page-size state; sort direction changes actual row order |
| `defaults to latest first seen and paginates results` | Newest-first rows, next-page links, and page-size changes expose the expected data |
| `publishes canonical SEO and crawler metadata` | Filtered pages are nonindexable with canonical URL, safe JSON-LD and download metadata; image/manifest/robots/sitemap routes work and local analytics stays absent |
| `legacy host permanently redirects paths and queries without serving alternate content` | Retired-host requests preserve path/query through a 308 canonical-origin redirect |
| `crawler can follow unfiltered pages without JavaScript` | SSR pagination has real links, visible rows, and valid page-specific canonical/indexing metadata |
| `does not index out-of-range or alternate directory pages` | Invalid/alternate views are nonindexable while unrelated tracking parameters do not break valid page indexing |

### Hydration, accessibility, and downloads

Sources: [directory-hydration.spec.ts](../site/tests/e2e/directory-hydration.spec.ts), [accessibility.spec.ts](../site/tests/e2e/accessibility.spec.ts), and [downloads.spec.ts](../site/tests/e2e/downloads.spec.ts).

| Test title | Behavior protected |
|---|---|
| `hydration restores private lists without guessing their counts in server HTML` | Withheld JavaScript proves SSR's public total/unknown private state; hydration applies saved/hidden data without changing the URL or producing errors |
| `normal directory` | Axe scans the default directory for supported WCAG violations |
| `filtered directory` | Axe scans a populated filtered view |
| `empty results` | Axe scans an empty view and its real reset journey restores rows/search/URL |
| `persisted dark mode remains accessible after reload` | Theme choice survives reload and the resulting page passes axe |
| `downloads sanitized exports whose counts and hashes match their metadata` | Actual CSV/JSON HTTP responses have correct types/filenames, public-only fields, and metadata matching their bytes/counts |
| `CSV and JSON downloads work at ${width}px without horizontal scrolling` | Mobile and narrow-desktop users can reach both links and complete named downloads without failures |

### Private browser lists

Source: [local-opportunities.spec.ts](../site/tests/e2e/local-opportunities.spec.ts).

| Test title | Behavior protected |
|---|---|
| `crawler HTML contains no fabricated local-state summaries` | Server HTML contains no invented saved/applied/hidden or new-opportunity summaries; hydration shows only one real local-state summary with initial zero counts |
| `first and returning visits, corrupt state and stale IDs` | Real storage loads/prunes correctly; new-role membership survives reload, hidden roles disappear from new counts, and corruption recovers |
| `empty local lists explain the selected view without claiming the directory is empty` | Empty saved/applied views remain distinguishable from an empty dataset and can return to all rows without URL changes |
| `mobile empty messages and reset controls need no horizontal scrolling` | Mobile empty-list/filter recovery is reachable and restores the dataset |
| `hiding every role leaves a clear route to restoring the directory` | All-hidden state is recoverable through Hidden and restore actions |
| `menu dismissal preserves tab order and focus after a viewport change` | Tab/Shift+Tab and resizing dismiss menus while restoring meaningful keyboard focus |
| `saved, applied, hidden and restored work across filters, pages and reloads` | Local choices persist, compose with public filters, respect hiding/restoring, and remain accessible |
| `saved rows respect pagination and sorting without changing URL semantics` | Private view pagination clamps locally without rewriting public page state; public sorting still applies |
| `keyboard actions, menu dismissal, focus and mobile reachability` | Keyboard save/apply/hide, scroll/Escape dismissal, focused actions, reachable menus, axe, and mobile overflow preserve usability |
| `local actions still work when storage access is disabled` | Storage-denied browsers can still use in-memory local lists |
| `tabs merge sequential local actions and synchronize clearing without requests` | Tabs merge sequential actions, ignore stale clear notifications, synchronize real clearing, store only approved state, and make no action requests or URL changes |
| `quota failures retain consecutive in-memory actions instead of stale stored state` | Failed writes do not undo consecutive local actions; removing the last saved row recovers focus |

### API and feeds

Sources: [api.spec.ts](../site/tests/e2e/api.spec.ts) and [feed.spec.ts](../site/tests/e2e/feed.spec.ts).

| Test title | Behavior protected |
|---|---|
| `serves the exact repository v1 schema at its canonical product URL` | The public schema route serves the reviewed contract bytes and identity |
| `read-only API serves canonical rows with stable schema, filtering and pagination` | Real SQLite/API/export projections agree on sanitized fields and IDs, timestamp format, filtering, pagination, and CORS |
| `semantically equivalent query strings return identical representations and ETags` | Defaults and reordered filters cannot fragment conditional caching |
| `ETag revalidation, validation errors, and no mutation endpoints` | GET/HEAD/OPTIONS, weak validators, query failures, CORS, and 405 mutation rejection preserve the read-only HTTP contract |
| `RSS publishes recent open opportunities as a bounded, cacheable read-only feed` | RSS serves fixture rows with validators, public-only data, and homepage autodiscovery |
| `RSS and Atom accept only safe exact filters and return an empty feed for unmatched values` | Both feed formats filter real rows; unmatched values remain valid empty feeds and malformed queries fail safely |
| `Atom supplies a feed-level author inherited by entries, including empty feeds` | XML parsing verifies valid namespace-scoped author metadata for populated, filtered, and empty Atom feeds |
| `feed validators support HEAD and conditional GET without mutation methods` | Feed bodies/validators agree across methods and mutation methods are rejected |

### Status over HTTP and standalone production

Sources: [status.spec.ts](../site/tests/e2e/status.spec.ts) and [status-production.spec.ts](../site/tests/e2e/status-production.spec.ts).

| Test title | Behavior protected |
|---|---|
| `status reports the served dataset, not a newer failed collection or a runtime path` | Status agrees with API/download counts, metadata and content hashes, reports only successful collection time, disables caching, and leaves SQLite bytes unchanged |
| `status supports HEAD and CORS but rejects queries and mutation methods` | Public status HTTP methods, query rejection, preflight restrictions, and no-store behavior are wired correctly |
| `production status reads the selected dataset without modifying SQLite` | Built standalone status uses the configured release/fixed paths, emits production headers, and preserves database bytes |
| `production status fails closed without leaking details: ${failure}` | Missing/invalid/unmigrated databases; missing/invalid/non-UTF-8/oversized/mismatched metadata; and missing/changed/oversized downloads return safe 503 GET/HEAD responses without repairing state; each restored fixture recovers |
| `production status preserves SQLite and metadata microseconds independently` | Real production reads retain both clocks' independent microseconds |
| `production status counts only open rows and represents a never-collected empty dataset` | Closed rows and missing success history yield a genuine empty/null response, not fake freshness |
| `production status follows release cutovers and rejects a missing pointer without legacy fallback` | Linux standalone requests follow immutable publication switches, reject missing current pointers, and recover after restoration |

## Fixtures and optional checks

| File or test | Purpose and boundary |
|---|---|
| [conftest.py](conftest.py) | Temporary settings/home/cwd, HTTPX blocking, exact live opt-in, checked-in fixture loader, deterministic rules/search, and migrated database/session fixtures |
| [shell_helpers.py](shell_helpers.py) | Environment allowlist and blocking SSH/SCP/SFTP fallbacks for offline shell tests |
| `__init__.py` files | Python package discovery/import support; no tests or behavior assertions |
| [linkedin_search_page_1.html](fixtures/linkedin_search_page_1.html) | One eligible internship plus an unrelated senior role exercises stable IDs and prefiltering |
| [linkedin_search_page_2.html](fixtures/linkedin_search_page_2.html) | Overlapping identity plus a second technical role exercises pagination/deduplication |
| [linkedin_job_detail_1111111111.html](fixtures/linkedin_job_detail_1111111111.html) | Explicit identity, relative posting age, start-cycle prose, and structured industry evidence |
| [linkedin_job_detail_3333333333.html](fixtures/linkedin_job_detail_3333333333.html) | Remote-European machine-learning role; workplace type must not become industries |
| [create-fixture.mjs](../site/tests/e2e/create-fixture.mjs) | Invokes the Python fixture owner so browser tests use real migrations/export contracts, not a parallel schema |
| [helpers.ts](../site/tests/e2e/helpers.ts) | Waits for interactivity and distinguishes filtered counts from the immutable full-dataset badge |
| `site/tests/e2e/.tmp/` | Ignored synthetic runtime output, never a source fixture to review or commit |
| `test_linkedin_search_page_parsing_performance` in [benchmarks/test_parsing_classification.py](benchmarks/test_parsing_classification.py) | Offline search-parser throughput trend with a correctness sanity check; not an absolute timing gate |
| `test_classification_performance` in [benchmarks/test_parsing_classification.py](benchmarks/test_parsing_classification.py) | Offline full classification hot-path trend with fixed evidence; not duplicate functional coverage |
| `test_public_linkedin_search_and_detail_are_reachable` in [integration/test_live_smoke.py](integration/test_live_smoke.py) | Optional bounded adapter compatibility smoke test, excluded from normal validation and never run without exact live selection plus explicit permission/opt-in |

Linux-only recovery/release checks and Bash/`jq` workflow checks are not replaced by Windows skips. Symlink tests need platform permission. A skipped test is not a pass. This inventory describes intended coverage, not a claim that every platform or optional live check has run.
