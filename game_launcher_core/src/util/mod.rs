//! **TODO:** Refactor the Python dependency out or make it optional

use cpython::{PyModule, PyResult, Python};

}

pub mod constants;
pub mod naming;
// TODO: I need to solve:
//
// * Ensuring a consistent sort order when using this as a sorting key
// * Using variant names as labels in the GUI
// * Deciding whether I need to leave room for new variants
// * Finding a way to either put the doc comments on the same line or shut up clippy about them
pub mod executables {
    #[repr(C)]
    pub enum Role {
        Play = -2,
        Configure,
        Unknown,
        Update,
        Install,
        Uninstall,
    }
    // TODO: Implement ToPyObject
}

/// Called by the top-level `py_module_initializer!` macro to export the symbols in this file
///
/// TODO: come up with a macro to remove all of the repeated boilerplate in this.
pub fn into_python_module(py: &Python) -> PyResult<PyModule> {
    let py_util = PyModule::new(*py, "util")?;
    py_util.add(*py, "constants", constants::into_python_module(py)?)?;
    py_util.add(*py, "naming", naming::into_python_module(py)?)?;
    Ok(py_util)
}
