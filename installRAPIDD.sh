#!/bin/bash

run () {

    INSTALLD="$1"
    TARBALLPATH="$2"

    mkdir -p $INSTALLD
    cd $INSTALLD
    ls
    # Make sure there is only a single uncompressed folder starting with EMELA-
    for a in `ls -d RAPIDD*`; do mv $a OLD_${a}_`date '+%Y%m%d%H%M%S'`; done;
    echo "Decompressing rapidd ${TARBALLPATH}"
    tar xvzf ${TARBALLPATH}
    echo "Enter RAPIDD directory and installing DMTCP"
    ls
    cd RAPIDD_for_DM-maddm
    chmod +x instructions_cmake.sh
    ./instructions_cmake.sh
}

run "$@"
