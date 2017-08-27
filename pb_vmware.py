#!/usr/bin/env python
"""Helper module for easier pyVmomi use.

Yes, these are my first bigger Python scripts and this is my first foolish
and very amateur try of a Python module. Maybe, one day, it will be a real
module and make everything right.
"""

from pyVim import connect
from pyVmomi import vim
import time
import sys
import ssl       # imported to define SSL context (see below)
import requests  # imported to disable SSL warning


# returns everything we need to work with vCenter
def vcenter_connect(host, username, password):
    """Connect to vCenter and return all variables needed."""
    # No warnign for self signed SSL certificates
    requests.packages.urllib3.disable_warnings()
    # Disabling SSL certificate verification
    # Fix for python 2.7.10+ and vSphere 6. For details see:
    # https://github.com/mistio/mist.io/issues/691
    # https://github.com/vmware/pyvmomi/issues/212
    # Disabling SSL certificate verification
    context = ssl.SSLContext(ssl.PROTOCOL_TLSv1)
    context.verify_mode = ssl.CERT_NONE
    instance = connect.SmartConnect(
        host=host,
        user=username,
        pwd=password,
        sslContext=context
    )
    # Getting instance content
    content = instance.RetrieveContent()
    datacenters = content.rootFolder.childEntity
    datacenter = datacenters[0]
    vm_folder = datacenter.vmFolder

    return instance, content, datacenters, datacenter, vm_folder


# create folder
def create_folder(content, vm_folder, foldername):
    """Create folder in VM view."""
    if (get_obj(content, 'folder', foldername)) is None:
        vm_folder.CreateFolder(foldername)
        print "Folder '%s' created" % (foldername)
    else:
        print "Folder with name '%s' already exists" % (foldername)


def get_obj(content, type, name):
    """Get object from vCenter server inventory."""
    vimtype = None
    if type == 'datacenter':
        vimtype = [vim.Datacenter]
    elif type == 'cluster':
        vimtype = [vim.ClusterComputeResource]
    elif type == 'respool':
        vimtype = [vim.ResourcePool]
    elif type == 'folder':
        vimtype = [vim.Folder]
    elif type == 'vm':
        vimtype = [vim.VirtualMachine]
    elif type == 'template':
        vimtype = [vim.VirtualMachine]
    elif type == 'datastore':
        vimtype = [vim.Datastore]
    elif type == 'dstorecluster':
        vimtype = [vim.StoragePod]
    elif type == 'network':
        vimtype = [vim.Network]
    elif type == 'dvsportgroup':
        vimtype = [vim.dvs.DistributedVirtualPortgroup]

    obj = None
    container = content.viewManager.CreateContainerView(
        content.rootFolder,
        vimtype,
        True
    )
    container_object_list = container.view
    # destroying the container to free up resources on the vCenter
    container.Destroy()
    for container_object in container_object_list:
        if container_object.name == name:
            obj = container_object
            break

    return obj


def get_dvsportgroup_by_key(content, key):
    """Get DVS port group by key from vCenter inventory."""
    vimtype = [vim.dvs.DistributedVirtualPortgroup]
    dvsportgroup = None
    container = content.viewManager.CreateContainerView(
        content.rootFolder,
        vimtype,
        True
    )
    obj_list = container.view
    # destroying the container to free up resources on the vCenter
    container.Destroy()
    for obj in obj_list:
        if obj.key == key:
            dvsportgroup = obj
            break
    return dvsportgroup


def get_dvsportgroup_by_name(content, name):
    """Get DVS port group by name from vCenter inventory."""
    vimtype = [vim.dvs.DistributedVirtualPortgroup]
    dvsportgroup = None
    container = content.viewManager.CreateContainerView(
        content.rootFolder,
        vimtype,
        True
    )
    obj_list = container.view
    # destroying the container to free up resources on the vCenter
    container.Destroy()
    for obj in obj_list:
        if obj.name == name:
            dvsportgroup = obj
            break
    return dvsportgroup


def print_vm_info(vm):
    """Print some VM info (including snapshots)."""
    summary = vm.summary
#   config = vm.config
    print 'VM name        :', summary.config.name
    print 'Guest OS       :', summary.config.guestFullName
    print 'Hostname       :', summary.guest.hostName
    print 'UUID           :', summary.config.uuid
    print 'Folder         :', vm.parent.name
    print 'State          :', summary.runtime.powerState
    print 'Tools status   :', summary.guest.toolsRunningStatus
    print 'IP address     :', summary.guest.ipAddress
    print 'vCPU           :', summary.config.numCpu
    print 'vRAM (MB)      :', summary.config.memorySizeMB
    print 'Ethernet cards :', summary.config.numEthernetCards
    print 'vDisks         :', summary.config.numVirtualDisks
    print 'VM path        :', summary.config.vmPathName

    # If the object has a currentSnapshot, we want to decend the hierarchy down
    # max 3 levels (root snapshot + 2 additional snapshots). If there is more,
    # the user needs to take a look with the vSphere client
    snapshot = vm.snapshot
    if hasattr(snapshot, 'currentSnapshot'):
        sys.stdout.write('Snapshots      : ')
        # Getting info about the root snapshot and displaying it
        root_snapshot = snapshot.rootSnapshotList[0]
        root_snapshot_name = root_snapshot.name
        root_snapshot_date = root_snapshot.createTime
        print "%s: %s" % (root_snapshot_date, root_snapshot_name)
        # If the root snapshot has children, lets see its ugly faces
        if (root_snapshot.childSnapshotList):
            for first_snapshot in root_snapshot.childSnapshotList:
                print "                 %s: %s" % (
                    first_snapshot.createTime,
                    first_snapshot.name
                )
                # Let's see if the first snapshots has any child objects
                if (first_snapshot.childSnapshotList):
                    for second_snapshot in first_snapshot.childSnapshotList:
                        print "                 %s: %s" % (
                            second_snapshot.createTime,
                            second_snapshot.name
                        )
                        # To see more snapshots, use the vSphere Client
                        if (second_snapshot.childSnapshotList):
                            print '                 WARNING:' \
                                ' This VM has more than 3 snapshots'
    # VM has no snapshots :(
    else:
        print 'Snapshots      : No'
    # We need some distance (divider)
    print ""


def print_csv_vm_info(vm, content):
    """Detailed VM information in CSV format."""
    vm_name = vm.summary.config.name
    guest_os = vm.summary.config.guestFullName
    hostname = vm.summary.guest.hostName
    uuid = vm.summary.config.uuid
    folder = vm.parent.name
    state = vm.summary.runtime.powerState
    tools_state = vm.summary.guest.toolsRunningStatus
    ip_address = vm.summary.guest.ipAddress
    vcpu = vm.summary.config.numCpu
    vram = vm.summary.config.memorySizeMB
    vnics = vm.summary.config.numEthernetCards
    vdisks = vm.summary.config.numVirtualDisks
    vmpath = vm.summary.config.vmPathName
    slot = 1
    maxslots = 4
    networks = []
    """
    The function prints the data in the following order:
    VM ID,VM name,VM UUID,State,IP address,Hostname,GuestOS,vCPU,vRAM,
    no. of vDisks, no. of vNICs,Network 1,Network 2,Network 3,Network 4,
    VMware Tools, Folder,VM path
    """
    for device in vm.config.hardware.device:
        # If the device is our network device
        if isinstance(device, vim.vm.device.VirtualEthernetCard):
            # We only print out a max of 4 networks
            if slot > maxslots:
                return
            try:
                old_network_pgkey = device.backing.port.portgroupKey
                dvsportgrp = get_dvsportgroup_by_key(content,
                                                     old_network_pgkey
                                                     )
                networks.append(dvsportgrp.name)
            except:
                vswitch_name = device.backing.deviceName
                networks.append(vswitch_name)
            slot + 1

    open_slots = maxslots - len(networks)
    while open_slots > 0:
        networks.append('n/a')
        open_slots -= 1

    network1 = networks[0]
    network2 = networks[1]
    network3 = networks[2]
    network4 = networks[3]

    print "%s,%s,%s,%s,%s,%s,%s,%s,%s,\
        %s,%s,%s,%s,%s,%s,%s,%s,%s" % (vm,
                                       vm_name,
                                       uuid,
                                       state,
                                       ip_address,
                                       hostname,
                                       guest_os,
                                       vcpu,
                                       vram,
                                       vdisks,
                                       vnics,
                                       network1,
                                       network2,
                                       network3,
                                       network4,
                                       tools_state,
                                       folder,
                                       vmpath
                                       )


def vm_info(data_item, type, content, depth=1):
    """We just descend recursively until we reached max depth of 20."""
    maxdepth = 25
    if depth > maxdepth:
        return
    # If the object is a virtual machine, we want to display it's information
    if isinstance(data_item, vim.VirtualMachine):
        if type == 'csv':
            print_csv_vm_info(data_item, content)
        elif type == 'text':
            print_vm_info(data_item)
        else:
            print 'Wrong type, neither text nor csv'
            return
    # If the object has child entities, we follow down the rabbit hole until we
    # reach maxdepth and identify every object on our way
    if hasattr(data_item, 'childEntity'):
        data_item_list = data_item.childEntity
        for item in data_item_list:
            vm_info(item, type, content, depth + 1)
        return


def list_vms_with_snapshots(item):
    """Look through all objects and identify Virtual Machines."""
    if isinstance(item, vim.VirtualMachine):
        if check_for_snapshots(item):
            print_vm_info(item)

    if hasattr(item, 'childEntity'):
        item_list = item.childEntity
        for subitem in item_list:
            list_vms_with_snapshots(subitem)


def check_if_template(object):
    """Check if object is a VM template."""
    if object.config.template is True:
        return True
    else:
        return False


def check_for_snapshots(virtual_machine):
    """Check if the Virtual Machine has any snapshots."""
    snapshot = virtual_machine.snapshot
    if hasattr(snapshot, 'currentSnapshot'):
        return True


def check_on_task(task):
    """Check on a task sent to vCenter."""
    progress = ['|', '/', '-', '\\']
    sys.stdout.write('Progress:  ')
    sys.stdout.flush()
    while task.info.state == vim.TaskInfo.State.running:
        for i in progress:
            sys.stdout.write("\b%s" % i)
            sys.stdout.flush()
            time.sleep(0.2)

    if task.info.state == vim.TaskInfo.State.success:
        print "\bDone"
        print 'Task successfully completed'
    else:
        print 'Task failed! Check VMware logs:'
        print task.info.error


def clone_vm(template, target, folder, datastore, respool):
    """Clone a Virtual Machine."""
    print 'Preparing relocating specification...'
    relspec = vim.vm.RelocateSpec()
    relspec.datastore = datastore
    relspec.pool = respool
    print 'Preparing cloning specification...'
    clonespec = vim.vm.CloneSpec(
        powerOn=False,
        template=False,
        location=relspec
    )
    print "Starting cloning process for new VM '%s'..." % target
    task = template.Clone(
        name=target,
        folder=folder,
        spec=clonespec
    )
    check_on_task(task)

# def vm_change_host(vm, target_host, respool):
# def vm_change_dstore(vm, target_dstore, respool):


def vcenter_disconnect(service_instance):
    """Disconnect from vCenter after our work is done."""
    connect.Disconnect(service_instance)


# Start program
if __name__ == "__main__":
    print "This is a module and cannot directly be used"
    sys.exit(0)
