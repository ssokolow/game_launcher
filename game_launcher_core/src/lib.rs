#[macro_use] extern crate cpython;

use cpython::{PyModule, PyResult};

pub mod util;

// add bindings to the generated python module
// N.B: names: "librust2py" must be the name of the `.so` or `.pyd` file
py_module_initializer!(core,
                       initcore,
                       PyInit_core, |py, m| {
    try!(m.add(py, "__doc__", "GUI agnostic core functionality for game_launcher."));

    let py_util = try!(util::get_python_module(&py));
    try!(m.add(py, "util", py_util));
    Ok(())
});

#[cfg(test)]
mod tests {
    #[test]
    fn it_works() {
    }
}
