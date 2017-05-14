//! GUI-agnostic core functionality for `game_launcher`.
//!
//! **TODO:**
//!
//! * Come up with a proper name to replace the `game_launcher` placeholder.
//! * Also provide language-agnostic C bindings.

// Make rustc's built-in lints more strict (I'll opt back out selectively)
#![warn(warnings)]

// FIXME: Figure out how to keep this from complaining about every use of `lazy_static!`
//#![warn(missing_docs)]

// TODO: Once clippy is included in stable, don't feature-gate my warnings
// (Or at least find a way to enable build-time and `cargo clippy`-time with a single feature)
// Set clippy into a whitelist-based configuration so I'll see new lints as they come in
#![cfg_attr(feature="cargo-clippy", warn(clippy_pedantic, clippy_restrictions))]

// Opt out of the lints I've seen and don't want
#![cfg_attr(feature="cargo-clippy", allow(assign_ops, float_arithmetic, shadow_reuse))]

#[macro_use]
extern crate cpython;

use cpython::{PyModule, PyResult};

pub mod util;

/// Add binding boilerplate so this can be `import`ed.
py_module_initializer!(core, initcore, PyInit_core, |py, m| {
    m.add(py, "__doc__", "GUI-agnostic core functionality for writing game launchers")?;
    m.add(py, "util", util::into_python_module(&py)?)?;
    Ok(())
});

#[cfg(test)]
mod tests {
    #[test]
    fn it_works() {}
}
