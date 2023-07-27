.PHONY: quality style

check_dirs := app.py deepfloydif.py falcon.py

quality:
	black --check $(check_dirs)
	ruff $(check_dirs)
style:
	black $(check_dirs)
	ruff $(check_dirs) --fix
