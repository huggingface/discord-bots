.PHONY: quality style

check_dirs := /codellama/app.py, /deepfloydif/app.py, /falcon/app.py, /wuerstchen/app.py, /legacy/app.py

quality:
	black --check $(check_dirs)
	ruff $(check_dirs)
style:
	black $(check_dirs)
	ruff $(check_dirs) --fix
