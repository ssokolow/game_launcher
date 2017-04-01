#[macro_use] extern crate cpython;

use cpython::{PyResult, Python};

// add bindings to the generated python module
// N.B: names: "librust2py" must be the name of the `.so` or `.pyd` file
py_module_initializer!(core,
                       initcore,
                       PyInit_core, |py, m| {
    try!(m.add(py, "__doc__", "GUI agnostic core functionality for game_launcher."));
    Ok(())
});

#[cfg(test)]
mod tests {
    #[test]
    fn it_works() {
    }
}
