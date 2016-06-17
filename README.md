#Service Funciton Chaining Demo using Netfloc, netfloc-heat and T-Nova VNFs

## Scenario
User1 sends traffic to user2. The 2 users are connected with a switch (Pica8 bridge). On the same switch there is a NFVI-PoP (OpenStack Cloud). At the beginning the traffic is directly from user1 to user2. That traffic is random and the only specific thing is a UDP video stream at port 33334. Then the WICM, that is in the control of the Pica8 switch, redirects the traffic to the NFVI-PoP. In there netfloc has some chains already established. The traffic goes to vTC eth1. If it is the udp video stream (the distinction is port based, on port 33334) the vTC sends it to eth3 to be forwarded towards the vMT. vMT transcodes the video stream and adds a watermark. All other traffic is sent to eth2 and then towards the vTC-f. Both of these chains arrive then at user2. After this the WICM stops the redirection towards the PoP so the traffic goes again directly from user1 to user2.

This is setup prepared for the SFC PoP2 on the Demokritos testbed. Netfloc has to be up and running on the SDN node, and the server application on the Control node ```[localadmin@10.100.0.3]: /home/localadmin/netfloc-demo``` with root access. For the demo the netloc-heat plugin is already configured. 

## Configure OpenStack HEAT for Netfloc

This is an OpenStack HEAT plugin for the [SDK for SDN - Netfloc](http://icclab.github.io/netfloc/ "Netfloc's github page") in order to use the resources of its service funciton chaining (SFC) library. It contains ```netfloc.py``` to be copied in the heat plugins library and two yaml templates: ```create_sfc.yaml``` to create all the required OpenStack resources and a bascic SFC. ```delete_sfc.yaml``` is to delete a chain given its ID number.

## Prepare the plugin

* Create a heat plugin directory under /usr/lib and copy inside the file netfloc.py (or place it alternatively under existing user-defined library):

```
mkdir /usr/lib/heat
cp src/netfloc.py /usr/lib/heat/
```

* Uncomment the ```plugin_dirs``` line in ```/etc/heat/heat.conf``` and include the path to the library. In Demokritos testbed:

```
plugin_dirs=/var/lib/heat/heat/contrib/nova_flavor/nova_flavor,/var/lib/heat/heat/contrib/netfloc/resources

Netfloc: /var/lib/heat/heat/contrib/netfloc/resources/netfloc.py
```

* For the chain to work, the port ID has to be returned by the ```handle_create()``` method of the native heat implementation for the [port.py resource](https://github.com/openstack/heat/blob/master/heat/engine/resources/openstack/neutron/port.py#L406). To do so include the following line at the end of this method:

```
return port['id']  
```
This will enable to return the Port ID as a resource in the yaml template for chain creation.
The heat port.py resource library is located under: 

``` 
/usr/lib/python2.7/site-packages/heat/engine/resources/openstack/neutron/port.py
```

* Restart the heat engine service:

```
service heat-engine restart
```

* Run ```heat resource-type-list``` and verify that the following two Netfloc resources show up:

```
Netfloc::Chain::Create                   |
Netfloc::Chain::Delete
```

## Test the service chain

* Before creating a chain, Netfloc must be running in a clean OpenStack environment and a public network has to be manualy created with assigning its ID as a parameter in the ```netfloc-demo/templates/demo_create.yaml``` file. 

* Once the setup is done and the chain is created using:
```heat-create -f demo_create.yaml [name_of_stack]``` 
the chain ID is listed in the Outputs section of the Stack Overview. Verify that the traffic steering is correct (ex. tcpdump) inside the VNF and on the endpoints. 

* To delete the chain run: 
```heat-delete -f demo_delete.yaml [name_of_stack]```
specifying in the template the ID of the chian to be deleted.

* This is the output from the heat-engine log file:

```
tail -f /var/log/heat/heat-engine.log | grep --line-buffered netfloc:
18589 DEBUG urllib3.connectionpool [-] "POST /restconf/operations/netfloc:create-service-chain HTTP/1.1" 200 None _make_request /usr/lib/python2.7/dist-packages/urllib3/connectionpool.py:430
18589 DEBUG urllib3.connectionpool [-] "POST /restconf/operations/netfloc:delete-service-chain HTTP/1.1" 200 0 _make_request /usr/lib/python2.7/dist-packages/urllib3/connectionpool.py:430
```
* This is the output from the Netfloc log file:

```
root@odl:~/netfloc_current# tail -f karaf/target/assembly/data/log/karaf.log | grep --line-buffered chainID
2016-05-26 10:29:44,826 | INFO  | tp1443878269-438 | ServiceChain                     | 269 - ch.icclab.netfloc.impl - 1.0.0.SNAPSHOT | ServiceChain chainID: 1
2016-05-26 10:29:44,826 | INFO  | tp1443878269-438 | NetflocServiceImpl               | 269 - ch.icclab.netfloc.impl - 1.0.0.SNAPSHOT | chainID: 1
```

A simple demo example of service chain setup is shown in the following ICCLab [blog post](https://blog.zhaw.ch/icclab/service-function-chaining-using-the-sdk4sdn/).
Following the basic template, the complexity of the chain can be modified by defining additional VNF resources in the yaml template. 

## Server app for port mapping and flows setup

* Location: ```netfloc-demo/src/server.py```
* For the app to work, a passwordless login is required for: Node2 and Switch from the Control node. Plus ***NOPASSWD*** is required for the ***ovs-ofctl*** and the VNF scrips in Node2 and the Switch. The VNFs also reqire passwordless access and root priviledges for the scripts, but this is all preconfigured in the VNFs snapsohts.
* The way to do it:

```
Switch
sudo visudo -f /etc/sudoers.d/ovs-ofctl 
localadmin nfvipop2-switch = (root) NOPASSWD: /usr/local/bin/ovs-ofctl

sudo visudo -f /etc/sudoers.d/sfc-vlan-flows
localadmin nfvipop2-switch = (root) NOPASSWD: /home/localadmin/sfc-vlan-flows

Control
sudo visudo -f /etc/sudoers.d/ovs-ofctl 
localadmin node2 = (root) NOPASSWD: /usr/local/bin/ovs-ofctl

vSF
sudo visudo -f /etc/sudoers.d/ovs-ofctl 
ubuntu vsf = (root) NOPASSWD: /usr/bin/ovs-ofctl

vTC
sudo visudo -f /etc/sudoers.d/run-vTC
ubuntu ubuntu-amd64 = (root) NOPASSWD: /home/ubuntu/run-vTC.sh

sudo visudo -f /etc/sudoers.d/sudo
ubuntu ubuntu-amd64 = (root) NOPASSWD: ALL

vTC-f
sudo visudo -f /etc/sudoers.d/run-vTC-f
ubuntu ubuntu-amd64 = (root) NOPASSWD: /home/ubuntu/run-vTC-f.sh

sudo visudo -f /etc/sudoers.d/sudo
ubuntu ubuntu-amd64 = (root) NOPASSWD: ALL

vMT
sudo visudo -f /etc/sudoers.d/sudo
ubuntu ubuntu-amd64 = (root) NOPASSWD: ALL

```

## Scripts in the OS nodes and the VMs
Already prepared in the nodes.

* In Switch - ***sfc-vlan-flows***

```
root@nfvipop2-switch:/home/localadmin# cat sfc-vlan-flows
ovs-ofctl add-flow br0 priority=14,in_port=3,dl_vlan=400,actions=output:1
ovs-ofctl add-flow br0 priority=14,in_port=2,dl_vlan=401,actions=output:3
ovs-ofctl add-flow br0 priority=14,in_port=3,dl_vlan=401,actions=output:1
ovs-ofctl add-flow br0 priority=14,in_port=2,dl_vlan=400,actions=output:3
```
* In vSF - ***sfc-flows-sf***

```
ovs-ofctl del-flows vnf
ovs-ofctl add-flow vnf priority=1,in_port=1,actions=drop
ovs-ofctl add-flow vnf priority=1,in_port=2,actions=drop
ovs-ofctl add-flow vnf priority=2,in_port=1,dl_vlan=401,actions=mod_vlan_vid:400,output:2
ovs-ofctl add-flow vnf priority=2,in_port=1,dl_vlan=400,actions=mod_vlan_vid:401,output:2
ovs-ofctl dump-flows vnf
ifconfig eth1 up
ifconfig eth2 up
```
* In vTC - ***run-vTC.sh***

```
#!/bin/sh
if [ ! -f vtc/PF_RING/kernel/pf_ring.ko ]; then 
	insmod vtc/PF_RING/kernel/pf_ring.ko
fi
ifconfig eth1 promisc up
ifconfig eth2 promisc up
ifconfig eth3 promisc up
cd ndpi-send/nDPI/example
nohup ./ndpiReader -i eth1 -a eth2 -b eth3 -t -v 2 -V 2 &
echo "vTC started successfully ツ"
exit
```
* Verify with ```ps aux | grep ndpi``` that the vTC is running.


* In vTC-f ***run-vTC-f.sh***

```
if [ ! -f vtc/PF_RING/kernel/pf_ring.ko ]; then
	insmod vtc/PF_RING/kernel/pf_ring.ko
fi
ifconfig eth1 promisc up
ifconfig eth2 promisc up
cd vtc/PF_RING/userland/examples
nohup ./pfbridge -a eth1 -b eth2 &
echo "vTC-f started successfully ツ"
exit
```
* Verify with ```ps aux | grep pfring``` that the vTC is running.

* In vMT ***run-vMT.sh***

```
ifconfig eth1 promisc up
ifconfig eth2 promisc up
ffmpeg -re -i udp:13.13.13.5:33334 -i watermark_sesame_logo.png -filter_complex "overlay=7*((main_w-overlay_w)/8):(main_h-overlay_h)/2" -vcodec mpeg4 -an -b:v 2048 -f mpegts udp:10.50.0.2:33334
```

* Run the server.py app from ```netfloc-demo/src``` on Control node. Expected output:

```
Node2 SFC flows installed successfully :)
-----------------------------------------
 cookie=0x0, duration=0.002s, table=0, n_packets=0, n_bytes=0, idle_age=593, priority=14,in_port=1,dl_vlan=400 actions=output:522
 cookie=0x0, duration=216.778s, table=0, n_packets=0, n_bytes=0, idle_age=593, priority=14,in_port=1,dl_vlan=401 actions=output:522

Control SFC flows installed successfully :)
-------------------------------------------
 cookie=0x0, duration=0.002s, table=0, n_packets=0, n_bytes=0, idle_age=593, priority=14,in_port=774,dl_vlan=400 actions=output:1
 cookie=0x0, duration=0.005s, table=0, n_packets=0, n_bytes=0, idle_age=593, priority=14,in_port=774,dl_vlan=401 actions=output:1

Switch SFC flows installed successfully :)
------------------------------------------
 cookie=0x0, duration=216.765s, table=0, n_packets=0, n_bytes=0, idle_age=593, priority=14,in_port=3,dl_vlan=400 actions=output:2
 cookie=0x0, duration=216.761s, table=0, n_packets=0, n_bytes=0, idle_age=593, priority=14,in_port=2,dl_vlan=401 actions=output:1
 cookie=0x0, duration=216.758s, table=0, n_packets=0, n_bytes=0, idle_age=593, priority=14,in_port=3,dl_vlan=401 actions=output:2
 cookie=0x0, duration=216.754s, table=0, n_packets=0, n_bytes=0, idle_age=593, priority=14,in_port=2,dl_vlan=400 actions=output:1

Please enter user@IP of the Service Forwarder VNF: ubuntu@10.100.0.102
Service Forwarder SFC flows installed successfully :)
-----------------------------------------------------
NXST_FLOW reply (xid=0x4):
 cookie=0x0, duration=0.001s, table=0, n_packets=0, n_bytes=0, idle_age=0, priority=2,in_port=1,dl_vlan=400 actions=mod_vlan_vid:401,output:2
 cookie=0x0, duration=0.003s, table=0, n_packets=0, n_bytes=0, idle_age=0, priority=2,in_port=1,dl_vlan=401 actions=mod_vlan_vid:400,output:2
 cookie=0x0, duration=0.008s, table=0, n_packets=0, n_bytes=0, idle_age=0, priority=1,in_port=1 actions=drop
 cookie=0x0, duration=0.005s, table=0, n_packets=0, n_bytes=0, idle_age=0, priority=1,in_port=2 actions=drop

Please enter user@IP of the vTC VNF: ubuntu@10.100.0.104
ubuntu@10.100.0.104
vTC started successfully ツ

Please enter user@IP of the vTC-f VNF: ubuntu@10.100.0.103
vTC-f started successfully ツ
```

* With this the demo is (almost) ready to run. At the moment the vMT flows are added manually (PRELIMINARY). 

### Rules to make the vMT work

* First send video packets from ***User1 [localadmin@10.30.0.101], port IP: 10.50.0.1*** to ***User2 [tnova@10.30.0.102], port IP: 10.50.0.2:33334***

```
ffmpeg -re -i big_buck_bunny_720p_surround.avi -vcodec mpeg4 -an -b 1024k -s 640x480 -f mpegts udp:10.50.0.2:33334
```
* The following is needed to override the netfloc chain rules with new rules (as vMT requires). Two flows has to be added manually. 

#### vMT Flow (1) 

* Send the video stream from user1 after all chains are established. Go in vMT and do: ```tcpdump –i eth1 –nvve```* Get the source mac of the udp packets, remember it (for example ```04:31:ff:ff:ff:ff```) and modify it to ```04:31:00:00:00:00```
* Find in the Controller the ```vMT_in_port``` number inside ```/port_mappings/control_port_mappings```. The port we need is the one that corresponds to```vMT_eth0_port``` and it is usually one less numebr than the ```vMT_in_port```.
* Run ```ovs-ofctl dump-flows br-int | grep "priority=20,in_port=1"``` to find the following rule: ```priority=20,in_port=1,dl_dst=02:00:00:00:00:00/ff:ff:00:00:00:00 actions=output:<vMT_eth1_port>```
* According to this, create the following rule: ```ovs-ofctl add-flow br-int priority=21,in_port=1,dl_dst=02:00:00:00:00:00/ff:ff:00:00:00:00,actions=strip_vlan,mod_dl_dst:<vMT eth0 mac>,mod_nw_dst:<vMT eth0 IP>,mod_nw_tos:4,output:<vMT eth0 port>```
* The final rule looks like this:
```ovs-ofctl add-flow br-int priority=21,in_port=1,dl_dst=02:00:00:00:00:00/ff:ff:00:00:00:00,actions=strip_vlan,mod_dl_dst:fa:16:3e:21:41:e0,mod_nw_dst:13.13.13.4,mod_nw_tos:4,output:784```

#### vMT Flow (2) 

* Search the mac address you remembered in the previous command (02:12:00:00:00:00) on the Control node (running the vMT):
```ovs-ofctl dump-flows br-int | grep 02:12:00:00:00:00```. Normally only one flow should appear as output, for example:
```
priority=20,in_port=319,dl_src=04:31:00:00:00:00/ff:ff:00:00:00:00,dl_dst=04:00:00:00:00:0,actions=mod_dl_src:00:90:27:22:d2:68,mod_dl_dst:b8:ae:ed:77:73:bc,output:773
```

* You need to take the actions from that flow. Add 2 more actions and mach it accordingly to create the following flow rule: 

```ovs-ofctl add-flow br-int priority=21,in_port=<vMT eth0 port>,dl_type=0x0800,nw_proto=17,nw_src=<vMT eth0 IP>,nw_dst=10.50.0.2,dl_src=<vMT eth0 mac>,dl_dst=<GET PACKET DST MAC FROM TCPDUMP ETH0 IN vMT>,actions=mod_vlan_vid:401,mod_nw_src=10.50.0.1,mod_dl_src:00:90:27:22:d2:68,mod_dl_dst:b8:ae:ed:77:73:bc,output:773```
* The final rule looks like this: 

```ovs-ofctl add-flow br-int priority=21,in_port=769,dl_type=0x0800,nw_proto=17,nw_src=13.13.13.5,nw_dst=10.50.0.2,dl_src=fa:16:3e:58:9a:84,dl_dst=fa:16:3e:21:f8:8d,actions=mod_vlan_vid:401,mod_nw_src=10.50.0.1,mod_dl_src:00:90:27:22:d2:68,mod_dl_dst:b8:ae:ed:77:73:bc,output:773```
* After the flows are installed, run the following command in the vMT to start the transcoding:

```
ffmpeg -re -i udp:13.13.13.5:33334 -i watermark_xil.png -filter_complex "overlay=7*((main_w-overlay_w)/8):(main_h-overlay_h)/2" -vcodec mpeg4 -an -b:v 2048 -f mpegts udp:10.50.0.2:33334
```

This command takes the video from the portIP 13.13.13.5 of eth0, adds a watermark and sends the video to destination IP: 10.50.0.2:33334. To change the watermark, replace the file watermark_xil.png. With T-Nova or Sesame logos:

```
ffmpeg -re -i udp:13.13.13.5:33334 -i watermark_tnova_logo.jpg -filter_complex "overlay=7*((main_w-overlay_w)/8):(main_h-overlay_h)/2" -vcodec mpeg4 -an -b:v 2048 -f mpegts udp:10.50.0.2:33334
```

* To see video in User2 (10.50.0.2), connect with Teamviewer. Run the ffplayer and the video shloud appear with the watermark on it:

```
ffplay udp://10.50.0.2:33334```
* The UDP packets can be captured on User2 on the following interface:```tcpdump -i eth0.100 udp```.

## Video with and w/o watermark

* WICM component is used to make redirection of the flows to the SFC PoP. When redirection is enabled the video is with watermark.

* WICM redirection: REST calls are needed here. They can be done with CURL. To view the redirections do:
```curl http://10.30.0.12:12891/vnf-connectivity```* To enable the redirection search the last ```$ns_instance_id``` and replace it with new (```$ns_instance_id``` must be unique for each redirection). Then run the following to allocate vnlan_ids for the redirection:```
localadmin@control:~$ curl -X  POST -H "Content-Type: application/json" -H "Cache-Control: no-cache" -d '{"service":{"ns_instance_id":"1","client_mkt_id":"1","nap_mkt_id":"1","nfvi_mkt_id":"1"}}' http://10.30.0.12:12891/vnf-connectivity
{
  "allocated": {
    "ce_transport": {
      "type": "vlan",
      "vlan_id": 400
    },
    "ns_instance_id": "1",
    "pe_transport": {
      "type": "vlan",
      "vlan_id": 401
    }
  }
```* To activte the redirection run:```
localadmin@control:~$ curl -X PUT http://10.30.0.12:12891/vnf-connectivity/1
{
  "activated": {
    "ns_instance_id": "1"
  }
```* To disable the redirection and with this, the chain & video transcoding, run:

```curl -X DELETE http://10.30.0.12/vnf-connectivity/$ns_instance_id```