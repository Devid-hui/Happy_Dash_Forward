# Naifrog publication and independent remote readback

Actual character commit 9f27f2281b63cad171d28a8402dbe797323c3790 was pushed successfully. Fresh remote fetch and actual LFS download verified 15 key file SHA values. These receipts identify that commit, not subsequent documentation/CI follow-ups.

Its first cloud run 38351268709 obtained LFS correctly, then timed out at 120 seconds during cold Godot import (62 percent). Full raw failure log is retained. The follow-up uses the existing runner timeout option with 360 seconds and preserves all failure gates.
