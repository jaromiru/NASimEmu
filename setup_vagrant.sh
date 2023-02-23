#!/bin/bash

if [[ $# -ne 1 ]] ; then
    echo 'Use: setup_vagrant.sh <path_to_scenario.yaml>'
    exit 1
fi

SCENARIO=$1
python3 -m nasimemu.vagrant_gen $SCENARIO --dst vagrant/Vagrantfile --routeros vagrant/firewall.rsc