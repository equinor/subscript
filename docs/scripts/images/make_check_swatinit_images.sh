#!/bin/bash

cd "$(dirname "$0")"

check_swatinit ../../../tests/data/reek/eclipse/model/2_R001_REEK-0.DATA \
    --volplotfile check_swatinit_volplot.png

# Sorry, this csv-file is not under version control:
check_swatinit ~/drogon.csv --plotfile check_swatinit_scatter.png  \
    --eqlnum 4
