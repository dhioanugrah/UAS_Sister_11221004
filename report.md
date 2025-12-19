# Laporan UAS Sistem Terdistribusi  
## Implementasi Pub-Sub Log Aggregator Terdistribusi dengan Idempotent Consumer, Deduplication, dan Kontrol Konkurensi

---

## 1. Pendahuluan
Perkembangan sistem informasi modern menuntut kemampuan untuk memproses data dalam jumlah besar secara terdistribusi. Sistem terdistribusi memungkinkan pembagian beban kerja ke beberapa komponen yang berjalan secara paralel, namun juga menghadirkan tantangan berupa konsistensi data, duplikasi pesan, kegagalan parsial, serta masalah konkurensi. Salah satu arsitektur yang umum digunakan untuk menangani kebutuhan tersebut adalah **publish–subscribe (pub-sub)**.

Pada tugas Ujian Akhir Semester ini, dibangun sebuah sistem **Pub-Sub Log Aggregator Terdistribusi** yang berfokus pada penerapan konsep idempotent consumer, deduplication persisten, serta transaksi dan kontrol konkurensi. Implementasi dilakukan menggunakan Docker Compose agar seluruh layanan berjalan pada jaringan lokal tanpa ketergantungan pada layanan eksternal publik.

---

## 2. Gambaran Umum Sistem
Sistem yang dikembangkan terdiri dari beberapa layanan utama, yaitu publisher, broker, aggregator, dan storage. Publisher berperan sebagai penghasil event log, broker sebagai perantara pesan, aggregator sebagai pemroses event, dan storage sebagai penyimpan data persisten. Komunikasi antar layanan dilakukan secara asinkron melalui mekanisme pub-sub.

Pendekatan ini memungkinkan sistem untuk menangani duplikasi pesan dan kegagalan komponen tanpa menyebabkan inkonsistensi data. Dengan demikian, sistem tetap dapat beroperasi secara andal meskipun terjadi retry pengiriman event atau restart container.

---

## 3. T1 – Karakteristik Sistem Terdistribusi dan Trade-off Desain
Sistem terdistribusi memiliki karakteristik utama berupa concurrency, absence of global clock, serta kemungkinan terjadinya partial failure. Komponen dalam sistem tidak berbagi memori dan hanya berkomunikasi melalui jaringan, sehingga sinkronisasi menjadi tantangan utama.

Arsitektur publish–subscribe menawarkan keunggulan berupa loose coupling antara publisher dan consumer, sehingga meningkatkan skalabilitas dan fleksibilitas sistem. Namun, trade-off yang muncul adalah meningkatnya kompleksitas dalam menjaga konsistensi data, terutama terkait duplikasi pesan dan ordering event. Oleh karena itu, diperlukan mekanisme tambahan seperti idempotency dan deduplication untuk memastikan state sistem tetap benar (Tanenbaum & Van Steen, 2017).

---

## 4. T2 – Pemilihan Arsitektur Publish–Subscribe
Arsitektur publish–subscribe lebih tepat digunakan dibanding client–server ketika sistem membutuhkan komunikasi asinkron dan skalabilitas tinggi. Dalam konteks log aggregator, publisher tidak perlu mengetahui secara langsung consumer mana yang akan memproses event, sehingga sistem menjadi lebih fleksibel dan mudah dikembangkan.

Selain itu, pub-sub memungkinkan penambahan consumer baru tanpa perlu mengubah logika publisher. Hal ini sangat sesuai untuk sistem monitoring dan logging yang cenderung berkembang seiring waktu (Coulouris et al., 2012).

---

## 5. T3 – At-least-once vs Exactly-once Delivery
Exactly-once delivery merupakan konsep ideal namun sulit diwujudkan dalam sistem terdistribusi nyata karena adanya kegagalan jaringan dan crash komponen. Oleh sebab itu, sistem ini menerapkan at-least-once delivery, di mana event dapat dikirim atau diproses lebih dari satu kali.

Untuk mengatasi efek samping dari duplikasi tersebut, digunakan konsep **idempotent consumer**, yaitu consumer yang mampu memproses event yang sama berulang kali tanpa menghasilkan perubahan state ganda. Pendekatan ini secara praktis memberikan hasil akhir yang setara dengan exactly-once delivery.

---

## 6. T4 – Skema Penamaan Topic dan Event ID
Setiap event dalam sistem diidentifikasi secara unik menggunakan kombinasi `(topic, event_id)`. Topic merepresentasikan kategori atau sumber log, sedangkan event_id menggunakan UUID yang bersifat collision-resistant.

Skema ini memungkinkan proses deduplication dilakukan secara deterministik pada level database dengan menggunakan constraint unik. Dengan demikian, sistem dapat dengan mudah mendeteksi event duplikat tanpa memerlukan penyimpanan state tambahan di memori.

---

## 7. T5 – Ordering Event
Sistem ini tidak menerapkan total ordering global karena tidak menjadi kebutuhan utama dalam konteks log aggregator. Ordering event dilakukan secara praktis menggunakan timestamp ISO 8601 yang dikirim oleh publisher.

Pendekatan ini memiliki keterbatasan, seperti kemungkinan terjadinya clock skew atau out-of-order delivery. Namun, karena tujuan utama sistem adalah agregasi log, keterbatasan tersebut masih dapat ditoleransi.

---

## 8. T6 – Failure Modes dan Strategi Mitigasi
Beberapa failure mode yang mungkin terjadi dalam sistem ini antara lain crash pada consumer, retry pengiriman event oleh publisher, serta duplikasi pesan akibat kegagalan jaringan. Untuk mengatasi hal tersebut, sistem menggunakan Redis Streams dengan consumer group yang mendukung mekanisme pending message dan acknowledgment.

Selain itu, deduplication persisten di database memastikan bahwa event yang sama tidak diproses ulang meskipun terjadi restart container atau retry.

---

## 9. T7 – Eventual Consistency
Sistem menerapkan model **eventual consistency**, di mana state akhir sistem akan menjadi konsisten setelah seluruh event diproses. Idempotency dan deduplication berperan penting dalam menjamin bahwa meskipun terjadi duplikasi event, state sistem tidak akan menyimpang dari kondisi yang diharapkan (Coulouris et al., 2012).

---

## 10. T8 – Desain Transaksi (Fokus Bab 8)
### 10.1 Keputusan Desain
Setiap event diproses dalam satu transaksi database yang mencakup:
1) deduplication (penandaan event pernah diproses),  
2) penyimpanan event unik ke tabel `events`, dan  
3) pembaruan metrik pada tabel `stats`.

### 10.2 Alasan dan Trade-off
Pada sistem pub-sub dengan model at-least-once, event dapat terkirim ulang (retry) atau terbaca ulang setelah crash. Tanpa transaksi, sistem rentan menghasilkan state parsial (misalnya event tersimpan tetapi stats tidak ter-update, atau sebaliknya). Dengan transaksi, sistem memperoleh atomicity dan consistency: perubahan state hanya terjadi bila seluruh rangkaian pemrosesan sukses.

### 10.3 Mekanisme Teknis
Transaksi database dilakukan pada consumer. Dedup dilakukan terlebih dahulu menggunakan tabel `processed_events` yang memiliki primary key `(topic, event_id)` dan operasi:
- `INSERT ... ON CONFLICT DO NOTHING`  
Jika insert berhasil (unik), event disimpan ke `events` dan stats dinaikkan sebagai unique. Jika insert gagal (duplikat), stats dinaikkan sebagai duplicate.

### 10.4 Bukti Pengujian
Keputusan desain transaksi dan konsistensi metrik didukung oleh pengujian:
- `tests/test_dedup_idempotency.py::test_stats_invariant_received_ge_sum`  
  Memastikan invariant statistik: `received >= unique_processed + duplicate_dropped`.

---

## 11. T9 – Kontrol Konkurensi (Fokus Bab 9)
### 11.1 Keputusan Desain
Kontrol konkurensi diimplementasikan menggunakan:
- constraint unik pada tabel dedup (`processed_events`), dan
- operasi `INSERT ... ON CONFLICT DO NOTHING` di dalam transaksi.

### 11.2 Alasan dan Trade-off
Dengan multi-worker consumer (`CONSUMER_WORKERS > 1`), dua worker dapat membaca event yang sama hampir bersamaan (race condition). Jika dedup dilakukan di memori, akan ada risiko double-processing saat restart atau bila worker berbeda. Dengan dedup di database, sistem memperoleh *single source of truth* yang persisten dan aman konkurensi.

### 11.3 Mekanisme Teknis (Atomic Dedup)
Dedup dilakukan secara atomik pada database melalui unique constraint sehingga hanya satu worker yang dapat “mengklaim” `(topic, event_id)` sebagai unik. Worker lain akan mendapatkan konflik dan diperlakukan sebagai duplikat, sehingga tidak menyimpan event kedua kali.

Kalimat kunci:
> Dedup dilakukan secara atomik di tingkat database menggunakan constraint unik dan transaksi, sehingga race condition tidak menghasilkan double-processing walaupun multi-worker.

### 11.4 Bukti Pengujian Konkurensi
Keamanan terhadap race condition dibuktikan melalui pengujian:
- `tests/test_concurrency.py::test_parallel_duplicate_still_one`  
  Duplikasi paralel tetap menghasilkan 1 event unik.
- `tests/test_concurrency.py::test_parallel_unique_count_increases`  
  Event paralel yang berbeda menaikkan unique count sesuai jumlah event unik.

---

## 12. T10 – Orkestrasi, Keamanan, dan Persistensi
Docker Compose digunakan sebagai alat orkestrasi untuk menjalankan seluruh layanan dalam satu jaringan lokal. Pendekatan ini meningkatkan keamanan karena tidak ada layanan yang diekspos ke jaringan publik selain endpoint API untuk keperluan demo.

Data disimpan menggunakan named volume PostgreSQL (`pg_data`), sehingga tetap persisten meskipun container dihentikan atau dihapus. Selain itu, Redis juga menggunakan named volume (`redis_data`) untuk menjaga state stream/consumer group pada skenario tertentu saat demo.

### 12.1 Bukti Persistensi (Restart/Recreate)
Persistensi dibuktikan dengan:
1) recreate container aggregator tanpa menghapus volume database, dan  
2) memverifikasi data event dan metrik masih tersedia melalui endpoint `/events` dan `/stats`.

Pengujian terkait persistensi tersedia pada:
- `tests/test_persistence_restart.py::test_persistence_after_recreate`  
  (Dapat dijalankan pada environment yang mengaktifkan docker-in-docker / `RUN_DOCKER=1` sesuai konfigurasi test.)

---

## 13. Evaluasi dan Pengujian
Sistem diuji menggunakan unit dan integration tests sebanyak 14 test yang mencakup validasi skema event, deduplication, konkurensi, dan persistensi.

### 13.1 Ringkasan Test yang Mendukung Keputusan Desain
Berikut pemetaan keputusan desain terhadap bukti pengujian:

| Aspek | Keputusan Desain | Bukti Pengujian (pytest) |
|---|---|---|
| Validasi API | Request schema harus valid (topic, event_id, timestamp, dsb.) | `tests/test_api_validation.py::*` |
| Dedup & Idempotency | Dedup persisten di DB via `(topic,event_id)` + `ON CONFLICT DO NOTHING` | `test_dedup_same_event_only_one_in_events`, `test_dedup_across_batches` |
| Konkurensi | Multi-worker aman race condition (atomic dedup di DB) | `test_parallel_duplicate_still_one`, `test_parallel_unique_count_increases` |
| Statistik & Observability | Invariant stats konsisten | `test_stats_invariant_received_ge_sum`, `test_get_stats_has_keys` |
| Persistensi | Data tidak hilang saat recreate container | `test_persistence_after_recreate` *(opsional tergantung env)* |

### 13.2 Pengujian Beban
Selain test otomatis, dilakukan pengujian beban menggunakan publisher simulator untuk memproses lebih dari 20.000 event dengan tingkat duplikasi di atas 30%. Hasil pengujian menunjukkan bahwa sistem mampu mempertahankan konsistensi data dan tetap responsif di bawah beban paralel.

---

## 14. Kesimpulan
Berdasarkan hasil implementasi dan pengujian, dapat disimpulkan bahwa sistem Pub-Sub Log Aggregator yang dibangun telah berhasil memenuhi tujuan pembelajaran mata kuliah Sistem Terdistribusi. Penerapan idempotent consumer, deduplication persisten, serta transaksi dan kontrol konkurensi terbukti efektif dalam menjaga konsistensi sistem pada kondisi retry, duplikasi, dan pemrosesan paralel.

---

## Daftar Pustaka (APA 7th)

Coulouris, G., Dollimore, J., Kindberg, T., & Blair, G. (2012). *Distributed systems: Concepts and design* (5th ed.). Addison-Wesley.

Tanenbaum, A. S., & Van Steen, M. (2017). *Distributed systems: Principles and paradigms* (2nd ed.). Pearson Education.
