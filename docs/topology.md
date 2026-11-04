# How the topology is built

The cockpit merges every source into one model, keyed by IP address, then by MAC and name:

1. **Scan** (`nmap -sn` + a few TCP ports): live devices, MAC + vendor on local subnets, device type guessed from vendor and ports (domain controller = 53 + 88 + 389, ESXi = 902 + 443, printer = 9100, Windows = 3389 / 445…).
2. **Names**: reverse DNS against your AD (`names.dns_servers`, or auto-detected DCs), NetBIOS (`nbstat`) for Windows names and MACs even across routers, vCenter VM and host names, agent names, manual `overrides`.
3. **Path to the Internet** (`traceroute`): private hops become gateway/firewall/router nodes, the first public hop becomes the ISP node.
4. **vCenter / ESXi** (pyVmomi, read-only): hosts, VMs (IPs from VMware Tools), datastores, triggered alarms, quick stats, and `QueryNetworkHint` on every physical NIC. That gives the **CDP/LLDP neighbour of each host uplink**: switch name, port, management IP.
5. **Agents**: `lldp_neighbor_info` from lldpd on physical Linux servers.
6. **SNMP** (when you have read access): `ifName`, `ifOperStatus`, `ifHighSpeed`, LLDP-MIB and CISCO-CDP-MIB neighbours, Q-BRIDGE/BRIDGE MAC tables, ARP tables of L3 devices. Switch-to-switch links come from LLDP/CDP. Device-to-port links come from MAC tables, ignoring uplinks (ports with neighbours or more than 6 MACs).

## The tree

```
Internet
└─ ISP (first public hop)
   └─ provider router / firewall (private hops, from traceroute)
      └─ Site (one per entry in sites:)
         └─ Network (subnet)
            └─ Core switch ─ access switches (LLDP/CDP/SNMP) ─ devices on their port
               └─ ESXi ─ VMs
```

Devices with no known switch port hang under their network. In the UI, workstations, phones and printers under the same parent are grouped ("24 workstations · 2 absent"); click a group to expand it.

## Status, without false positives

| Status | Rule |
|---|---|
| **OK** | Answers ping or its TCP port, or its agent is alive, or vCenter says connected, or it answered ARP in the last scan |
| **Alert / Critical** | OK but has warning / critical alerts |
| **Down** | Important device (server, VM, ESXi, DC, firewall, switch, `watch:`) that answered in the last 24 h and stopped |
| **Absent** | Non-critical device (PC, phone…) no longer answering: normal at night |
| **Off** | VM powered off in vCenter |
