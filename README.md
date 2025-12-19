# UAS Sistem Paralel dan Terdistribusi
## Pub-Sub Log Aggregator Terdistribusi
### (Idempotent Consumer, Deduplication, Transaksi & Kontrol Konkurensi)

---

## 1. Gambaran Umum
Project ini merupakan implementasi **sistem log aggregator terdistribusi** berbasis arsitektur **publish–subscribe**.  
Sistem dirancang untuk:
- Menangani **duplikasi event**
- Aman terhadap **retry & crash**
- Mendukung **multi-worker concurrency**
- Menjamin **konsistensi data** melalui transaksi database
- Berjalan **sepenuhnya di Docker Compose (jaringan lokal)**

---

## 2. Arsitektur Sistem
```
Publisher
   |
   v
Redis Streams (Broker)
   |
   v
Aggregator API (FastAPI)
(Multi Worker Consumer)
   |
   v
PostgreSQL (Dedup + Events + Stats)
```

**Penjelasan singkat:**
- **Publisher**: simulator pengirim event (termasuk duplikasi)
- **Redis Streams**: message broker internal (at-least-once delivery)
- **Aggregator**: memproses event secara idempotent
- **PostgreSQL**: penyimpanan persisten + deduplication

---

## 3. Teknologi yang Digunakan
| Komponen | Teknologi |
|--------|----------|
| API | Python FastAPI |
| Broker | Redis Streams |
| Database | PostgreSQL 16 |
| Orkestrasi | Docker Compose |
| Testing | Pytest (14 test files) |

---

## 4. Prasyarat
Pastikan sudah terinstall:
- Docker Desktop
- Docker Compose v2

Cek:
```bash
docker --version
docker compose version
```

---

## 5. Menjalankan Sistem (STEP BY STEP)

### 5.1 Clone Repository
```bash
git clone <repo-anda>
cd <repo-anda>
```

---

### 5.2 Build dan Jalankan Semua Service
```bash
docker compose up --build -d
```

Service yang aktif:
- Aggregator API → http://localhost:8080
- Redis → internal
- PostgreSQL → internal

---

### 5.3 Inisialisasi Database (WAJIB, SEKALI SAJA)
Langkah ini membuat tabel dedup, events, dan stats.

```bash
docker cp ./aggregator/app/sql/001_init.sql $(docker compose ps -q storage):/tmp/001_init.sql
docker compose exec storage psql -U user -d db -f /tmp/001_init.sql
```

Jika berhasil, akan muncul output `CREATE TABLE`.

---

## 6. Menjalankan API Secara Manual

### 6.1 Publish Event
Endpoint:
```
POST http://localhost:8080/publish
```

Contoh payload:
```json
{
  "events": [
    {
      "topic": "ops",
      "event_id": "EVT-001",
      "timestamp": "2025-01-01T10:00:00Z",
      "source": "manual",
      "payload": { "msg": "hello" }
    }
  ]
}
```

---

### 6.2 Melihat Event yang Sudah Diproses
```bash
GET http://localhost:8080/events?topic=ops
```

---

### 6.3 Melihat Statistik Sistem
```bash
GET http://localhost:8080/stats
```

Statistik mencakup:
- received
- unique_processed
- duplicate_dropped
- topics
- uptime

---

## Ringkasan Endpoint API

| Method | Endpoint | Deskripsi |
|------|---------|----------|
| POST | `/publish` | Menerima satu atau batch event untuk dipublish ke broker |
| GET | `/events` | Menampilkan event unik yang telah diproses (filter by topic) |
| GET | `/stats` | Menampilkan statistik sistem |

Catatan:
- Endpoint `/publish` bersifat **idempotent secara hasil**.
- Endpoint `/events` hanya menampilkan event **unik**.

---

## 7. Deduplication & Idempotency (Hal Penting)
- Event unik ditentukan oleh kombinasi `(topic, event_id)`
- Dedup dilakukan di database menggunakan:
```sql
INSERT ... ON CONFLICT DO NOTHING
```
- Aman terhadap:
  - event duplikat
  - retry publisher
  - multi-worker concurrency
  - restart container

---

## 8. Menjalankan Publisher (Load Test Internal)
Publisher akan mengirim:
- ≥ 20.000 event
- ≥ 30% duplikasi

Command:
```bash
docker compose --profile load up --build publisher
```

---

## 9. Menjalankan Test (PENTING UNTUK UAS)

### 9.1 Penjelasan Struktur Test
Folder `tests/` berisi **banyak file**, misalnya:
- `test_api_validation.py`
- `test_dedup_idempotency.py`
- `test_concurrency.py`
- `test_persistence_restart.py`

Semua test dijalankan **secara otomatis**.

---

### 9.2 Cara Menjalankan Semua Test
```bash
docker compose --profile test run --rm tester
```

Jika berhasil, akan muncul output:
```
14 passed
```

---

## 10. Uji Persistensi (Demo Wajib)
Langkah untuk membuktikan data tetap ada:

```bash
docker compose rm -sf aggregator
docker compose up -d aggregator
```

Lalu cek kembali:
```bash
GET /events
GET /stats
```

Data tetap ada karena menggunakan **named volume PostgreSQL**.

---

## 11. Logging & Observability
Lihat log aggregator:
```bash
docker compose logs -f aggregator
```

---

## Asumsi dan Batasan Sistem

Beberapa asumsi dan batasan dalam perancangan sistem ini:
1. Sistem menggunakan **at-least-once delivery**.
2. Konsistensi dijaga melalui **idempotent consumer**, bukan exactly-once delivery.
3. Ordering event tidak dijamin secara global.
4. Sistem berjalan pada jaringan lokal Docker Compose.
5. Fokus utama adalah konsistensi dan ketahanan duplikasi.

---

## 12. Video Demo
Video demo (YouTube Unlisted/Public) mencakup:
1. Arsitektur sistem
2. Build & run Docker Compose
3. Event duplikat & deduplication
4. Konkurensi multi-worker
5. Restart container & persistensi data
6. Statistik & logging

**Link video demo:** 
taruh disini

---
 
## 13. Author
Nama  : Dhio Anugrah Prakasa Putro  
NIM   : 11221004  
Mata Kuliah : Sistem Paralel dan Terdistribusi
