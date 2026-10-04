"""Static model of the Smart Campus: zones, monitored gateways and devices."""
from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class Zone:
    id: str
    name: str
    gateway: str          # SNMP-polled device (the counter source)
    description: str
    load: float           # relative traffic level vs. the training-device baseline


@dataclass(frozen=True)
class Device:
    id: str
    name: str
    type: str
    zone: str
    ip: str
    services: tuple = ()


ZONES = [
    Zone("student", "Student Network", "GW-STU-01", "Student computers, mobiles, student Wi-Fi, LMS access", 1.04),
    Zone("faculty", "Faculty Network", "GW-FAC-01", "Faculty PCs, Wi-Fi, email, LMS, web services", 0.98),
    Zone("admin", "Administration", "GW-ADM-01", "Administrative PCs, databases, management systems", 0.96),
    Zone("labs", "Computer Labs", "GW-LAB-01", "Lab PCs, lab servers, shared services", 1.02),
    Zone("iot", "IoT Network", "GW-IOT-01", "CCTV, sensors, smart classroom, access control, lighting, RFID", 0.97),
    Zone("services", "Campus Services", "GW-SRV-01", "DNS, web, database, LMS and authentication servers", 1.00),
]

DEVICES = [
    Device("stu-pc-01", "Student PC Pool", "computer", "student", "10.10.1.0/24", ("web", "lms")),
    Device("stu-wifi-01", "Student Wi-Fi AP Cluster", "wifi", "student", "10.10.2.0/23", ("web",)),
    Device("stu-mob-01", "Student Mobile Devices", "mobile", "student", "10.10.4.0/22", ("web", "lms")),
    Device("fac-pc-01", "Faculty Workstations", "computer", "faculty", "10.20.1.0/24", ("auth", "lms", "email")),
    Device("fac-wifi-01", "Faculty Wi-Fi", "wifi", "faculty", "10.20.2.0/24", ("web",)),
    Device("adm-pc-01", "Admin Workstations", "computer", "admin", "10.30.1.0/24", ("auth", "erp")),
    Device("adm-db-01", "Records Database", "server", "admin", "10.30.10.5", ("sql",)),
    Device("adm-mgmt-01", "Management System", "server", "admin", "10.30.10.6", ("web", "auth")),
    Device("lab-pc-01", "Lab A PCs", "computer", "labs", "10.40.1.0/24", ("web", "git")),
    Device("lab-pc-02", "Lab B PCs", "computer", "labs", "10.40.2.0/24", ("web", "git")),
    Device("lab-srv-01", "Lab Server", "server", "labs", "10.40.10.2", ("ssh", "nfs")),
    Device("iot-cctv-01", "CCTV Cameras", "iot", "iot", "10.50.1.0/24", ("rtsp",)),
    Device("iot-temp-01", "Temperature Sensors", "iot", "iot", "10.50.2.0/24", ("mqtt",)),
    Device("iot-class-01", "Smart Classroom Controllers", "iot", "iot", "10.50.3.0/24", ("mqtt", "http")),
    Device("iot-acc-01", "Access Control Panels", "iot", "iot", "10.50.4.0/24", ("https",)),
    Device("iot-light-01", "Smart Lighting", "iot", "iot", "10.50.5.0/24", ("mqtt",)),
    Device("iot-rfid-01", "RFID Readers", "iot", "iot", "10.50.6.0/24", ("https",)),
    Device("iot-gw-01", "IoT Gateway", "gateway", "iot", "10.50.0.1", ("mqtt", "https")),
    Device("srv-dns-01", "DNS Server", "server", "services", "10.60.0.53", ("dns",)),
    Device("srv-web-01", "Web Server", "server", "services", "10.60.0.80", ("http", "https")),
    Device("srv-db-01", "Database Server", "server", "services", "10.60.0.33", ("sql",)),
    Device("srv-lms-01", "LMS", "server", "services", "10.60.0.90", ("https",)),
    Device("srv-auth-01", "Authentication Server", "server", "services", "10.60.0.88", ("ldap", "radius")),
]

ZONE_BY_ID = {z.id: z for z in ZONES}


def zones_dict():
    return [asdict(z) for z in ZONES]


def devices_dict():
    return [asdict(d) for d in DEVICES]
