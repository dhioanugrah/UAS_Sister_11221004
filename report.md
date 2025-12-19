
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
Setiap event diproses dalam satu transaksi database yang mencakup proses pencatatan statistik, deduplication, dan penyimpanan event. Transaksi ini memastikan prinsip **ACID**, khususnya atomicity dan consistency.

Dengan menggunakan transaksi, sistem dapat mencegah terjadinya lost update dan memastikan bahwa perubahan state hanya terjadi jika seluruh langkah pemrosesan event berhasil dijalankan.

---

## 11. T9 – Kontrol Konkurensi (Fokus Bab 9)
Kontrol konkurensi diimplementasikan menggunakan primary key unik pada tabel deduplication dan perintah `INSERT ... ON CONFLICT DO NOTHING`. Pendekatan ini memastikan bahwa hanya satu worker yang berhasil memproses event unik, meskipun beberapa worker mencoba memproses event yang sama secara paralel.

Isolation level yang digunakan adalah READ COMMITTED, yang dianggap cukup untuk kebutuhan sistem ini karena potensi race condition telah dimitigasi melalui constraint unik dan operasi upsert.

---

## 12. T10 – Orkestrasi, Keamanan, dan Persistensi
Docker Compose digunakan sebagai alat orkestrasi untuk menjalankan seluruh layanan dalam satu jaringan lokal. Pendekatan ini meningkatkan keamanan karena tidak ada layanan yang diekspos ke jaringan publik selain endpoint API untuk keperluan demo.

Data disimpan menggunakan named volume PostgreSQL, sehingga tetap persisten meskipun container dihentikan atau dihapus.

---

## 13. Evaluasi dan Pengujian
Sistem diuji menggunakan unit dan integration tests sebanyak 14 test yang mencakup validasi skema event, deduplication, konkurensi, dan persistensi. Selain itu, dilakukan pengujian beban menggunakan publisher simulator untuk memproses lebih dari 20.000 event dengan tingkat duplikasi di atas 30%.

Hasil pengujian menunjukkan bahwa sistem mampu mempertahankan konsistensi data dan tetap responsif di bawah beban paralel.

---

## 14. Kesimpulan
Berdasarkan hasil implementasi dan pengujian, dapat disimpulkan bahwa sistem Pub-Sub Log Aggregator yang dibangun telah berhasil memenuhi tujuan pembelajaran mata kuliah Sistem Terdistribusi. Penerapan idempotent consumer, deduplication persisten, serta transaksi dan kontrol konkurensi terbukti efektif dalam menjaga konsistensi sistem.

---

## Daftar Pustaka (APA 7th)

Coulouris, G., Dollimore, J., Kindberg, T., & Blair, G. (2012). *Distributed systems: Concepts and design* (5th ed.). Addison-Wesley.

Tanenbaum, A. S., & Van Steen, M. (2017). *Distributed systems: Principles and paradigms* (2nd ed.). Pearson Education.
