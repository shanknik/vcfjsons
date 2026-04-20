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
.\VCF-HostPrep.ps1
```

You will be prompted for:

```
Hosts      : wld-h1.lab.local, wld-h2.lab.local, wld-h3.lab.local
Username   : root
Password   : ********
NTP Servers: 192.168.1.10
DNS Servers: 192.168.1.10
```

The script handles everything from there — including reboots where needed — with no further input required.

---

## Output

### Console (per host)

```
========================================
 Processing: wld-h1.lab.local
========================================
  [+] PowerCLI connected
  [+] NTP configured
  [+] vSwitch0 MTU set to 9000
  [i] Configured hostname : wld-h1.lab.local
  [i] Certificate CN      : localhost.localdomain
  [!] CN mismatch - regenerating certificate...
  [i] New certificate CN  : wld-h1.lab.local
  [+] New CN matches hostname - will reboot and verify

========================================
 Rebooting Hosts & Awaiting Online
========================================
  [+] Reboot command sent
  [+] Host offline after 40 seconds
  [+] Host responding to ping after 130 seconds
  [+] Post-reboot CN confirmed correct
```

### Final Summary Table

```
Host             Hostname         NTP OK  Auto-Start  Svc Running  DNS OK  MTU OK  Cert Match  Cert Action                        Reboot Needed  Overall
----             --------         ------  ----------  -----------  ------  ------  ----------  -----------                        -------------  -------
wld-h1.lab.local wld-h1.lab.local PASS    PASS        PASS         PASS    PASS    MATCH       Regenerated - confirmed post-reboot Done           PASS
wld-h2.lab.local wld-h2.lab.local PASS    PASS        PASS         PASS    PASS    MATCH       None required                      No             PASS
```

### CSV Report

Saved automatically to `%USERPROFILE%\Desktop\VCF_HostPrep_YYYYMMDD_HHMMSS.csv`

---

## Reboot Behaviour

- A reboot is only triggered if the cert CN did not match and was regenerated
- The script polls every 10 seconds waiting for the host to go offline (2 minute timeout)
- Then polls every 10 seconds waiting for it to come back online (10 minute timeout)
- Allows a 30 second warmup after ping responds for ESXi services to stabilise
- Post-reboot the cert CN is re-read and verified before marking the host as passed
- If a host times out it is flagged in the summary for manual follow-up
- No user input is required during the reboot wait cycle

---

## Verification Checks

| Check | Pass Condition |
|---|---|
| NTP Servers | All expected NTP servers are configured on the host |
| NTP Auto-Start | ntpd service policy is set to on |
| NTP Running | ntpd service is currently running |
| DNS Servers | All expected DNS servers are configured on the host |
| vSwitch0 MTU | MTU equals 9000 |
| Cert CN | CN in /etc/vmware/ssl/rui.crt matches the hostname output |

All six checks must pass for a host to show PASS in the Overall column.

---

## SSH Handling

SSH is used only for certificate operations — reading the current CN and running `/sbin/generate-certificates`. The script:

- Records whether SSH was already enabled before starting
- Enables SSH only if it was not already running
- Restores SSH to its original state after cert operations complete on each host

---

## Troubleshooting

**Host shows UNREACHABLE**
- Confirm the hostname resolves in DNS or use the IP address directly in the host list
- Confirm port 443 is reachable: `Test-NetConnection -ComputerName <host> -Port 443`
- Confirm port 22 is reachable: `Test-NetConnection -ComputerName <host> -Port 22`

**PowerCLI keeps reinstalling**
- The check uses `VMware.VimAutomation.Core` as the detection module — confirm it exists with `Get-Module -ListAvailable VMware.VimAutomation.Core`

**Encoding errors on run**
- Save the script as UTF-8 in VS Code: bottom right corner, click encoding, Save with Encoding, UTF-8
- All status strings in this script are plain ASCII with no emoji to avoid encoding issues

**NTP firewall rule error on ESXi 9**
- Expected and handled automatically — ESXi 9 manages the NTP Client firewall rule via the system service, the script skips this step gracefully

---

## Related

- [LAB2PROD YouTube Channel](https://youtube.com/@LAB2PROD) — VCF lab to production walkthroughs
- [Broadcom TechDocs - Regenerate Self-Signed Certificate](https://techdocs.broadcom.com/us/en/vmware-cis/vcf/vcf-5-2-and-earlier/4-5/administering/prepare-esxi-hosts-for-vmware-cloud-foundation-admin/install-esxi-interactively-and-configure-hosts-for-vmware-cloud-foundation-admin/regenerate-the-self-signed-certificate-on-all-hosts-admin.html)
- [VMware PowerCLI Documentation](https://developer.broadcom.com/powercli)
- [Posh-SSH on PowerShell Gallery](https://www.powershellgallery.com/packages/Posh-SSH)

---

## License

MIT
