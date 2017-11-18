'''
Please add your name: SheZhaochen
Please add your matric number: A0174088W
'''

import sys
import os
from sets import Set

from pox.core import core

import pox.openflow.libopenflow_01 as of
import pox.openflow.discovery
import pox.openflow.spanning_tree
import time

from pox.lib.revent import *
from pox.lib.util import dpid_to_str
from pox.lib.addresses import IPAddr, EthAddr
log = core.getLogger()

class Controller(EventMixin):
	def __init__(self):
		self.listenTo(core.openflow)
		core.openflow_discovery.addListeners(self)
		# MAC to port table here
		self.macToPort = {}
		# Blocklist and premium account 
		premium = []
	
	def addpremium(ip):
		premium.append(ip)
	
	def ispremium(ip):
		for i in premium:
			if i == ip: return True
		return False
	
	# You can write other functions as you need.

	def _handle_PacketIn (self, event):   
		packet = event.parsed
		dpid = event.dpid
		port = event.port
		def install_enqueue(event, packet, outport, q_id):
			log.info("Installing flow %s:%d %s:%d", packet.src, event.port, packet.dst, outport)
			msg = of.ofp_flow_mod()
			msg.match = of.ofp_match.from_packet(packet, event.port)
			msg.actions.append(of.ofp_action_enqueue(port = outport, queue_id = q_id))
			msg.data = event.ofp
			self.connection.send(msg)
          	
    	# Check the packet and decide how to route the packet
		def forward(message = None):
			log.info("Start forwarding: %s to from port %d", packet, event.port)
			self.macToPort[dpid][packet.src] = port
			if packet.dst.is_multicast:
				flood("Multicast packet, flooding")
			if packet.dst not in self.macToPort[dpid]:
				flood("Port for %s unknown, flooding" , packet.dst)
			else:
				install_enqueue(event, packet, self.macToPort[dpid][packet.dst], qid)
        # When it knows nothing about the destination, flood but don't install the rule
		def flood (message = None):
			log.info(message)
			msg = of.ofp_packet_out(data = event.ofp)
			msg.actions.append(of.ofp_action_output(port = of.OFPP_FLOOD))
			msg.in_port = event.port
			msg.data = event.ofp
			event.connection.send(msg)
			log.info("Flooding %s", dpid_to_str(event.dpid))
		# Add the MAC table
		forward()

	def _handle_ConnectionUp(self, event):
		def addblock(ip1, ip2, port):
			self.blocklist.append([ip1,ip2,port])
		dpid = dpid_to_str(event.dpid)
		log.debug("Switch %s has come up.", dpid)
		filename = "policy.in"
		self.macToPort[dpid] = {}
		self.premium = []
		blocklist = []
		ff = open(filename, "r")
		tinput = ff.readline()[:-1].split(' ')
		n, m = map(int, tinput)
		for i in range(1, n+1):
			tinput = ff.readline()
			if tinput[-1] == '\n' : tinput = tinput[:-1]
			tinput = tinput.split(',')
			addblock(tinput[0], tinput[1], int(tinput[2]))
			addblock(tinput[1], tinput[0], int(tinput[2]))
		for i in range(1, m+1):
			tinput = ff.readline()
			if tinput[-1] == '\n' : tinput = tinput[:-1]
			addpremium(tinput)
		
		# Send the firewall policies to the switch
		def sendFirewallPolicy(connection, policy):
			src = policy[0]
			dst = policy[1]
			port = policy[2]
			msg = of.ofp_flow_mod()
			msg.priority = 100
			msg.actions.append(of.ofp_action_output(port = of.OFPP_NONE))
			msg.match.dl_type = 0x800
			msg.match.nw_proto = 6
			msg.match.nw_src = IPAddr(src)
			msg.match.nw_dst = IPAddr(dst)
			msg.match.tp_dst = int(port)
			connection.send(msg)
			log.info(" Firewall rule %s %s:%d sending", src, dst, port)
		for i in blocklist:	
			sendFirewallPolicy(event.connection, i)
	#	for i in [FIREWALL POLICIES]:
    #        sendFirewallPolicy(event.connection, i)
            
def launch():
    # Run discovery and spanning tree modules
    pox.openflow.discovery.launch()
    pox.openflow.spanning_tree.launch()

    # Starting the controller module
    core.registerNew(Controller)
