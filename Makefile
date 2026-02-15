COLOR_RESET=\033[0m
COLOR_GREEN=\033[32m
COLOR_YELLOW=\033[33m
COLOR_RED=\033[31m

PYTHON := .venv/bin/python

# Homebrew Tcl/Tk ships read-only; Nuitka's xattr -cr fails on the copies.
TCL_TK_LIB := $(shell $(PYTHON) -c "import tkinter; r=tkinter.Tk(); r.withdraw(); print(r.tk.eval('info library')); r.destroy()" 2>/dev/null)
TK_LIB := $(shell $(PYTHON) -c "import tkinter; r=tkinter.Tk(); r.withdraw(); print(r.tk.eval('set tk_library')); r.destroy()" 2>/dev/null)

.PHONY: help build-ext run profile distribute distribute-fast fix-tcl-perms clean

help: ## Show available targets
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "$(COLOR_GREEN)%-20s$(COLOR_RESET) %s\n", $$1, $$2}'

build-ext: ## Build C extension (moog filter)
	@echo "$(COLOR_YELLOW)Building C extension...$(COLOR_RESET)"
	@$(PYTHON) setup.py build_ext --inplace
	@echo "$(COLOR_GREEN)C extension built.$(COLOR_RESET)"

run: ## Run synth GUI
	@$(PYTHON) -m synth --gui

profile: ## Run performance profiler
	@$(PYTHON) profile_synth.py

fix-tcl-perms: ## Fix Homebrew Tcl/Tk read-only permissions for Nuitka
	@if [ -n "$(TCL_TK_LIB)" ]; then chmod -R u+w "$(TCL_TK_LIB)" "$(TK_LIB)" 2>/dev/null || true; fi

distribute: build-ext fix-tcl-perms ## Build standalone app with Nuitka (optimized)
	@echo "$(COLOR_YELLOW)Building VOOG with Nuitka...$(COLOR_RESET)"
	@mkdir -p dist
	@$(PYTHON) -m nuitka \
		--onefile \
		--standalone \
		--output-filename=voog \
		--output-dir=dist \
		--enable-plugin=tk-inter \
		--follow-imports \
		--lto=yes \
		--python-flag=-m \
		--jobs=8 \
		--nofollow-import-to=numba \
		--nofollow-import-to=llvmlite \
		--assume-yes-for-downloads \
		--show-progress \
		synth
	@echo "$(COLOR_GREEN)Build complete: dist/voog$(COLOR_RESET)"

distribute-fast: build-ext fix-tcl-perms ## Build standalone app with Nuitka (fast, no LTO)
	@echo "$(COLOR_YELLOW)Building VOOG with Nuitka (fast)...$(COLOR_RESET)"
	@mkdir -p dist
	@$(PYTHON) -m nuitka \
		--onefile \
		--standalone \
		--output-filename=voog \
		--output-dir=dist \
		--enable-plugin=tk-inter \
		--follow-imports \
		--python-flag=-m \
		--jobs=8 \
		--nofollow-import-to=numba \
		--nofollow-import-to=llvmlite \
		--assume-yes-for-downloads \
		synth
	@echo "$(COLOR_GREEN)Fast build complete: dist/voog$(COLOR_RESET)"

clean: ## Clean build artifacts
	@echo "$(COLOR_YELLOW)Cleaning...$(COLOR_RESET)"
	@rm -rf dist build *.egg-info
	@find . -name "*.so" -path "*/synth/*" -delete
	@find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
	@echo "$(COLOR_GREEN)Clean.$(COLOR_RESET)"

.DEFAULT_GOAL := help
