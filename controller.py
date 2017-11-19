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
		self.premium = {}
	
	# You can write other functions as you need.

	def _handle_PacketIn (self, event):   
		packet = event.parsed
		dpid = event.dpid
		inport = event.port
		def install_enqueue(event, packet, outport, q_id):
			log.debug("Installing flow %s:%d %s:%d to %d", packet.src, event.port, packet.dst, outport, q_id)
			msg = of.ofp_flow_mod()
			msg.match = of.ofp_match.from_packet(packet, inport)
			msg.actions.append(of.ofp_action_enqueue(port = outport, queue_id = q_id))
			msg.data = event.ofp
			msg.priority = 50
			event.connection.send(msg)
          	
    	# Check the packet and decide how to route the packet
		def forward(message = None):
			log.debug("Start forwarding: %s to from port %d", packet, event.port)
			
#			if self.macToPort.get(dpid) == None: self.macToPort[dpid] = {}
			
			# Only record mactable when first time arrived
			if self.macToPort[dpid].get(packet.src) == None: self.macToPort[dpid][packet.src] = inport
			if packet.dst.is_multicast:
				
				flood("Multicast packet, flooding")
			elif packet.dst not in self.macToPort[dpid]:
				flood("Port for %s unknown, flooding" % packet.dst)
			else:
				q_id = 0 #Default queue
				
				#Check type of packet to analyze IP address
				if packet.type == packet.IP_TYPE:
					sip = packet.payload.srcip;
					dip = packet.payload.dstip;
					log.debug("here comes a packet from %s", sip)
					
					if sip == None: q_id = 0
					elif self.premium[dpid].get(sip) == None: q_id = 2
					else :q_id = 1
				elif packet.type == packet.ARP_TYPE:
					sip = packet.payload.protosrc
					dip = packet.payload.protodst
					log.debug("here comes a packet from %s", sip)
					if sip == None: q_id = 0
					elif self.premium[dpid].get(sip) == None: q_id = 2
					else :q_id = 1
				log.info("q_id is %d", q_id)
				install_enqueue(event, packet, self.macToPort[dpid][packet.dst], q_id)
	# When it knows nothing about the destination, flood but don't install the rule
		def flood (message = None):
			log.debug(message)
			msg = of.ofp_packet_out()
			msg.actions.append(of.ofp_action_output(port = of.OFPP_FLOOD))
			msg.in_port = inport
			msg.data = event.ofp
			event.connection.send(msg)
			log.debug("Flooding %s", dpid_to_str(event.dpid))
		# Add the MAC table
		forward()

	def _handle_ConnectionUp(self, event):
		dpid = event.dpid
		log.debug("Switch %d has come up.", dpid)
		filename = "policy.in"
		self.macToPort[dpid] = {}
		self.premium[dpid] = {} 
		blocklist = []
		ff = open(filename, "r")
		tinput = ff.readline()[:-1].split(' ')
		n, m = map(int, tinput)
		def addblock(blocklist, ip1, ip2, port):
			blocklist.append([ip1,ip2,port])
		for i in range(1, n+1):
			tinput = ff.readline()
			if tinput[-1] == '\n' : tinput = tinput[:-1]
			tinput = tinput.split(',')
			addblock(blocklist, tinput[0], tinput[1], int(tinput[2]))
			addblock(blocklist, tinput[1], tinput[0], int(tinput[2]))
		for i in range(1, m+1):
			tinput = ff.readline()
			if tinput[-1] == '\n' : tinput = tinput[:-1]
#			pp = IPAddr(tinput)
#			print("IP address map: %s -> %s", tinput, pp)
			self.premium[dpid][IPAddr(tinput)] = True
		print self.premium
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
			log.debug(" Firewall rule %s %s:%d sending", src, dst, port)
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
