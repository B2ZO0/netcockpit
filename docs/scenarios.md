# Scenarios

Every infrastructure is different. Find the situation closest to yours: for each one, what to answer in the assistant (`./setup.sh --configure`), what you will see, and the limits to know about.

> 🇫🇷 Version française : [cas-pratiques.md](cas-pratiques.md) · First install: [step-by-step guide](getting-started.md)

In the cockpit, the **Setup** screen (the flag in the left rail) always tells you what is in place and what is left to do, with commands ready to copy.

**Contents**

| Your situation | Recipe |
|---|---|
| One location, one network | [Small organisation](#small-organisation-one-network) |
| Several buildings or VLANs on one site | [Several buildings, one site](#several-buildings-or-vlans-on-one-site) |
| Several sites linked by VPN, fibre or MPLS | [Multi-site](#several-sites-linked-vpn-fibre-mpls) |
| Switches and firewall managed by a provider | [Outsourced network](#network-managed-by-a-provider) |
| No Active Directory domain | [No AD](#no-active-directory) |
| Hyper-V, Proxmox or physical servers | [No VMware](#no-vmware-hyper-v-proxmox-physical-servers) |
| Several ESXi hosts without vCenter | [Several ESXi](#several-esxi-hosts-without-vcenter) |
| Ubiquiti UniFi, Cisco or other switches | [Switches](#see-switches-port-by-port) |
| New addressing plan | [Re-addressing](#changing-addressing) |
| Small VM, homelab | [Low RAM](#small-machine-or-homelab) |
| Where to put the monitoring host, which flows to open | [Placement and flows](#where-to-put-the-monitoring-host) |
| Wall screen, team access | [Wall screen and access](#wall-screen-and-team-access) |

---

## Small organisation, one network

*One network (for example 192.168.10.0/24), a router or firewall, a few servers.*

- **In the assistant**: press Enter to almost everything. The detected network, gateway and DNS servers are right. Name your site ("HQ", "Office"…), then Enter at "Add another …?".
- **Then**: install the agent on your servers (*Setup* screen, step 4) and connect Telegram (step 5).
- **You will see**: the gateway, your servers, PCs, printers and Wi-Fi access points, with their names.

## Several buildings or VLANs on one site

*Building A on 192.168.10.0/24, building B on 192.168.20.0/24, or one VLAN per use (servers, workstations, phones, Wi-Fi).*

- **In the assistant**: pick **1) Building**. For the building the host is in, keep the detected network and add that building's other VLANs, comma-separated (`192.168.10.0/24, 192.168.11.0/24`). Then "Add another building?": its name and networks.
- **How to find the networks**: `ipconfig` on a PC in each building (IPv4 address and mask), or the scope list in the DHCP console.
- **Check** from the monitoring host: `ping <an address in the other building>`. If it does not answer, a firewall between VLANs blocks ping: ask for it to be opened from the monitoring host's IP.
- **You will see**: a building filter at the top of the cockpit, one branch per building in the topology, and devices grouped by building in Zabbix.

## Several sites linked (VPN, fibre, MPLS)

*A head office and branches, linked by a site-to-site VPN or a carrier network.*

- **One monitoring host is enough**, at the head office, as long as it can reach the branches' networks.
- **In the assistant**: pick **2) Site** (or **3) Branch**). Declare each site with its networks.
- **To open in the VPN or firewall**, from the monitoring host's IP to the branches: ICMP (ping) and the TCP discovery ports (listed in `config/cockpit.yml`, `scan.ports`). NetBIOS (UDP 137) gives Windows PC names across routers.
- **Agents in branches** send to the monitoring host on TCP 9090 and 3100. These ports must cross the VPN.
- **Limit**: a site with no route to the monitoring host is not visible. A second install in that site is possible, but the two cockpits are then independent.

## Network managed by a provider

*NetCockpit's original use case: no access to switches, firewall or routers.*

- **Everything works without access**: scan, names, VMware, agents, alerts.
- **Switches** are recognised through the ESXi hosts (CDP/LLDP of their NICs) and through Linux servers running the agent.
- **To ask your provider** to go further:
  1. a **read-only SNMP v2c community** from the monitoring host's IP: full port-by-port map, traffic, errors;
  2. **syslog forwarding** to the monitoring host (port 514);
  3. **LLDP or CDP enabled** on server-facing ports;
  4. their **agreement for the scan** (ping and a few ports every 30 minutes).
- Once you have the SNMP community, run the assistant again and enter it with the switch and firewall IPs.

## No Active Directory

*Workgroup, small business without a domain, homelab.*

- **In the assistant**: leave internal DNS **empty**.
- **Names** then come from NetBIOS (Windows PCs), VMware (VMs) and the agents (servers).
- **For the rest** (printers, cameras, NAS), name them by hand in `config/cockpit.yml`:
  ```yaml
  overrides:
    192.168.10.30: { name: NAS-Backup, role: nas }
    192.168.10.60: { name: Printer-Reception, role: printer }
  ```
  then `docker compose restart cockpit`.

## No VMware (Hyper-V, Proxmox, physical servers)

- **In the assistant**: press Enter at the VMware question.
- **Hyper-V**: install the Windows agent on the Hyper-V host and in the important VMs. You get CPU, RAM, disks and logs for each.
- **Proxmox**: install the Linux agent on the Proxmox host (it is Debian) and in the important VMs.
- **Physical servers**: the agent is enough. On Linux it also reads LLDP and knows which switch and port the server is plugged into.
- **Limit**: without VMware, the topology does not draw the "VM → host" link. Hyper-V and Proxmox inventory is on the roadmap.

## Several ESXi hosts without vCenter

- **Today NetCockpit connects to one VMware address.** With vCenter, every host reports. With several standalone ESXi hosts, give the most important one to the assistant.
- **The other ESXi hosts** stay visible as devices (ping, port 443), and **Zabbix** can monitor them natively: in Zabbix, create one host per ESXi with the "VMware" template and the macros `{$VMWARE.URL}` (`https://<ESXi>/sdk`), `{$VMWARE.USERNAME}` and `{$VMWARE.PASSWORD}`.
- Support for several ESXi hosts is on the roadmap.

## See switches port by port

| Hardware | How to enable read-only SNMP |
|---|---|
| Ubiquiti UniFi | *UniFi Network → Settings → CyberSecure → Traffic Logging*: enable SNMP v1/v2c, change the `public` community. USW Flex and Ultra do not support SNMP. |
| Cisco (IOS) | `snmp-server community <community> RO <ACL>`, with an ACL limited to the monitoring host's IP. |
| HPE Aruba, Netgear, D-Link, TP-Link… | *SNMP* menu of the web interface: create a read-only v2c community. |
| Managed by a provider | Ask for a read-only v2c community from the monitoring host's IP. |

Then run the assistant again: enter the community, then the switch and firewall IPs. Without SNMP, switches stay visible through ESXi hosts (CDP/LLDP) and the Linux agent (lldpd).

## Changing addressing

*Example: moving from 192.168.x.x to 10.x.x.x.*

1. **Before the move**, run the assistant and add the new networks **next to** the old ones, for each building: `192.168.10.0/24, 10.10.0.0/24`.
2. **During the move**, devices that change address appear under their new IP. Their old address turns grey (*absent*), with no false alert.
3. **After the move**, run the assistant and remove the old networks. Also update DNS servers and the gateway if they changed.
4. **If the monitoring host itself changes address**: run `./setup.sh` after the change, then reinstall the agent on the servers with the new address (or change the address in their Alloy configuration).

## Small machine or homelab

- **Less than 8 GB of RAM**: answer **n** to the Zabbix question. Everything else runs in 4 to 6 GB.
- **Homelab**: the demo (`docker compose -f docker-compose.demo.yml up`) lets you try without touching anything. For your real network, proceed as for a [small organisation](#small-organisation-one-network).
- **Shorter history**: `RETENTION=15d` in `.env`, then `./setup.sh`.

## Where to put the monitoring host

- **Best place**: the server VLAN, with a fixed IP address.
- **Outbound** from the monitoring host: ICMP and the discovery ports to every monitored network, TCP 443 to vCenter or ESXi, UDP 161 to switches (if SNMP), UDP 137 to PCs (NetBIOS).
- **Inbound** to the monitoring host: TCP 9090 and 3100 from servers running the agent, UDP/TCP 514 from firewalls and switches (syslog), TCP 8088, 3000 and 8081 from administrators' workstations.
- **Never publish** these ports on the Internet: several have no authentication.

## Wall screen and team access

- **Wall screen**: open **Topology**, tick **Problems only**, then switch the browser to full screen (F11). The night theme reads well from a distance.
- **Team access**: the cockpit has no user accounts yet. Restrict port 8088 to administrators' workstations (firewall rule or VLAN ACL). Grafana and Zabbix have their own accounts.
- **Everyone picks their language and theme** at the bottom of the left rail: the choice is remembered per browser.

---

A situation missing from this list? Open an [issue](https://github.com/B2ZO0/netcockpit/issues) or a [discussion](https://github.com/B2ZO0/netcockpit/discussions): the answer will join this page.
