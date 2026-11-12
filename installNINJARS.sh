#!/bin/bash
#
# Build and install the MadLoop NinjaRS Fortran bridge (libninjars.a, MLReductionLib=8).
# Called by HEPToolInstaller.py, which checks the prerequisites (Linux, GNU Fortran,
# Rust >= rust-version of the bridge, make, cc, m4) before calling this script, and
# which writes lib/ninjars-config.json once this script succeeded.
#
#   installNINJARS.sh <install_dir> <tarball> <fortran_compiler> <source_dir>
#
# CARGO_TARGET_DIR is set by the caller (Cargo build cache kept under the HEPTools prefix).

fail () {
    echo "ERROR: $1"
    echo "ninjars installation FAILED"
    exit 1
}

run () {

    NINJARSINSTALLD="${1%/}"
    TARBALLPATH="$2"
    FORTRANCOMPILER="$3"
    SOURCED="$4"

    echo "== Installing the MadLoop NinjaRS bridge =="
    echo "Install directory : ${NINJARSINSTALLD}"
    echo "Tarball           : ${TARBALLPATH}"
    echo "Fortran compiler  : ${FORTRANCOMPILER} ($(${FORTRANCOMPILER} --version | head -n 1))"
    echo "Fortran target    : $(${FORTRANCOMPILER} -dumpmachine)"
    echo "Rust toolchain    : $(cargo --version) / $(rustc --version)"
    echo "Cargo target dir  : ${CARGO_TARGET_DIR}"
    echo "Note: Cargo fetches the NinjaRS, oneloopmaster and Symbolica revisions pinned in"
    echo "      the bridge Cargo.lock (network access is needed unless they are in the Cargo cache)."

    mkdir -p "${NINJARSINSTALLD}" "${SOURCED}/ninjars_bridge" || fail "cannot create directories"
    echo "Decompressing the NinjaRS bridge"
    tar xzf "${TARBALLPATH}" -C "${SOURCED}/ninjars_bridge" || fail "cannot decompress ${TARBALLPATH}"
    cd "${SOURCED}/ninjars_bridge" || fail "cannot enter the source directory"
    # Accept tarballs with or without a single top-level directory
    if [ ! -f Makefile ]; then
        TOPDIRS=( */ )
        if [ ${#TOPDIRS[@]} -eq 1 ] && [ -d "${TOPDIRS[0]}" ]; then
            cd "${TOPDIRS[0]}" || fail "cannot enter ${TOPDIRS[0]}"
        fi
    fi
    for f in Makefile Cargo.toml Cargo.lock mninjars.f90 smoke.f90; do
        [ -f "$f" ] || fail "${TARBALLPATH} is not a MadLoop NinjaRS bridge tarball (missing $f)"
    done
    echo "Bridge sources in $(pwd)"

    echo "== make install PREFIX=${NINJARSINSTALLD} FC=${FORTRANCOMPILER} =="
    make install PREFIX="${NINJARSINSTALLD}" FC="${FORTRANCOMPILER}" || fail "make install failed"

    # Keep the exact manifest and lock used for this build (provenance of ninjars-config.json)
    cp Cargo.toml Cargo.lock "${NINJARSINSTALLD}/" || fail "cannot copy Cargo.toml/Cargo.lock"

    LIBD="${NINJARSINSTALLD}/lib"
    for f in libninjars.a mninjars.mod ninjars-native-libs.txt ninjars-link-before.txt; do
        [ -s "${LIBD}/$f" ] || fail "make install did not produce ${LIBD}/$f"
    done
    echo "Rust native libraries   : $(cat "${LIBD}/ninjars-native-libs.txt")"
    echo "Compiler runtime before : $(cat "${LIBD}/ninjars-link-before.txt")"

    # Smoke test against the *installed* library, with the link order MadLoop uses:
    # compiler runtime first, then the bridge archive, then the Rust native libraries.
    echo "== Building the smoke test against the installed library =="
    ${FORTRANCOMPILER} -I"${LIBD}" smoke.f90 \
        $(cat "${LIBD}/ninjars-link-before.txt") \
        "${LIBD}/libninjars.a" \
        $(cat "${LIBD}/ninjars-native-libs.txt") \
        -o ninjars_smoke || fail "the smoke test does not compile/link against the installed library"
    echo "== Running the smoke test =="
    ./ninjars_smoke || fail "the smoke test failed (return code $?)"

    echo "Finished building and testing the NinjaRS bridge"
}

run "$@"
