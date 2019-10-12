'''
Please add your name:
Please add your matric number: 
'''

import os
import sys
import atexit
from mininet.net import Mininet
from mininet.log import setLogLevel, info
from mininet.cli import CLI
from mininet.topo import Topo
from mininet.link import Link
from mininet.node import RemoteController

net = None
linkbw = []

class TreeTopo(Topo):
			
    def __init__(self):
        Topo.__init__(self)
        self.build_topo()

    def build_topo(self):
        fp = open("topology.in", "r")
        line = fp.readline()
        data = line.split(" ")
        numHost = data[0]
        numSwitch = data[1]
        numLink = data[2]
        for h in range(int(numHost)):
            self.addHost('h%d' % (h+1))

        for s in range(int(numSwitch)):
            sconfig = {'dpid': "%016x" % (s+1)}
            self.addSwitch('s%d' % (s+1), **sconfig)

        for i in range(int(numLink)):
            linkData = fp.readline().replace("\r","").replace("\n","")
            param = linkData.split(",")
            bandwidth = int(param[2])
            self.addLink(param[0], param[1])
            linkbw.append((param[0], param[1], bandwidth))
        
	# Add hosts
    # > self.addHost('h%d' % [HOST NUMBER])

	# Add switches
    # > sconfig = {'dpid': "%016x" % [SWITCH NUMBER]}
    # > self.addSwitch('s%d' % [SWITCH NUMBER], **sconfig)

	# Add links
	# > self.addLink([HOST1], [HOST2])

def startNetwork():
    info('** Creating the tree network\n')
    topo = TreeTopo()

    global net
    net = Mininet(topo=topo, link = Link,
                  controller=lambda name: RemoteController(name, ip='192.168.211.3'),
                  listenPort=6633, autoSetMacs=True)

    info('** Starting the network\n')
    net.start()

    links = topo.links(True, False, True)
    switches = topo.switches()

    for link in links:
        node1 = link[0]
        node2 = link[1]

        if bool(node1 in switches) != bool(node2 in switches):
            curr = [elem for elem in linkbw if node1 in elem and node2 in elem]
            if node1 in switches:
                switch = node1
                switch_port = link[2]['port1']
            else:
                switch = node2
                switch_port = link[2]['port2']
            bandwidth = curr[0][2] * 1000000
            os.system('sudo ovs-vsctl -- set Port %s qos=@newqos \
               -- --id=@newqos create QoS type=linux-htb other-config:max-rate=%d queues=0=@q0,1=@q1,2=@q2 \
               -- --id=@q0 create queue other-config:max-rate=%d other-config:min-rate=%d \
               -- --id=@q1 create queue other-config:min-rate=%d \
               -- --id=@q2 create queue other-config:max-rate=%d' % (switch + "-eth" + str(switch_port), bandwidth ,0.6 * bandwidth,0.3 * bandwidth,0.8 * bandwidth, 0.2 * bandwidth))
            print("create qos for host", switch + "-eth" + str(switch_port), bandwidth)

        elif node1 in switches and node2 in switches:
            switch1 = node1
            switch1_port = link[2]['port1']
            switch2 = node2
            switch2_port = link[2]['port2']

            curr = [elem for elem in linkbw if node1 in elem and node2 in elem]
            bandwidth = curr[0][2] * 1000000

            os.system('sudo ovs-vsctl -- set Port %s qos=@newqos \
               -- --id=@newqos create QoS type=linux-htb other-config:max-rate=%d queues=0=@q0,1=@q1,2=@q2 \
               -- --id=@q0 create queue other-config:max-rate=%d other-config:min-rate=%d \
               -- --id=@q1 create queue other-config:min-rate=%d \
               -- --id=@q2 create queue other-config:max-rate=%d' % (switch1 + "-eth" + str(switch1_port), bandwidth ,0.6 * bandwidth, 0.3 * bandwidth, 0.8 *bandwidth, 0.2* bandwidth))
            print("create qos for switch", switch1 + "-eth" + str(switch1_port), bandwidth)
            os.system('sudo ovs-vsctl -- set Port %s qos=@newqos \
               -- --id=@newqos create QoS type=linux-htb other-config:max-rate=%d queues=0=@q0,1=@q1,2=@q2 \
               -- --id=@q0 create queue other-config:max-rate=%d other-config:min-rate=%d \
               -- --id=@q1 create queue other-config:min-rate=%d \
               -- --id=@q2 create queue other-config:max-rate=%d' % (switch2 + "-eth" + str(switch2_port), bandwidth ,0.6 * bandwidth, 0.3 * bandwidth, 0.8 * bandwidth, 0.2 * bandwidth))
            print("create qos for switch", switch2 + "-eth" + str(switch2_port),bandwidth)




    # Create QoS Queues
    # > os.system('sudo ovs-vsctl -- set Port [INTERFACE] qos=@newqos \
    #            -- --id=@newqos create QoS type=linux-htb other-config:max-rate=[LINK SPEED] queues=0=@q0,1=@q1,2=@q2 \
    #            -- --id=@q0 create queue other-config:max-rate=[LINK SPEED] other-config:min-rate=[LINK SPEED] \
    #            -- --id=@q1 create queue other-config:min-rate=[X] \
    #            -- --id=@q2 create queue other-config:max-rate=[Y]')

    info('** Running CLI\n')
    CLI(net)

def stopNetwork():
    if net is not None:
        net.stop()
        # Remove QoS and Queues
        os.system('sudo ovs-vsctl --all destroy Qos')
        os.system('sudo ovs-vsctl --all destroy Queue')


if __name__ == '__main__':
    # Force cleanup on exit by registering a cleanup function
    atexit.register(stopNetwork)

    # Tell mininet to print useful information
    setLogLevel('info')
    startNetwork()
