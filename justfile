# Run `cargo check` plus some basic setup.py sanity checks
check:
	@echo "$(tput setaf 2)--== Python/rustc Lints (stable) ==--$(tput sgr0)"
	python3 setup.py check
	@echo "$(tput setaf 2)--== Clippy Lints ==--$(tput sgr0)"
	@# (This can be rolled into python3 setup.py check once clippy is in stable channel
	@#  by using the compiler plugin approach to running clippy)
	cd game_launcher_core && cargo +nightly clippy || true

# Rebuild the Rust `core` module
rebuild:
	rm src/core.cpython-*.so || true
	python3 setup.py develop
	#
	# Quick and dirty check for success
	@ls -lh src/core.cpython-*.so

# Run all installed static analysis, plus `cargo +stable test`.
test: check
	@echo "--== Coding Style ==--"
	cd game_launcher_core && cargo fmt -- --write-mode checkstyle | grep -v '<' || true
	@echo "--== Outdated Packages ==--"
	cd game_launcher_core && cargo outdated || true
	@printf "\n--== Dead Internal Documentation Links ==--\n"
	cd game_launcher_core && cargo doc && cargo deadlinks || true
	@printf "\n--== Rust Test Suite (on stable) ==--\n"
	cd game_launcher_core && cargo +stable test  # Test with stable so nightly dependencies don't slip in
	@printf "\n--== Python Test Suite ==--\n"
	nosetests3

unittest: rebuild
	cd game_launcher_core && cargo test
	nosetests3

# vim: set ft=make textwidth=100 colorcolumn=101 noexpandtab sw=8 sts=8 ts=8 :
