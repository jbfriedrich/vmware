#!/usr/bin/env python

# Importing required modules
import  argparse
import  sys
import  getpass
from    pb_vmware   import *

# Start program
if __name__ == "__main__":
    # Parsing arguments
    parser = argparse.ArgumentParser(
        prog='migrate_to_cluster.py'
    )
    parser.add_argument(
        '-s',
        '--server',
        help='vCenter server name or IP address',
        required=True
    )
    parser.add_argument(
        '-t',
        '--target',
        help='vMotion target host or cluster',
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
        '-m',
        '--virtualmachine',
        help='Virtual Machine',
        required=True
    )
    parser.add_argument(
        '-d',
        '--datastore',
        help='datastore or datastore cluster',
        required=True
    )
    parser.add_argument(
        '-v',
        '--verbose',
        help='more information displayed',
        action='store_true'
    )
    args = parser.parse_args()
    # General arguments
    verbose             =   args.verbose
    # Arguments for connecting to the vCenter
    hostname            =   args.server
    username            =   args.username
    passwd              =   args.password
    # Arguments for migrating VMs
    vm_name             =   args.virtualmachine
    target_name         =   args.target
    dstore_name         =   args.datastore

    # Asking user for password if not specified on the commandline
    if passwd is None:
        passwd  =   getpass.getpass()

    # Connecting to the vCenter
    print "Connecting to '%s' as user '%s'..." % (hostname, username)
    instance, content, datacenters, datacenter, vm_folder = vcenter_connect(
        hostname,
        username,
        passwd
    )
    # Getting vCenter objects to all the names
    vm_folder           =   datacenter.vmFolder
    item_list           =   vm_folder.childEntity
    destination_cluster =   get_obj(content, 'cluster', target_name)
    dstore_cluster      =   get_obj(content, 'dstorecluster', dstore_name)
    virtual_machine     =   get_obj(content, 'vm', vm_name)
    # Important for the storage placement spec later
    migrate_priority    =   vim.VirtualMachine.MovePriority.defaultPriority
    # Getting the cluster's default resource pool
    resource_pool       =   destination_cluster.resourcePool

    # Migrating the VM to a host in the target cluster. I am using fully DRS
    # so I use the cluster's default resource pool instead of a single host
    # in Migrate() so the right host gets chosen automagically
    print "Migrating %s to cluster %s (Respool: %s)" % (virtual_machine.name, destination_cluster.name, resource_pool.name)
    task = virtual_machine.Migrate(pool=resource_pool, priority=migrate_priority)
    check_on_task(task)

    # Creating an empty list for all nics that need to be reconfigured
    device_change = []
    # Going through all devices in the VM hardware config
    for device in virtual_machine.config.hardware.device:
        # If the device is our network device
        if isinstance(device, vim.vm.device.VirtualEthernetCard):
            old_network_pgkey	= device.backing.port.portgroupKey
            old_network			= get_dvsportgroup_by_key(content, old_network_pgkey)
            old_network_name	= old_network.name

            # The new network name in my case, is the old one with a suffix
            new_network_name	= old_network_name + '-10GbE'
            new_network			= get_dvsportgroup_by_name(content, new_network_name)

            # Preparing the DVS port connection
            dvs_port_conn = vim.dvs.PortConnection()
            dvs_port_conn.portgroupKey	= new_network.key
            dvs_port_conn.switchUuid = new_network.config.distributedVirtualSwitch.uuid

            # Preparing NIC specification and integration DVS port conn spec
            nicspec = vim.vm.device.VirtualDeviceSpec()
            nicspec.operation = vim.vm.device.VirtualDeviceSpec.Operation.edit
            nicspec.device = device
            nicspec.device.wakeOnLanEnabled = True
            nicspec.device.backing = vim.vm.device.VirtualEthernetCard.DistributedVirtualPortBackingInfo()
            nicspec.device.backing.port = dvs_port_conn
            nicspec.device.connectable = vim.vm.device.VirtualDevice.ConnectInfo()
            nicspec.device.connectable.connected = True
            nicspec.device.connectable.startConnected = True
            nicspec.device.connectable.allowGuestControl = True

            # Add vNIC specification to our empty list
            device_change.append(nicspec)
            break
            # TBD: VMs with more than one network card need to be handled as well

    # Applying the changes to the virtual network device
    config_spec = vim.vm.ConfigSpec(deviceChange=device_change)
    print "Migrating vNIC network from %s to %s for VM %s" % (old_network_name, new_network_name, virtual_machine.name)
    task = virtual_machine.ReconfigVM_Task(config_spec)
    check_on_task(task)

    # To be able to storage migrate our VMs vDisks to a fully automated
    # storage cluster, we need to build several specifications. These specifications
    # are intertwined.
    # PodSelectionSpec -+-> StoragePlacementSpec
    # RelocateSpec    __|
    # More details at https://github.com/vmware/pyvmomi/blob/master/docs/vim/StorageResourceManager.rst#recommendDatastores
    pod_selection_spec = vim.storageDrs.PodSelectionSpec(
        storagePod = dstore_cluster
    )
    vm_relocate_spec = vim.vm.RelocateSpec(
        pool = resource_pool
    )
    storage_placement_spec = vim.storageDrs.StoragePlacementSpec(
        type                = 'relocate',
        priority            = migrate_priority,
        vm                  = virtual_machine,
        podSelectionSpec    = pod_selection_spec,
        relocateSpec        = vm_relocate_spec
    )
    # After the StoragePlacementSpec is built, we use it to get a storage
    # recommendation from the SDRS cluster, i.e. which datastore from the
    # cluster we should use for our relocation
    storagemgr = content.storageResourceManager
    storage_rec = storagemgr.RecommendDatastores(
        storageSpec=storage_placement_spec
    )
    # We get several recommendations, we use the first one that is given to us
    storage_rec_key	= storage_rec.recommendations[0].key
    # Starting the actual relocation task and checking for progress
    print "Migrating %s to datastore cluster %s (Respool: %s)" % (virtual_machine.name, dstore_cluster.name, resource_pool.name)
    task = storagemgr.ApplyStorageDrsRecommendation_Task(storage_rec_key)
    check_on_task(task)
    vcenter_disconnect(instance)
