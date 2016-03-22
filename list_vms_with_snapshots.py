#!/usr/bin/env python

# Importing required modules
import  argparse
import  sys
import  getpass
from    pb_vmware   import  *

# Start program
if __name__ == "__main__":
    # Parsing arguments
    parser = argparse.ArgumentParser(
        prog='list_vms_with_snapshots.py'
    )
    parser.add_argument(
        '-s', '--server',
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
    for item in item_list:
        list_vms_with_snapshots(item)
    # Clean exit
    connect.Disconnect(instance)
    sys.exit(0)
