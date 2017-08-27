#!/usr/bin/env python
"""List all Virtual Machines."""

# Importing required modules
import argparse
import sys
import getpass
from pb_vmware import vcenter_connect, vcenter_disconnect, vm_info

# Start program
if __name__ == "__main__":
    # Parsing arguments
    parser = argparse.ArgumentParser(
        prog='list_all_vms.py'
    )
    parser.add_argument(
        '-c',
        '--csv',
        help='print VM info as CSV',
        action='store_true'
    )
    parser.add_argument(
        '-s',
        '--server',
        help='vCenter server name or IP address',
        required=True
    )
    parser.add_argument(
        '-u',
        '--username',
        help='vCenter username',
        required=True
    )
    parser.add_argument(
        '-p',
        '--password',
        help='vCenter password'
    )
    parser.add_argument(
        '-v',
        '--verbose',
        help='more information displayed',
        action='store_true'
    )
    args = parser.parse_args()
    verbose = args.verbose
    hostname = args.server
    username = args.username
    passwd = args.password
    csv_style = args.csv
    # Asking user for password if not specified on the commandline
    if passwd is None:
        passwd = getpass.getpass()

    instance, content, datacenters, datacenter, vm_folder = vcenter_connect(
        hostname,
        username,
        passwd
    )

    vm_folder = datacenter.vmFolder
    item_list = vm_folder.childEntity
    if csv_style is True:
        print ('VM ID,VM name,VM UUID,State,IP address,Hostname, \
               GuestOS,vCPU,vRAM,# of vDisks,# of vNICs,Network 1, \
               Network 2,Network 3,Network 4,VMware Tools,Folder,VM path'
               )
    for item in item_list:
        if csv_style is True:
            vm_info(item, 'csv', content)
        else:
            vm_info(item, 'text', content)
    # Clean exit
    vcenter_disconnect(instance)
    sys.exit(0)
