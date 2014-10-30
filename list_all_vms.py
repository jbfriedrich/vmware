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
parser.add_argument('-s', '--server', help='vCenter server name or IP address',
                    required=True)
parser.add_argument('-u', '--username', help='vCenter username', required=True)
parser.add_argument('-p', '--password', help='vCenter password')
parser.add_argument('-v', '--verbose', help='more information displayed',
                    action='store_true')

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

# Function to display VM information. stupid tabs variable included, that 
# is supposed to help displaying folder hierarchy. Working on new output format
def list_vm_info(virtual_machine, tabs=1):
    summary = virtual_machine.summary
    print tabs * 3 * ' ' + '-> ' + summary.config.name
    print tabs * 3 * ' ' + '   ' + 'Distribution     :', summary.config.guestFullName
    print tabs * 3 * ' ' + '   ' + 'Hostname         :', summary.guest.hostName
    print tabs * 3 * ' ' + '   ' + 'UUID             :', summary.config.uuid
    print tabs * 3 * ' ' + '   ' + 'IP address       :', summary.guest.ipAddress
    print tabs * 3 * ' ' + '   ' + 'vCPU             :', summary.config.numCpu
    print tabs * 3 * ' ' + '   ' + 'vRAM (MB)        :', summary.config.memorySizeMB
    print tabs * 3 * ' ' + '   ' + 'Ethernet cards   :', summary.config.numEthernetCards
    print tabs * 3 * ' ' + '   ' + 'vDisks           :', summary.config.numVirtualDisks
    print tabs * 3 * ' ' + '   ' + 'VM path          :', summary.config.vmPathName
    print tabs * 3 * ' ' + '   ' + 'Power state      :', summary.runtime.powerState
    
    # If the object has a currentSnapshot, we want to decend the hierarchy down
    # max 3 levels (root snapshot + 2 additional snapshots). If there is more,
    # the user needs to take a look with the vSphere client    
    snapshot = virtual_machine.snapshot
    if hasattr(snapshot, 'currentSnapshot'):
        print tabs * 3 * ' ' + '   ' + 'Snapshots        : Yes'
        # Getting info about the root snapshot and displaying it
        root_snapshot = snapshot.rootSnapshotList[0]
        root_snapshot_name = root_snapshot.name
        root_snapshot_date = root_snapshot.createTime
        print tabs * 3 * ' ' + '   ' + 'Latest snapshots :'
        print tabs * 3 * ' ' + '     \\- ' + "%s: %s" % (root_snapshot_date,
                                                         root_snapshot_name)
        # If the root snapshot has children, lets see its ugly faces
        if (root_snapshot.childSnapshotList):
            for first_snapshot in root_snapshot.childSnapshotList:
                print tabs * 3 * ' ' + '       \\- ' + "%s: %s" % (first_snapshot.createTime,
                                                                   first_snapshot.name)                
                # Let's see if the first snapshots has any child objects
                if (first_snapshot.childSnapshotList):
                    for second_snapshot in first_snapshot.childSnapshotList:
                        print tabs * 3 * ' ' + '         \\- ' + "%s: %s" % (second_snapshot.createTime,
                                                                             second_snapshot.name)
                        # If there are more snapshots, go use the vSphere Client
                        if (second_snapshot.childSnapshotList):
                            print tabs * 3 * ' ' + '           !!  ' + 'WARNING: Only 3 levels of' \
                            ' snapshots supported, but this Virtual Machine has more'
    # VM has no snapshots :(
    else:
        print tabs * 3 * ' ' + '   ' + 'Snapshots        : No'
    # We need some distance (divider)
    print ""

# Display the folder names in a funky way.
# The 90's called, they want their ASCII back    
def print_folder_name(folder, tabs=1):
    print tabs * 2 * ' ' + '== ' + folder.name + "\n"

# We just descend recursively until we reached max depth of 20
def identify_item(data_item, depth=1):
    maxdepth = 20
    if depth > maxdepth:
        return            

    # If the found object is a folder, we want to print it's name
    if isinstance(data_item, vim.Folder):
        print_folder_name(data_item, depth)

    # If the object is a virtual machine, we want to display it's information
    elif isinstance(data_item, vim.VirtualMachine):
        list_vm_info(data_item, depth)

    # If the object has child entities, we follow down the rabbit hole until we
    # reach maxdepth and identify every object on our way
    if hasattr(data_item, 'childEntity'):
        data_item_list = data_item.childEntity
        for item in data_item_list:
            identify_item(item, depth + 1)
        return

# Start program
if __name__ == "__main__":
    for datacenter in datacenters:
        if verbose:
            dc_name = datacenter.name
            print "\n--== Datacenter:", dc_name, "==--\n"

        vm_folder = datacenter.vmFolder
        item_list = vm_folder.childEntity
    
        for item in item_list:
            identify_item(item)

    # Clean exit    
    sys.exit(0)