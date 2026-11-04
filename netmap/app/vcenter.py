"""Interrogation de vCenter (lecture seule) : ESXi, VM, alarmes, voisins CDP/LLDP des cartes physiques."""
import logging
import ssl
import time
from urllib.parse import urlparse

log = logging.getLogger("netmap.vcenter")

try:
    from pyVim.connect import Disconnect, SmartConnect
    from pyVmomi import vim, vmodl
    HAVE_PYVMOMI = True
except ImportError:  # pragma: no cover
    HAVE_PYVMOMI = False


class VCenter:
    def __init__(self, url, user, password):
        u = urlparse(url if "://" in url else f"https://{url}")
        self.host = u.hostname
        self.port = u.port or 443
        self.user = user
        self.password = password
        self.si = None
        self.state = {"up": False, "error": "pas encore interrogé", "hosts": [], "vms": [], "datastores": [],
                      "alarms": [], "links": [], "updated": 0}

    # ------------------------------------------------------------ connexion
    def _connect(self):
        if self.si is not None:
            try:
                if self.si.content.sessionManager.currentSession is not None:
                    return
            except Exception:  # session expirée
                pass
            self.si = None
        ctx = ssl._create_unverified_context()
        self.si = SmartConnect(host=self.host, port=self.port, user=self.user, pwd=self.password, sslContext=ctx)
        log.info("connecté à vCenter %s", self.host)

    def close(self):
        if self.si:
            try:
                Disconnect(self.si)
            except Exception:
                pass

    # ------------------------------------------------------------ helpers
    def _collect(self, obj_type, path_set):
        content = self.si.RetrieveContent()
        view = content.viewManager.CreateContainerView(content.rootFolder, [obj_type], True)
        try:
            pc = vmodl.query.PropertyCollector
            traversal = pc.TraversalSpec(name="tv", path="view", skip=False, type=vim.view.ContainerView)
            obj_spec = pc.ObjectSpec(obj=view, skip=True, selectSet=[traversal])
            prop_spec = pc.PropertySpec(type=obj_type, pathSet=path_set, all=False)
            fspec = pc.FilterSpec(objectSet=[obj_spec], propSet=[prop_spec])
            out = []
            res = content.propertyCollector.RetrievePropertiesEx([fspec], pc.RetrieveOptions())
            while res:
                for obj in res.objects:
                    props = {p.name: p.val for p in (obj.propSet or [])}
                    props["_obj"] = obj.obj
                    out.append(props)
                if not res.token:
                    break
                res = content.propertyCollector.ContinueRetrievePropertiesEx(res.token)
            return out
        finally:
            view.Destroy()

    # ------------------------------------------------------------ collecte rapide (2 min)
    def poll(self):
        if not HAVE_PYVMOMI:
            self.state.update(up=False, error="pyvmomi non installé")
            return self.state
        try:
            self._connect()
            clusters = {c["_obj"]._moId: c.get("name") for c in
                        self._collect(vim.ClusterComputeResource, ["name"])}
            hosts = []
            host_names = {}
            for h in self._collect(vim.HostSystem, [
                    "name", "runtime.connectionState", "runtime.inMaintenanceMode", "runtime.powerState",
                    "config.network.vnic", "summary.hardware.vendor", "summary.hardware.model",
                    "summary.hardware.cpuMhz", "summary.hardware.numCpuCores", "summary.hardware.memorySize",
                    "summary.quickStats.overallCpuUsage", "summary.quickStats.overallMemoryUsage",
                    "summary.quickStats.uptime", "summary.overallStatus", "config.product.fullName", "parent"]):
                moid = h["_obj"]._moId
                host_names[moid] = h.get("name")
                ips = []
                for vnic in h.get("config.network.vnic") or []:
                    try:
                        if vnic.spec.ip.ipAddress:
                            ips.append(vnic.spec.ip.ipAddress)
                    except AttributeError:
                        pass
                parent = h.get("parent")
                mhz = (h.get("summary.hardware.cpuMhz") or 0) * (h.get("summary.hardware.numCpuCores") or 0)
                mem_mb = (h.get("summary.hardware.memorySize") or 0) / 1048576
                cpu_used = h.get("summary.quickStats.overallCpuUsage") or 0
                mem_used = h.get("summary.quickStats.overallMemoryUsage") or 0
                hosts.append({
                    "moid": moid, "name": h.get("name"), "ips": ips,
                    "state": str(h.get("runtime.connectionState")),
                    "maintenance": bool(h.get("runtime.inMaintenanceMode")),
                    "power": str(h.get("runtime.powerState")),
                    "health": str(h.get("summary.overallStatus")),
                    "model": f"{h.get('summary.hardware.vendor') or ''} {h.get('summary.hardware.model') or ''}".strip(),
                    "version": h.get("config.product.fullName"),
                    "cluster": clusters.get(parent._moId) if parent is not None else None,
                    "cores": h.get("summary.hardware.numCpuCores") or 0,
                    "cpu_mhz_total": mhz, "cpu_mhz_used": cpu_used,
                    "cpu_pct": round(cpu_used / mhz * 100, 1) if mhz else None,
                    "mem_gb": round(mem_mb / 1024, 1), "mem_used_gb": round(mem_used / 1024, 1),
                    "mem_pct": round(mem_used / mem_mb * 100, 1) if mem_mb else None,
                    "uptime_s": h.get("summary.quickStats.uptime"),
                    "_cpu_mhz_core": h.get("summary.hardware.cpuMhz") or 0,
                })
            core_mhz = {h["name"]: h["_cpu_mhz_core"] for h in hosts}
            vms = []
            for v in self._collect(vim.VirtualMachine, [
                    "name", "runtime.powerState", "runtime.host", "guest.ipAddress", "guest.net",
                    "guest.hostName", "guest.toolsRunningStatus", "config.guestFullName", "config.template",
                    "config.hardware.numCPU", "config.hardware.memoryMB",
                    "summary.quickStats.overallCpuUsage", "summary.quickStats.guestMemoryUsage",
                    "summary.quickStats.uptimeSeconds", "summary.storage.committed", "summary.overallStatus"]):
                if v.get("config.template"):
                    continue
                ips, macs = [], []
                for nic in v.get("guest.net") or []:
                    if nic.macAddress:
                        macs.append(nic.macAddress.lower())
                    for ip in nic.ipAddress or []:
                        if ":" not in ip and not ip.startswith("169.254."):
                            ips.append(ip)
                if v.get("guest.ipAddress") and ":" not in v["guest.ipAddress"] and v["guest.ipAddress"] not in ips:
                    ips.insert(0, v["guest.ipAddress"])
                host = v.get("runtime.host")
                hname = host_names.get(host._moId) if host is not None else None
                vcpu = v.get("config.hardware.numCPU") or 0
                mem_mb = v.get("config.hardware.memoryMB") or 0
                cpu_used = v.get("summary.quickStats.overallCpuUsage") or 0
                cap = vcpu * core_mhz.get(hname, 0)
                gmem = v.get("summary.quickStats.guestMemoryUsage") or 0
                vms.append({
                    "moid": v["_obj"]._moId, "name": v.get("name"), "ips": ips, "macs": macs,
                    "power": str(v.get("runtime.powerState")), "host": hname,
                    "hostname": v.get("guest.hostName"), "os": v.get("config.guestFullName"),
                    "tools": str(v.get("guest.toolsRunningStatus") or ""),
                    "health": str(v.get("summary.overallStatus")),
                    "vcpu": vcpu, "mem_gb": round(mem_mb / 1024, 1),
                    "cpu_pct": round(cpu_used / cap * 100, 1) if cap else None,
                    "mem_pct": round(gmem / mem_mb * 100, 1) if mem_mb else None,
                    "disk_gb": round((v.get("summary.storage.committed") or 0) / 1073741824, 1),
                    "uptime_s": v.get("summary.quickStats.uptimeSeconds"),
                })
            datastores = []
            for d in self._collect(vim.Datastore, ["name", "summary.capacity", "summary.freeSpace",
                                                   "summary.type", "summary.accessible", "host"]):
                cap = d.get("summary.capacity") or 0
                free = d.get("summary.freeSpace") or 0
                datastores.append({
                    "name": d.get("name"), "type": d.get("summary.type"),
                    "accessible": bool(d.get("summary.accessible")),
                    "capacity_gb": round(cap / 1073741824), "free_gb": round(free / 1073741824),
                    "used_pct": round((cap - free) / cap * 100, 1) if cap else None,
                    "hosts": sorted({host_names.get(m.key._moId, "") for m in (d.get("host") or []) if getattr(m, "key", None) is not None}),
                })
            alarms = self._alarms(host_names, {v["moid"]: v["name"] for v in vms})
            for h in hosts:
                h.pop("_cpu_mhz_core", None)
            self.state.update(up=True, error="", hosts=hosts, vms=vms, datastores=datastores, alarms=alarms, updated=time.time())
            log.info("vCenter : %d ESXi, %d VM, %d alarme(s)", len(hosts), len(vms), len(alarms))
        except Exception as e:  # réseau, identifiants, droits...
            log.warning("vCenter injoignable : %s", e)
            self.si = None
            self.state.update(up=False, error=str(e)[:200])
        return self.state

    def _alarms(self, host_names, vm_names):
        out = []
        names = dict(host_names, **vm_names)
        alarm_names = {}
        content = self.si.RetrieveContent()
        for st in content.rootFolder.triggeredAlarmState or []:
            status = str(st.overallStatus)
            if status not in ("red", "yellow"):
                continue
            ent_id = st.entity._moId
            if ent_id not in names:
                try:
                    names[ent_id] = st.entity.name
                except Exception:
                    names[ent_id] = ent_id
            al_id = st.alarm._moId
            if al_id not in alarm_names:
                try:
                    alarm_names[al_id] = st.alarm.info.name
                except Exception:
                    alarm_names[al_id] = al_id
            out.append({"entity": names[ent_id], "alarm": alarm_names[al_id], "status": status,
                        "acknowledged": bool(st.acknowledged)})
        return out

    # ------------------------------------------------------------ voisins réseau (à chaque scan)
    def network_links(self):
        """Pour chaque carte physique des ESXi : switch et port vus en CDP ou LLDP."""
        if not HAVE_PYVMOMI:
            return []
        links = []
        try:
            self._connect()
            for h in self._collect(vim.HostSystem, ["name", "runtime.connectionState", "config.network.vnic"]):
                if str(h.get("runtime.connectionState")) != "connected":
                    continue
                ips = []
                for vnic in h.get("config.network.vnic") or []:
                    try:
                        ips.append(vnic.spec.ip.ipAddress)
                    except AttributeError:
                        pass
                try:
                    hints = h["_obj"].configManager.networkSystem.QueryNetworkHint()
                except Exception as e:
                    log.debug("QueryNetworkHint %s : %s", h.get("name"), e)
                    continue
                for hint in hints or []:
                    cdp, lldp = hint.connectedSwitchPort, hint.lldpInfo
                    if cdp:
                        links.append({"host": h.get("name"), "host_ips": ips, "nic": hint.device, "proto": "CDP",
                                      "switch": cdp.devId or cdp.systemName, "port": cdp.portId,
                                      "switch_ip": cdp.address or cdp.mgmtAddr, "platform": cdp.hardwarePlatform})
                    elif lldp:
                        params = {p.key: p.value for p in (lldp.parameter or [])}
                        links.append({"host": h.get("name"), "host_ips": ips, "nic": hint.device, "proto": "LLDP",
                                      "switch": params.get("System Name") or lldp.chassisId,
                                      "port": params.get("Port Description") or lldp.portId,
                                      "switch_ip": params.get("Management Address"),
                                      "platform": params.get("System Description")})
            log.info("vCenter : %d lien(s) ESXi-switch trouvés en CDP/LLDP", len(links))
        except Exception as e:
            log.warning("lecture CDP/LLDP impossible : %s", e)
            self.si = None
        self.state["links"] = links
        return links
