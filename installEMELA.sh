#!/bin/bash

run () {

    INSTALLD="$1"
    VERSION="$2"
    TARBALLPATH="$3"
    CMAKEPATH="$4"
    LHAPDFPATH="$5"
    mkdir -p $INSTALLD
    cd $INSTALLD
    # Make sure there is only a single uncompressed folder starting with EMELA-
    for a in eMELA-*; do mv $a OLD_$a; done;
    echo "Decompressing EMELA"
    tar xvzf ${TARBALLPATH}
    echo "Enter EMELA directory and installing EMELA"
    cd eMELA-*
    mkdir build
    cd build
    ${CMAKEPATH}/bin/cmake .. -DCMAKE_INSTALL_PREFIX=$INSTALLD -DWITH_LHAPDF=ON
    make && make install
    cd ..
    echo "Finished installing EMELA"
}

run "$@"
