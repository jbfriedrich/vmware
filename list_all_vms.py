#!/usr/bin/env python

import argparse
import sys
from pyVim import connect
from pyVmomi import vim

parser = argparse.ArgumentParser(prog='list_all_vms.py')
parser.add_argument("server", help="vCenter server name or IP address")
parser.add_argument("username", help="vCenter username")
parser.add_argument("password", help="vCenter password")
args = parser.parse_args()

hostname = args.server
username = args.username
passwd = args.password

instance = connect.SmartConnect(host=hostname,
                                user=username,
                                pwd=passwd)

content = instance.RetrieveContent()

datacenters = content.rootFolder.childEntity

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
    
    snapshot = virtual_machine.snapshot
    if hasattr(snapshot, 'currentSnapshot'):
        print tabs * 3 * ' ' + '   ' + 'Snapshots        : Yes'
        root_snapshot = snapshot.rootSnapshotList[0]
        root_snapshot_name = root_snapshot.name
        root_snapshot_date = root_snapshot.createTime
        print tabs * 3 * ' ' + '   ' + 'Latest snapshots :'
        print tabs * 3 * ' ' + '     \\- ' + "%s: %s" % (root_snapshot_date,
                                                         root_snapshot_name)
                                                           
        if (root_snapshot.childSnapshotList):
            for first_snapshot in root_snapshot.childSnapshotList:
                print tabs * 3 * ' ' + '       \\- ' + "%s: %s" % (first_snapshot.createTime,
                                                                   first_snapshot.name)                
                if (first_snapshot.childSnapshotList):
                    for second_snapshot in first_snapshot.childSnapshotList:
                        print tabs * 3 * ' ' + '         \\- ' + "%s: %s" % (second_snapshot.createTime,
                                                                             second_snapshot.name)
                        if (second_snapshot.childSnapshotList):
                            print tabs * 3 * ' ' + '           !!  ' + 'WARNING: Only 3 levels of' \
                            ' snapshots supported, but this Virtual Machine has more'

    else:
        print tabs * 3 * ' ' + '   ' + 'Snapshots        : No'

    print ""
    
def print_folder_name(folder, tabs=1):
    print tabs * 2 * ' ' + '== ' + folder.name + "\n"
    
def identify_item(data_item, depth=1):
    maxdepth = 20
    if depth > maxdepth:
        return            

    if isinstance(data_item, vim.Folder):
        print_folder_name(data_item, depth)
        
    elif isinstance(data_item, vim.VirtualMachine):
        list_vm_info(data_item, depth)
        
    if hasattr(data_item, 'childEntity'):
        data_item_list = data_item.childEntity
        for item in data_item_list:
            identify_item(item, depth + 1)
        return


# Start program
if __name__ == "__main__":
    for datacenter in datacenters:
        dc_name = datacenter.name
        vm_folder = datacenter.vmFolder
        item_list = vm_folder.childEntity
        print "\n--== Datacenter:", dc_name, "==--\n"
    
        for item in item_list:
            identify_item(item)
        
    sys.exit(0)