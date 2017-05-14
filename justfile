# Run `cargo check` plus some basic setup.py sanity checks
check:
	#!/usr/bin/env python3

	import os, re, subprocess, sys
	from distutils.spawn import find_executable

	# Workaround for Manishearth/rust-clippy#1500
	filter_re = re.compile(b"\n?\n[^\n]*error.*: linking with `cc` failed: exit code: 1(.|\n)*syntax error in VERSION script(.|\n)*To learn more, run the command again with --verbose\.")

	print('* Running `setup.py check`...')
	subprocess.call(['python3', 'setup.py', 'check'])

	os.chdir('game_launcher_core')
	if find_executable('cargo-clippy'):
		print("* Running Clippy...")
		clippy = subprocess.Popen(
			['cargo', '+nightly', 'clippy', '--color=always'],
			stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
		clippy_output = clippy.communicate()[0]
		sys.stdout.buffer.write(filter_re.sub(b'', clippy_output))

		# ...and let `cargo check` handle dying on failure instead
		with open(os.devnull, 'wb') as devnull:
			sys.exit(subprocess.call(['cargo', 'check'], 
				stdout=devnull, stderr=devnull))
	else:
		print("* Clippy not found. Using `cargo check`...")
		sys.exit(subprocess.call(['cargo', 'check']))
		# Use sys.exit() rather than check_call() to avoid traceback

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
	@printf "\n--== Clippy Lints ==--\n"
	cd game_launcher_core && cargo +nightly clippy || true # Run clippy for maximum pedantry
	@printf "\n--== Rust Test Suite (on stable) ==--\n"
	cd game_launcher_core && cargo +stable test  # Test with stable so nightly dependencies don't slip in
	@printf "\n--== Python Test Suite ==--\n"
	nosetests3

unittest: rebuild
	cd game_launcher_core && cargo test
	nosetests3

# vim: set ft=make textwidth=100 colorcolumn=101 noexpandtab sw=8 sts=8 ts=8 :
