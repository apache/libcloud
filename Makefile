.PHONY: all
all:
	@echo "Run my targets individually!"

env/pyvenv.cfg: dev-requirements.txt
	python -m venv env
	./env/bin/python -m pip install --upgrade pip
	./env/bin/python -m pip install --requirement dev-requirements.txt

.PHONY: dev
dev: env/pyvenv.cfg

.PHONY: lint
lint: env/pyvenv.cfg action.py
	./env/bin/python -m black action.py
	./env/bin/python -m isort action.py
	./env/bin/python -m flake8 --max-line-length 100 action.py
