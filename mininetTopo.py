'''
Please add your name: She Zhaochen
Please add your matric number: A0174088W 
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

class TreeTopo(Topo):
			
	def __init__(self):
		# Initialize topology
		Topo.__init__(self)        	
	
	# You can write other functions as you need.
	
	# Add hosts
    # > self.addHost('h%d' % [HOST NUMBER])

	# Add switches
    # > sconfig = {'dpid': "%016x" % [SWITCH NUMBER]}
    # > self.addSwitch('s%d' % [SWITCH NUMBER], **sconfig)

	# Add links
	# > self.addLink([HOST1], [HOST2])

def startNetwork():
	info('** Creating the tree network\n')
	filename = "topology.in"
	ff = open(filename, "r")
	tinput = ff.readline().split(' ')
	n, m, l = map(int, tinput)
	print n,m,l
	topo = TreeTopo()
	links = []
	for i in range(1, n + 1):
		topo.addHost('h%d' % i)
	for i in range(1, m + 1):
		sconfig = {'dpid': "%016x" % i}
		topo.addSwitch('s%d' % i, **sconfig)
	bwmap = {}
	for i in range(1, l + 1):
		tinput = ff.readline()
		if tinput[-1] == '\n' : tinput = tinput[:-1]
		tinput = tinput.split(',')
		links.append([tinput[0], tinput[1], int(tinput[2])*1000000])
		if bwmap.get(tinput[0]) == None :bwmap[tinput[0]] = {}
		bwmap[tinput[0]][tinput[1]] = int(tinput[2]) * 1000000
		print links[-1]
		topo.addLink(tinput[0], tinput[1])
	print links
 	global net
	net = Mininet(topo=topo, link = Link,
                  controller=lambda name: RemoteController(name, ip='192.168.56.103'),
                  listenPort=6633, autoSetMacs=True)
	
	info('** Starting the network\n')
	net.start()
	nQoS = 0
	for link in topo.links(True, False, True):
		for switch in topo.switches():
			if link[2]["node1"] == switch:
				bw = bwmap[link[2]["node1"]][link[2]["node2"]]
				X = bw * 8 / 10
				Y = bw * 5 / 10
				nQoS += 1
    			# Create QoS Queues
				os.system('sudo ovs-vsctl -- set Port %s qos=@newqos \
                -- --id=@newqos create QoS type=linux-htb other-config:max-rate=%d queues=0=@q0,1=@q1,2=@q2 \
                -- --id=@q0 create queue other-config:max-rate=%d other-config:min-rate=%d \
                -- --id=@q1 create queue other-config:min-rate=%d \
                -- --id=@q2 create queue other-config:max-rate=%d' % (switch + '-eth' + str(link[2]['port1']), bw, bw, bw, X, Y))
				print "QoS on %s" % (switch + ':' + str(link[2]['port1']))
					
			if link[2]["node2"] == switch:
				bw = bwmap[link[2]["node1"]][link[2]["node2"]]
				X = bw * 8 / 10
				Y = bw * 5 / 10
				nQoS += 1
    			# Create QoS Queues
				os.system('sudo ovs-vsctl -- set Port %s qos=@newqos \
                -- --id=@newqos create QoS type=linux-htb other-config:max-rate=%d queues=0=@q0,1=@q1,2=@q2 \
                -- --id=@q0 create queue other-config:max-rate=%d other-config:min-rate=%d \
                -- --id=@q1 create queue other-config:min-rate=%d \
                -- --id=@q2 create queue other-config:max-rate=%d' % (switch + '-eth' + str(link[2]['port2']), bw, bw, bw, X, Y))
				print "QOS on %s" % (switch + ':' + str(link[2]['port2']))
	print "Total QoS: %d" % nQoS

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
