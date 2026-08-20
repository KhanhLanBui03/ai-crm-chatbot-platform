# docker/ — cấu hình cho các container hạ tầng

| Thư mục | Nội dung |
|---|---|
| `prometheus/` | `prometheus.yml` — danh sách target thu thập số liệu |
| `grafana/provisioning/` | Datasource và dashboard khai báo bằng file, để tái lập được |

Ba bảng điều khiển Grafana là đủ (kế hoạch mục 4.5): **sức khỏe hệ thống**, **đường ống AI**,
**chỉ số nghiệp vụ**. Đừng làm nhiều hơn.

Bật bằng profile riêng:

```bash
docker compose --profile observability up -d
```

Grafana: http://localhost:3000 · Prometheus: http://localhost:9090
