---
name: block-dangerous-rm
enabled: true
event: bash
pattern: rm\s+-rf?\s+\/(?:etc|usr|var|bin|lib(?:64)?|boot|sbin|opt|root|sys|proc|dev)(?:\/|\s|$)
action: block
---

⛔ Blocked: Deleting system directories is a destructive operation.

This rule blocks recursive rm into core Linux system directories:
/etc, /usr, /var, /bin, /lib, /boot, /sbin, /lib64, /opt, /root, /sys, /proc, /dev

If you have a legitimate reason to delete files in these directories,
disable this rule by setting `enabled: false` in this file, or
remove the file from .opencode/hookify/rules/.
