# Class Demo Check

- Generated at: `2026-05-07 14:09:45 UTC`
- Overall: `READY`

| Status | Check | Detail |
|---|---|---|
| OK | make demo-proof | passed; log: `<project-root>/reports/class_demo_demo-proof.log` |
| OK | make final-audit | passed; log: `<project-root>/reports/class_demo_final-audit.log` |
| OK | demo proof report | 2880 bytes |
| OK | final audit report | 8474 bytes |
| OK | QR presentation PDF | 1476864 bytes |
| OK | QR presentation PPTX | 94398 bytes |
| OK | brochure PDF | 606955 bytes |
| OK | e-kampus zip | 2342794 bytes |
| OK | Docker daemon | reachable: 29.4.0 |
| OK | brochure QR link | GET 200; remote size matches local PDF (606955 bytes) |
| OK | live local dashboard server | 127.0.0.1:8000 /health status=ok |

## Demo Order

1. Open the QR presentation PDF.
2. Show the QR slide and let classmates open the brochure.
3. Run `make -C <project-root> demo-proof`.
4. If you want the browser dashboard, run `make -C <project-root> serve` and open `http://127.0.0.1:8000/dashboard?top_n=10`.
5. Show `reports/final_project_audit.md`: it should say `READY`, `0 fail, 0 warn`.

## Cost Safety

This check does not create EKS, EC2, LoadBalancer, or other paid AWS runtime resources. It only reads local files, checks Docker, calls the local API if running, and validates the existing brochure QR link.
