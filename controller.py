'''
Please add your name: Song Zhiwen
Please add your matric number: A0122001M
'''

import sys
import os
import datetime
import time
import thread
from sets import Set

from pox.core import core

import pox.openflow.libopenflow_01 as of
import pox.openflow.discovery
import pox.openflow.spanning_tree

from pox.lib.revent import *
from pox.lib.util import dpid_to_str
from pox.lib.addresses import IPAddr, EthAddr

log = core.getLogger()

routingtable = {}

def clear_table():
    while 1:
        time.sleep(30)
        print("cleaning table")
        time_now = datetime.datetime.now()
        for switch, mapping in routingtable.items():
            for ip, info in mapping.items():
                time_diff = int(time.mktime(time_now.timetuple()) - time.mktime(info[1].timetuple()))
                if time_diff > 30:
                    print("routing timeout",ip, routingtable[switch][ip])
                    del routingtable[switch][ip]

    

class Controller(EventMixin):

    def __init__(self):
        self.listenTo(core.openflow)
        core.openflow_discovery.addListeners(self)
        self.prem_queue = {}
        
        thread.start_new_thread(clear_table , ())
    # You can write other functions as you need.
        
    def _handle_PacketIn (self, event):    
        packet = event.parsed
        dpid = dpid_to_str(event.dpid)
        inport = event.port

    	# install entries to the route table
        def install_enqueue(event, packet, outport, q_id):
            msg = of.ofp_flow_mod()

            msg.match = of.ofp_match.from_packet(packet, inport)
            msg.actions.append(of.ofp_action_enqueue(port = outport, queue_id=q_id))
            msg.data = event.ofp
            msg.priority = 50
            msg.idle_timeout = 50
            msg.hard_timeout = 50
            event.connection.send(msg)
            return
        
       #         time_diff = int(time.mktime(datetime.datetime.now().timetuple()) - time.mktime(dst_info[1].timetuple()))
       #         if (time_diff < 30):
       #             return dst_info[0]
       #         else:
       #             print("routing info outdated:", self.routingtable[dpid][packet.dst])
       #             del self.routingtable[dpid][packet.dst]
       #             return None
        
    	# Check the packet and decide how to route the packet
        def forward(message = None):
            
            if packet.dst.is_multicast:
                if packet.payload.protodst not in routingtable[dpid]:
                    flood("unknown destination")
            elif packet.dst not in routingtable[dpid]:
                print("unknown destination", dpid, packet.dst)
                print(packet.payload)
                flood("unknown destination")
            else:
                dst_port = routingtable[dpid][packet.dst][0]
                queue_id = 0
                
                if packet.type == packet.IP_TYPE:
                    queue_id = max(self.prem_queue.get(packet.payload.srcip, -1), self.prem_queue.get(packet.payload.dstip, -1))
                #elif packet.type == packet.ARP_TYPE:
                #    queue_id = max(self.prem_queue.get(packet.payload.protosrc, -1), self.prem_queue.get(packet.payload.protodst, -1))

                
                if queue_id == -1:
                    queue_id = 2
                print(datetime.datetime.now().time())
                print("putting to queue:" + str(queue_id))
                install_enqueue(event, packet, dst_port, queue_id)

        # When it knows nothing about the destination, flood but don't install the rule
        def flood (message = None):
            msg = of.ofp_packet_out()

            msg.in_port = inport
            action = of.ofp_action_output(port = of.OFPP_ALL)
            msg.actions.append(action)
            msg.data = event.ofp
            msg.priority = 1

            event.connection.send(msg)
        
        if packet.src not in routingtable[dpid]:
            routingtable[dpid][packet.src] = (inport, datetime.datetime.now())
            
        
        forward()


    def _handle_ConnectionUp(self, event):
        dpid = dpid_to_str(event.dpid)
        log.debug("Switch %s has come up.", dpid)
        
        routingtable[dpid] = {}

        print("Switch %s has come up.", dpid)

        fp = open("policy.in", "r")
        line = fp.readline().replace("\r","").replace("\n","")
        data = line.split(" ")

        numFirewall=int(data[0])
        numPrem=int(data[1])

        fw_policies=[]

        for i in range(numFirewall):
            line = fp.readline().replace("\r","").replace("\n","")
            data = line.split(",")
            fw_policies.append(data)

        for i in range(numPrem):
            line = fp.readline().replace("\r","").replace("\n","")
            data = line.split(",")
            self.prem_queue[IPAddr(data[0])]=int(data[1])


        # Send the firewall policies to the switch
        def sendFirewallPolicy(connection, policy):
            msg = of.ofp_flow_mod()
            msg.priority = 100
            msg.actions.append(of.ofp_action_output(port = of.OFPP_NONE))
            msg.match.dl_type = 0x0800
            msg.match.nw_proto = 6
            if len(policy) == 1:
                msg.match.nw_src = IPAddr(policy[0])
            elif len(policy) == 2:
                msg.match.nw_dst = IPAddr(policy[0])
                msg.match.tp_dst = int(policy[1])
            elif len(policy) == 3:
                msg.match.nw_src = IPAddr(policy[0])
                msg.match.nw_dst = IPAddr(policy[1])
                msg.match.tp_dst = int(policy[2])
            connection.send(msg)

        for i in range(len(fw_policies)):
            sendFirewallPolicy(event.connection, fw_policies[i])
            

def launch():
    # Run discovery and spanning tree modules
    pox.openflow.discovery.launch()
    pox.openflow.spanning_tree.launch()

    # Starting the controller module
    core.registerNew(Controller)
