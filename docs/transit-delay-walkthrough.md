# Transit Delay EKS Walkthrough (MVP)

Follow these steps to get a runnable, minimal slice of the project. Each step ends with a clear “check” so you know you’re on track.

## 0) Prerequisites
- CLI: `aws` (profile set), `kubectl`, `helm`, `docker` or `nerdctl`, `python3.11`, `pipx` or `pip`.
- Cluster: an EKS cluster with an IAM role that can read/write S3 and, if using Kinesis, `kinesis:*` on the target stream. A default StorageClass and a metrics server (for HPA) should exist.
- Buckets/streams: create (or reuse) S3 buckets for `raw/`, `processed/`, and `models/`. If you skip live streaming, you can replay `projects/transit-delay-eks/data/sample_bus_events.json`.

## 1) Local smoke test
```bash
cd projects/transit-delay-eks/services/ingest
python consumer.py --events ../data/sample_bus_events.json --s3-bucket YOUR_BUCKET --dry-run
```
Check: logs show 3 sample events validated; no S3 writes when `--dry-run` is set.

## 2) Build/push images (replace ECR repo names)
```bash
docker build -t $ECR/td-ingest:0.1 -f projects/transit-delay-eks/services/ingest/Dockerfile .
docker build -t $ECR/td-api:0.1 -f projects/transit-delay-eks/services/api/Dockerfile .
docker build -t $ECR/td-train:0.1 -f projects/transit-delay-eks/services/train/Dockerfile .
docker push $ECR/td-ingest:0.1 && docker push $ECR/td-api:0.1 && docker push $ECR/td-train:0.1
```
Check: images are visible in ECR and pullable from your node group.

## 3) Deploy to EKS
```bash
kubectl apply -f projects/transit-delay-eks/k8s/namespace.yaml
kubectl apply -f projects/transit-delay-eks/k8s/consumer-deployment.yaml
kubectl apply -f projects/transit-delay-eks/k8s/api-deployment.yaml
kubectl apply -f projects/transit-delay-eks/k8s/api-service.yaml
kubectl apply -f projects/transit-delay-eks/k8s/api-hpa.yaml
```
Check: `kubectl get pods -n transit-delay` shows 1/1 READY for consumer and api; HPA has current CPU metrics.

## 4) Run a training job (on-demand)
```bash
kubectl create -f projects/transit-delay-eks/k8s/train-job.yaml
kubectl logs job/td-train -n transit-delay -f
```
Check: job exits `Completed`; S3 has `models/<timestamp>/model.joblib` and `metrics.json`.

## 5) Hit the API
```bash
kubectl port-forward svc/td-api -n transit-delay 8000:80
curl -X POST http://localhost:8000/predict -H "Content-Type: application/json" -d '{"route_id":"M15","stop_id":"STOP_100","delay_seconds":180,"timestamp":1717000100}'
```
Check: Response includes `late_probability` and `is_late` boolean; `/healthz` returns `{"status":"ok"}`.

## 6) Observability quick wins
- Annotated manifests already expose Prometheus metrics; install the kube-prometheus-stack Helm chart and add the namespace to the scrape config.
- Create a simple Grafana dashboard showing: request rate/latency for `td-api`, error counts on the consumer, and distribution of `late_probability`.

## 7) Stretch goals
- Add weather as a feature (Open-Meteo API); store enriched data in `processed/`.
- Add a drift check CronJob computing PSI for `delay_seconds` vs. a baseline window; push results to CloudWatch Metrics.
- Switch Kinesis → MSK if you need more control; reuse the consumer container.
