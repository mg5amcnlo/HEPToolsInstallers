#!/bin/bash

run () {

    INSTALLD="$1"
    VERSION="$2"
    TARBALLPATH="$3"

    mkdir -p $INSTALLD
    cd $INSTALLD
    ls
    # Make sure there is only a single uncompressed folder starting with EMELA-
    for a in `ls -d DMTCP*`; do mv $a OLD_${a}_`date '+%Y%m%d%H%M%S'`; done;
    echo "Decompressing DMTCP ${TARBALLPATH}"
    tar xvzf ${TARBALLPATH}
    echo "Enter DMTCP directory and installing DMTCP"
    ls 
    cd dmtcp-*
    ./configure --prefix=$INSTALLD
    make 
    make install
}

run "$@"
