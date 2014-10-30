#!/usr/bin/env python

# Importing required modules
import argparse
import sys
import getpass
from pyVim import connect
from pyVmomi import vim
import requests             # Imported to disable SSL warning

# Parsing arguments
parser = argparse.ArgumentParser(prog='list_vms_with_snapshots.py')
parser.add_argument('-s', '--server', help='vCenter server name or IP address', required=True)
parser.add_argument('-u', '--username', help='vCenter username', required=True)
parser.add_argument('-p', '--password', help='vCenter password')
parser.add_argument('-v', '--verbose', help='more information displayed')

args = parser.parse_args()

verbose = args.verbose
hostname = args.server
username = args.username
passwd = args.password

# Asking user for password if not specified on the commandline
if passwd is None:
    passwd = getpass.getpass()

# Since all my VMware instances are using self-signed certificates, to which
# I do not necessarily have access to the root CA, SSL warnings are disabled
requests.packages.urllib3.disable_warnings()

# Connectign to vCenter
instance = connect.SmartConnect(host=hostname,
                                user=username,
                                pwd=passwd)
# Getting instance content
content = instance.RetrieveContent()

# Accessing datacenter folder directly under root folder. For more information
# about the hierarchy, see
# http://vmware.github.io/pyvmomi-community-samples/assets/vchierarchy.pdf
datacenters = content.rootFolder.childEntity

# Function to look through all objects and identify Virtual Machines
def find_vms_with_snapshots(item):
    if isinstance(item, vim.VirtualMachine):
        if check_for_snapshots(item):
            display_snapshot_info(item)
        
    if hasattr(item, 'childEntity'):
        item_list = item.childEntity
        for subitem in item_list:
            find_vms_with_snapshots(subitem)

# Check if the Virtual Machine has any snapshots
def check_for_snapshots(virtual_machine):
    snapshot = virtual_machine.snapshot
    if hasattr(snapshot, 'currentSnapshot'):
        return True

# Display Virtual Machine and Snapshot information
def display_snapshot_info(virtual_machine):
    summary = virtual_machine.summary
    snapshot = virtual_machine.snapshot
    
    # We want at least the VM name and it's UUID
    vm_name = summary.config.name
    vm_uuid = summary.config.uuid
    print ',' + 79 * '-'
    print '| Virtual Machine :', vm_name
    print '| VMware UUID     :', vm_uuid
    print '|' + 79 * '-'
    
    # Getting information about the root snapshot
    root_snapshot = snapshot.rootSnapshotList[0]
    root_snapshot_name = root_snapshot.name
    root_snapshot_date = root_snapshot.createTime
    print '|' + 36 * ' ' + 'Snapshots'
    print '|' + 79 * '-'
    print '|' + 17 * ' ' + 'Date' + 19 * ' ' + '|' + 16 * ' ' + 'Name'
    print '|' + 79 * '-'    
    print '| ' + str(root_snapshot_date) + '       | ' + root_snapshot_name
    # If there are child objects, we want information about them as well
    if (root_snapshot.childSnapshotList):
        for first_snapshot in root_snapshot.childSnapshotList:
            first_snapshot_name = first_snapshot.name
            first_snapshot_date = first_snapshot.createTime
            print '| \\__', first_snapshot_date, '  |', first_snapshot_name
            # Has the child object a child object? Grandkids! \ o /
            if (first_snapshot.childSnapshotList):
                for second_snapshot in first_snapshot.childSnapshotList:
                    second_snapshot_name = second_snapshot.name
                    second_snapshot_date = second_snapshot.createTime
                    print '|   \\__', second_snapshot_date, '|', second_snapshot_name
                    # If there are more snapshots, go use the vSphere Client
                    if (second_snapshot.childSnapshotList):
                        print '|' + 79 * '-'
                        print '|  !! WARNING - Only 3 levels of snapshots ' \
                        'supported, but this VM has more !!'
    print '`' + 79 * '-'
    print ""

def print_dc_name(name):
    print '//' + 78 * '='
    print '|| Datacenter: ', name
    print '\\\\' + 78 * '='
    print ''

# Coming soon. Optional display of days since snapshot was created instead of
# a cryptic timestamp.
def calculate_snapshot_age():
    print 'Not implemented yet.'

# Start program
if __name__ == "__main__":
    for datacenter in datacenters:
        if verbose:
            dc_name = datacenter.name
            print_dc_name(dc_name)

        vm_folder = datacenter.vmFolder
        item_list = vm_folder.childEntity

        for item in item_list:
            find_vms_with_snapshots(item)

    # Clean exit
    sys.exit(0)