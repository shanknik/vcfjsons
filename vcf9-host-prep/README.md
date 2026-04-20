# VCF-HostPrep

A PowerShell script to automate and verify ESXi host preparation for VMware Cloud Foundation (VCF) commissioning. Designed for standalone hosts with no vCenter — run this before importing hosts into SDDC Manager.

---

## What It Does

| Step | Action |
|---|---|
| 1 | Checks and installs prerequisites (PowerCLI, Posh-SSH) |
| 2 | Configures NTP servers and sets the ntpd service to auto-start |
| 3 | Sets vSwitch0 MTU to 9000 (required for VCF/NSX overlay networking) |
| 4 | Reads the current cert CN and compares it to the configured hostname |
| 5 | Regenerates the self-signed certificate if CN does not match (per Broadcom TechDocs) |
| 6 | Reboots affected hosts and waits for them to come back online automatically |
| 7 | Re-reads the cert CN post-reboot to confirm it is correct |
| 8 | Outputs a full verification summary table and exports a timestamped CSV report |

---

## Why This Matters for VCF

SDDC Manager validates ESXi host identity over HTTPS during commissioning. If the common name (CN) in the host self-signed certificate does not match the configured FQDN, commissioning will fail. This script catches and fixes that condition automatically — along with NTP and MTU settings that are equally required for a successful VCF bring-up.

---

## Requirements

| Requirement | Details |
|---|---|
| OS | Windows (PowerShell 5.1+) |
| PowerCLI | VMware.PowerCLI 13+ (auto-installed if missing) |
| Posh-SSH | 2.x or 3.x (auto-installed if missing) |
| ESXi | 8.x / 9.x standalone (no vCenter required) |
| Network | HTTPS (443) and SSH (22) access to each ESXi host |
| Permissions | Run PowerShell as Administrator for module installation |

> The script auto-detects the correct `New-SSHSession` parameter syntax for your installed version of Posh-SSH — no manual version management needed.

> On ESXi 9 the NTP firewall rule is owned by the system service and cannot be set manually. The script handles this gracefully and skips the step — the rule is managed automatically by ntpd.

---

## Usage

```powershell
# Run as Administrator
.
VCF-HostPrep.ps1
```

You will be prompted for: