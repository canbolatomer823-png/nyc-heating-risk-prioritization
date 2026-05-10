PROJECT_DIR := $(abspath $(dir $(lastword $(MAKEFILE_LIST))))
WORKSPACE_ROOT := $(abspath $(PROJECT_DIR)/../..)
PYTHON := $(WORKSPACE_ROOT)/.venv/bin/python
UVICORN := $(WORKSPACE_ROOT)/.venv/bin/uvicorn
R_SCRIPT := /opt/homebrew/bin/Rscript
ENV_FILE := $(PROJECT_DIR)/deploy/aws.env
SUPABASE_ENV_FILE := $(PROJECT_DIR)/deploy/supabase.env
RENDERED_DIR := $(PROJECT_DIR)/deploy/rendered
FINAL_WINDOW_ROOT := $(PROJECT_DIR)/data/windows/heat_season_2024_10_01_2025_05_31
DENSE_PANEL_PATH := $(FINAL_WINDOW_ROOT)/processed/building_day_heat_panel_dense.csv
MODELING_TABLE_PATH := $(FINAL_WINDOW_ROOT)/processed/building_day_modeling_table.csv
SCORED_CSV_PATH := $(FINAL_WINDOW_ROOT)/processed/logistic_regression_scored.csv
RECORD_LOOKUP_DB_PATH := $(FINAL_WINDOW_ROOT)/processed/record_lookup.sqlite
OOT_WINDOW_ROOT := $(PROJECT_DIR)/data/windows/oot_heat_season_2025_10_01_2026_04_26
OOT_MODELING_TABLE_PATH := $(OOT_WINDOW_ROOT)/processed/building_day_modeling_table.csv

.PHONY: modeling-table record-lookup train priority serve smoke demo-proof class-demo-check test policy-sim fairness-report error-analysis uncertainty drift-report experiment-registry r-analysis oot-validation analysis-suite supabase-dry-run supabase-check supabase-publish portfolio-pack final-audit aws-live-proof aws-shutdown-proof statistical-refresh-start statistical-refresh-status deploy-day-status deploy-validate deploy-render tfvars aws-preflight aws-preflight-release aws-bootstrap ecr-login kubeconfig k8s-check release release-dry-run

modeling-table:
	$(PYTHON) $(PROJECT_DIR)/src/modeling/build_modeling_table.py

record-lookup:
	$(PYTHON) $(PROJECT_DIR)/src/reporting/build_record_lookup_db.py

train:
	@if [ ! -f "$(MODELING_TABLE_PATH)" ] || [ "$(DENSE_PANEL_PATH)" -nt "$(MODELING_TABLE_PATH)" ]; then \
		$(MAKE) -C $(PROJECT_DIR) modeling-table; \
	fi
	$(PYTHON) $(PROJECT_DIR)/src/modeling/logistic_regression_model.py
	$(MAKE) -C $(PROJECT_DIR) experiment-registry
	@if [ ! -f "$(RECORD_LOOKUP_DB_PATH)" ] || [ "$(SCORED_CSV_PATH)" -nt "$(RECORD_LOOKUP_DB_PATH)" ]; then \
		$(MAKE) -C $(PROJECT_DIR) record-lookup; \
	fi

priority:
	$(PYTHON) $(PROJECT_DIR)/src/reporting/build_inspection_priority_report.py

serve:
	$(UVICORN) api.app:app --app-dir $(PROJECT_DIR)/src --host 0.0.0.0 --port 8000

smoke:
	bash $(PROJECT_DIR)/deploy/run_local_smoke_test.sh $(WORKSPACE_ROOT)

demo-proof:
	bash $(PROJECT_DIR)/deploy/run_demo_proof.sh $(WORKSPACE_ROOT)

class-demo-check:
	bash $(PROJECT_DIR)/deploy/run_class_demo_check.sh

test:
	$(PYTHON) -m unittest discover -s $(PROJECT_DIR)/tests -p 'test_*.py'

policy-sim:
	$(PYTHON) $(PROJECT_DIR)/src/reporting/simulate_inspection_policies.py

fairness-report:
	$(PYTHON) $(PROJECT_DIR)/src/reporting/build_subgroup_fairness_report.py

error-analysis:
	$(PYTHON) $(PROJECT_DIR)/src/reporting/analyze_model_errors.py

uncertainty:
	$(PYTHON) $(PROJECT_DIR)/src/reporting/build_uncertainty_report.py

drift-report:
	$(PYTHON) $(PROJECT_DIR)/src/reporting/build_drift_report.py

experiment-registry:
	$(PYTHON) $(PROJECT_DIR)/src/reporting/sync_experiment_registry.py

r-analysis:
	$(R_SCRIPT) $(PROJECT_DIR)/src/modeling/r_heat_season_analysis.R

oot-validation:
	@if [ ! -f "$(OOT_MODELING_TABLE_PATH)" ]; then \
		echo "missing out-of-time modeling table: $(OOT_MODELING_TABLE_PATH)"; \
		exit 1; \
	fi
	$(PYTHON) $(PROJECT_DIR)/src/reporting/evaluate_out_of_time_window.py

analysis-suite:
	$(MAKE) -C $(PROJECT_DIR) policy-sim
	$(MAKE) -C $(PROJECT_DIR) fairness-report
	$(MAKE) -C $(PROJECT_DIR) error-analysis
	$(MAKE) -C $(PROJECT_DIR) uncertainty
	$(MAKE) -C $(PROJECT_DIR) drift-report
	$(MAKE) -C $(PROJECT_DIR) experiment-registry
	$(MAKE) -C $(PROJECT_DIR) r-analysis

supabase-dry-run:
	$(PYTHON) $(PROJECT_DIR)/src/reporting/publish_supabase_reporting.py

supabase-check:
	@if [ -f "$(SUPABASE_ENV_FILE)" ]; then \
		set -a; . "$(SUPABASE_ENV_FILE)"; set +a; \
	fi; \
	$(PYTHON) $(PROJECT_DIR)/src/reporting/check_supabase_readiness.py

supabase-publish:
	@if [ -f "$(SUPABASE_ENV_FILE)" ]; then \
		set -a; . "$(SUPABASE_ENV_FILE)"; set +a; \
	fi; \
	$(PYTHON) $(PROJECT_DIR)/src/reporting/publish_supabase_reporting.py --publish

portfolio-pack:
	$(PYTHON) $(PROJECT_DIR)/src/reporting/build_portfolio_package.py

final-audit:
	$(PYTHON) $(PROJECT_DIR)/src/reporting/build_final_project_audit.py

aws-live-proof:
	@if [ -z "$(BASE_URL)" ]; then \
		echo "Usage: make -C $(PROJECT_DIR) aws-live-proof BASE_URL=http://your-aws-load-balancer"; \
		exit 2; \
	fi
	$(PYTHON) $(PROJECT_DIR)/src/aws/capture_live_deploy_proof.py --base-url "$(BASE_URL)"

aws-shutdown-proof:
	$(PYTHON) $(PROJECT_DIR)/src/aws/capture_shutdown_proof.py --env-file $(ENV_FILE)

statistical-refresh-start:
	bash $(PROJECT_DIR)/scripts/start_statistical_refresh.sh

statistical-refresh-status:
	bash $(PROJECT_DIR)/scripts/check_statistical_refresh.sh

deploy-day-status:
	bash $(PROJECT_DIR)/deploy/check_live_deploy_readiness.sh $(ENV_FILE)

deploy-validate:
	$(PYTHON) $(PROJECT_DIR)/src/aws/validate_deploy_env.py --env-file $(ENV_FILE)

deploy-render:
	$(PYTHON) $(PROJECT_DIR)/src/aws/render_deployment_assets.py --env-file $(ENV_FILE) --project-root $(PROJECT_DIR) --output-dir $(RENDERED_DIR)

tfvars:
	$(PYTHON) $(PROJECT_DIR)/src/aws/render_tfvars.py --env-file $(ENV_FILE)

aws-preflight:
	$(PYTHON) $(PROJECT_DIR)/src/aws/preflight_check.py --env-file $(ENV_FILE)

aws-preflight-release:
	$(PYTHON) $(PROJECT_DIR)/src/aws/preflight_check.py --env-file $(ENV_FILE) --require-docker --require-kubectl

aws-bootstrap:
	$(PYTHON) $(PROJECT_DIR)/src/aws/bootstrap_stack.py --env-file $(ENV_FILE) --write-env

ecr-login:
	$(PYTHON) $(PROJECT_DIR)/src/aws/ecr_login.py --env-file $(ENV_FILE)

kubeconfig:
	$(PYTHON) $(PROJECT_DIR)/src/aws/write_kubeconfig.py --env-file $(ENV_FILE) --output $(PROJECT_DIR)/deploy/generated-kubeconfig.yaml --python-bin $(PYTHON)

k8s-check:
	bash $(PROJECT_DIR)/deploy/check_k8s_manifests.sh $(RENDERED_DIR)/k8s

release:
	bash $(PROJECT_DIR)/deploy/release_to_aws.sh --env-file $(ENV_FILE)

release-dry-run:
	bash $(PROJECT_DIR)/deploy/release_to_aws.sh --env-file $(ENV_FILE) --dry-run
