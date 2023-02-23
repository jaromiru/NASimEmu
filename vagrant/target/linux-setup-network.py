#!/usr/bin/python3

import os, argparse

# -----
parser = argparse.ArgumentParser()
parser.add_argument('-subnetid', type=int)
args = parser.parse_args()

# -----

for subnet in range(10):
    if subnet == args.subnetid:
        continue

    os.system('route add -net 192.168.{remote_subnet}.0/24 gw 192.168.{local_subnet}.10'.format(remote_subnet=subnet, local_subnet=args.subnetid))
