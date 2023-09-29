.PHONY: quality style

check_dirs := codellama.py, deepfloydif.py, falcon180b.py, wuerstchen.py, musicgen.py

quality:
	black --check $(check_dirs)
	ruff $(check_dirs)
style:
	black $(check_dirs)
	ruff $(check_dirs) --fix
