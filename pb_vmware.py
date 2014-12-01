#!/usr/bin/env python

# Yes, these are my first Python scripts and this is my first foolish and very
# amateur try of a Python module. Maybe, one day, it will be a real module

from pyVim import connect
from pyVmomi import vim
import time
import sys
import requests # imported to disable SSL warning

# returns everything we need to work with vCenter    
def vcenter_connect(host, username, password):
    # No warnign for self signed SSL certificates
    requests.packages.urllib3.disable_warnings()
    instance    =   connect.SmartConnect(host=host,
                                         user=username,
                                         pwd=password)
    # Getting instance content
    content     =   instance.RetrieveContent()
    datacenters =   content.rootFolder.childEntity
    datacenter  =   datacenters[0]
    vm_folder   =   datacenter.vmFolder
    
    return instance, content, datacenters, datacenter, vm_folder

# create folder
def create_folder(content, vmfolder, foldername):
    if (get_obj(content, 'folder', foldername)) is None:
        vmfolder.CreateFolder(foldername)
        print "Folder '%s' created" % (foldername)
    else:
        print "Folder with name '%s' already exists" % (foldername)

# get object from vCenter server inventory
def get_obj(content, type, name):
    vimtype = None
    if type == 'datacenter':
        vimtype = [vim.Datacenter]
    elif type == 'cluster':
        vimtype = [vim.ClusterComputeResource]
    elif type == 'respool':
        vimtype = [vim.ResourcePool]
    elif type == 'folder':
        vimtype == [vim.Folder]
    elif type == 'vm':
        vimtype = [vim.VirtualMachine]
    elif type == 'template':
        vimtype = [vim.VirtualMachine]
    elif type == 'datastore':
        vimtype = [vim.Datastore]
    elif type == 'network':
        vimtype = [vim.Network]
    obj = None
    container = content.viewManager.CreateContainerView(content.rootFolder,
                                                        vimtype,
                                                        True)
    container_object_list = container.view
    # destroying the container to free up resources on the vCenter
    container.Destroy() 
    for container_object in container_object_list:
        if container_object.name == name:
            obj = container_object
            break

    return obj

# print some VM info (including snapshots)
def print_vm_info(vm):
    summary     =   vm.summary
    #config      =   vm.config
    print 'VM name        :', summary.config.name
    print 'Distribution   :', summary.config.guestFullName
    print 'Hostname       :', summary.guest.hostName
    print 'UUID           :', summary.config.uuid
    print 'State          :', summary.runtime.powerState
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
        print 'Snapshots       : Yes'
        # Getting info about the root snapshot and displaying it
        root_snapshot       =   snapshot.rootSnapshotList[0]
        root_snapshot_name  =   root_snapshot.name
        root_snapshot_date  =   root_snapshot.createTime
        print 'Latest snapshots :'
        print "   %s: %s" % (root_snapshot_date, root_snapshot_name)
        # If the root snapshot has children, lets see its ugly faces
        if (root_snapshot.childSnapshotList):
            for first_snapshot in root_snapshot.childSnapshotList:
                print "   %s: %s" % (first_snapshot.createTime, 
                                     first_snapshot.name)
                # Let's see if the first snapshots has any child objects
                if (first_snapshot.childSnapshotList):
                    for second_snapshot in first_snapshot.childSnapshotList:
                        print "   %s: %s" % (second_snapshot.createTime,
                                             second_snapshot.name)
                        # If there are more snapshots, go use the vSphere Client
                        if (second_snapshot.childSnapshotList):
                            print '   WARNING: Only 3 levels of' \
                            ' snapshots supported, but this Virtual Machine' \
                            ' has more'
    # VM has no snapshots :(
    else:
        print 'Snapshots       : No'
    # We need some distance (divider)
    print ""

# check if object is a VM template
def check_if_template(object):
    if object.config.template == True:
        return True
    else:
        return False

def check_on_task(task):
    print '| ',
    sys.stdout.flush()
    while task.info.state == vim.TaskInfo.State.running:
        print '\b\b=>',
        sys.stdout.flush()
        time.sleep(5)

    if task.info.state == vim.TaskInfo.State.success:
        print '\b\b Done!'
        print 'Cloning successfully completed'
    else:
        print '\b\b Failed!'
        print 'Cloning failed! Check VMware logs:'
        print task.info.error

def clone_vm(template, target, folder, datastore, respool):
    print 'Preparing relocating specification...'
    relspec             =   vim.vm.RelocateSpec()
    relspec.datastore   =   datastore
    relspec.pool        =   respool
    print 'Preparing cloning specification...'
    clonespec  =   vim.vm.CloneSpec(powerOn=False,
                                     template=False,
                                     location=relspec)
    print "Starting cloning new VM '%s'..." % target
    task = template.Clone(name=target, folder=folder, spec=clonespec)
    check_on_task(task)

# disconnect from vCenter after our work is done
def vcenter_disconnect(service_instance):
    connect.Disconnect(service_instance)