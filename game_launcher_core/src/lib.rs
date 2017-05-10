//! GUI-agnostic core functionality for `game_launcher`.
//!
//! **TODO:**
//!
//! * Come up with a proper name to replace the `game_launcher` placeholder.
//! * Also provide language-agnostic C bindings.

#[macro_use]
extern crate cpython;

use cpython::{PyModule, PyResult};

pub mod util;

/// Add binding boilerplate so this can be `import`ed.
py_module_initializer!(core, initcore, PyInit_core, |py, m| {
    m.add(py, "__doc__", "GUI-agnostic core functionality for game_launcher.")?;
    m.add(py, "util", util::into_python_module(&py)?)?;
    Ok(())
});

#[cfg(test)]
mod tests {
    #[test]
    fn it_works() {}
}
