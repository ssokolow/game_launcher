rebuild:
	rm src/core.cpython-*.so || true
	python3 setup.py develop
	#
	# Quick and dirty check for success
	@ls -lh src/core.cpython-*.so
	@python -c 'from src import core; print(core.__doc__)'
	@python -c 'from src import core; print(dir(core.util.constants))'

# vim: set ft=make textwidth=100 colorcolumn=101 noexpandtab sw=8 sts=8 ts=8 :
