# Linux Commands Cheatsheet — Module 1

Focused on what you actually need for container work and the rest of the OpenShift
course. Examples lean telecom (CDR logs, gateway services) where it helps.

> Shell: `bash`/`zsh` on Linux/macOS. On RHEL/UBI, the package manager is `dnf`.

---

## 1. Navigation & filesystem

| Command | What it does |
|---------|--------------|
| `pwd` | Print current directory |
| `ls -lah` | List all files, long format, human-readable sizes |
| `cd /path` · `cd -` · `cd ~` | Change dir · previous dir · home |
| `tree -L 2` | Directory tree, 2 levels deep |
| `find . -name "*.log"` | Find files by name |
| `find /var/log -mmin -10` | Files modified in the last 10 minutes |
| `du -sh *` | Size of each item in current dir |
| `df -h` | Free disk space per filesystem |
| `stat file` | Detailed metadata (size, perms, timestamps) |
| `readlink -f file` | Resolve to absolute/real path |

---

## 2. Files & directories

| Command | What it does |
|---------|--------------|
| `mkdir -p a/b/c` | Create nested directories |
| `touch file` | Create empty file / update timestamp |
| `cp -r src dst` | Copy (recursively) |
| `mv old new` | Move / rename |
| `rm -rf dir` | Remove recursively (⚠️ irreversible) |
| `ln -s target link` | Create a symbolic link |
| `chmod +x script.sh` | Make executable |
| `chmod 640 file` | Set octal permissions (rw-r-----) |
| `chown user:group file` | Change owner/group |

---

## 3. Viewing & editing files

| Command | What it does |
|---------|--------------|
| `cat file` | Print whole file |
| `less file` | Page through (q to quit, / to search) |
| `head -n 20 file` | First 20 lines |
| `tail -n 50 file` | Last 50 lines |
| `tail -f gateway.log` | **Follow** a log live (great for tailing a service) |
| `wc -l cdr.csv` | Count lines |
| `nano file` / `vi file` | Edit in terminal |

---

## 4. Searching: `grep` & `find`

| Command | What it does |
|---------|--------------|
| `grep "ERROR" app.log` | Lines containing ERROR |
| `grep -i "timeout" *.log` | Case-insensitive, all logs |
| `grep -r "966500" .` | Recursive search (e.g. an MSISDN prefix) |
| `grep -c "DELIVERED" sms.log` | Count matches |
| `grep -v "DEBUG" app.log` | Invert: lines *not* matching |
| `grep -E "FAIL|DROP" cdr.log` | Extended regex (OR) |
| `find . -type f -size +100M` | Files larger than 100 MB |
| `find . -name "*.tmp" -delete` | Find and delete matches |

---

## 5. Text processing (pipelines)

| Command | What it does |
|---------|--------------|
| `cut -d, -f1,3 cdr.csv` | Columns 1 & 3 of a comma-separated file |
| `sort file` · `sort -u` | Sort · sort + dedupe |
| `uniq -c` | Count consecutive duplicates (after `sort`) |
| `awk -F, '{print $2}' cdr.csv` | Print 2nd field (MSISDN, say) |
| `awk -F, '$4>60' cdr.csv` | Rows where field 4 (duration) > 60 |
| `sed 's/old/new/g' file` | Stream-replace text |
| `tr 'a-z' 'A-Z'` | Translate characters (lower→upper) |
| `xargs` | Build command lines from input |

**Telecom example — top 5 calling numbers in a CDR file:**
```bash
cut -d, -f2 cdr.csv | sort | uniq -c | sort -rn | head -5
```

---

## 6. Redirection & pipes

| Syntax | Meaning |
|--------|---------|
| `cmd > file` | stdout → file (overwrite) |
| `cmd >> file` | stdout → file (append) |
| `cmd 2> err.log` | stderr → file |
| `cmd > out 2>&1` | stdout + stderr → file |
| `cmd1 \| cmd2` | Pipe stdout of cmd1 into cmd2 |
| `cmd < input` | Feed file as stdin |
| `cmd1 && cmd2` | Run cmd2 only if cmd1 succeeds |
| `cmd1 \|\| cmd2` | Run cmd2 only if cmd1 fails |

---

## 7. Processes & resources

| Command | What it does |
|---------|--------------|
| `ps aux` | All running processes |
| `ps -ef \| grep nginx` | Find a process |
| `top` / `htop` | Live process/resource monitor |
| `kill <pid>` | Send SIGTERM (graceful) |
| `kill -9 <pid>` | Send SIGKILL (force) |
| `pkill -f app.py` | Kill by command pattern |
| `free -h` | Memory usage |
| `uptime` | Load average |
| `nproc` | Number of CPU cores |
| `jobs` · `bg` · `fg` | Manage shell background jobs |
| `nohup cmd &` | Run detached from the terminal |

---

## 8. The kernel features behind containers

These are the **namespaces** and **cgroups** from Visualization 02 — inspect them
directly:

| Command | What it does |
|---------|--------------|
| `lsns` | List namespaces on the host |
| `lsns -t net` | Network namespaces only |
| `ls -l /proc/<pid>/ns/` | Namespaces a process belongs to |
| `unshare --pid --fork --mount-proc bash` | Spawn a shell in a new PID namespace (DIY mini-container) |
| `cat /proc/cgroups` | Available cgroup controllers |
| `systemd-cgls` | Tree of cgroups |
| `cat /sys/fs/cgroup/.../memory.max` | A cgroup's memory limit |
| `nsenter -t <pid> -n ip addr` | Run a command inside another process's net namespace |
| `capsh --print` | Show Linux capabilities |

---

## 9. Networking

| Command | What it does |
|---------|--------------|
| `ip addr` | Show interfaces & IPs |
| `ip route` | Routing table |
| `ss -tulpn` | Listening TCP/UDP ports + owning process |
| `ping host` | Reachability test |
| `curl -s http://host:8080/health` | HTTP request (test an API) |
| `curl -I url` | Headers only |
| `wget url` | Download a file |
| `dig host` / `nslookup host` | DNS lookup |
| `getent hosts name` | Resolve a name (works for container DNS too) |
| `nc -zv host 5432` | Test if a TCP port is open (e.g. DB) |
| `traceroute host` | Path to a host |

**Telecom example — is the CDR database port reachable?**
```bash
nc -zv cdr-db 5432 && echo "DB reachable"
```

---

## 10. Package management (RHEL / UBI)

| Command (RHEL/`dnf`) | Debian/Ubuntu (`apt`) | What it does |
|----------------------|------------------------|--------------|
| `dnf install -y pkg` | `apt install -y pkg` | Install a package |
| `dnf remove pkg` | `apt remove pkg` | Remove |
| `dnf update` | `apt update && apt upgrade` | Update packages |
| `dnf search term` | `apt search term` | Search |
| `dnf info pkg` | `apt show pkg` | Package details |
| `rpm -qa` | `dpkg -l` | List installed packages |

---

## 11. Archives & file transfer

| Command | What it does |
|---------|--------------|
| `tar -czf out.tgz dir/` | Create gzip tarball |
| `tar -xzf out.tgz` | Extract gzip tarball |
| `tar -tzf out.tgz` | List contents without extracting |
| `gzip file` / `gunzip file.gz` | Compress / decompress |
| `scp file user@host:/path` | Copy over SSH |
| `rsync -avz src/ user@host:/dst/` | Efficient sync over SSH |

---

## 12. systemd & logs (RHEL nodes)

| Command | What it does |
|---------|--------------|
| `systemctl status sshd` | Service status |
| `systemctl start\|stop\|restart svc` | Control a service |
| `systemctl enable --now svc` | Start now + on boot |
| `journalctl -u svc` | Logs for a service |
| `journalctl -f` | Follow all logs live |
| `journalctl --since "10 min ago"` | Time-filtered logs |

---

## 13. Environment, shell & SSH

| Command | What it does |
|---------|--------------|
| `env` / `printenv` | Show environment variables |
| `export VAR=value` | Set an env var for this session |
| `echo $VAR` | Print a variable |
| `alias docker=podman` | Make `docker` run Podman |
| `history` | Command history (`!123` re-runs #123) |
| `which cmd` / `type cmd` | Locate a command |
| `man cmd` / `cmd --help` | Help |
| `ssh user@host` | Connect to a remote host |
| `ssh-keygen -t ed25519` | Generate an SSH key pair |
| `chmod +x` then `./script.sh` | Run a local script |

---

## 14. Handy one-liners

```bash
# Watch a value refresh every 2s (e.g. container count)
watch -n2 'podman ps -q | wc -l'

# Free up disk: biggest dirs under /var
du -h /var --max-depth=1 | sort -rh | head

# Tail a gateway log and highlight failures
tail -f gateway.log | grep --line-buffered -E "FAIL|ERROR"

# Count HTTP 5xx in an access log
awk '$9 ~ /^5/ {c++} END{print c}' access.log
```

> **Safety:** `rm -rf`, `>` (overwrite), and `kill -9` are irreversible. Double-check
> the target path before pressing Enter — especially on a shared lab cluster.
