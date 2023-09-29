.PHONY: quality style

check_dirs := /codellama/codellama.py, /deepfloydif/deepfloydif.py, /falcon/falcon180b.py, /wuerstchen/wuerstchen.py, /legacy/musicgen.py

quality:
	black --check $(check_dirs)
	ruff $(check_dirs)
style:
	black $(check_dirs)
	ruff $(check_dirs) --fix
