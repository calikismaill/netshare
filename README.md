# 📡 NetShare Pro — Modern & Minimalist WiFi Hotspot Manager

![Python](https://img.shields.io/badge/Python-3.8%2B-blue.svg)
![GTK3](https://img.shields.io/badge/GUI-GTK3-green.svg)
![Linux](https://img.shields.io/badge/Platform-Linux-orange.svg)
![License](https://img.shields.io/badge/License-MIT-purple.svg)

**NetShare Pro**, Linux sistemlerinde (`create_ap` backend servisini kullanarak) saniyeler içinde güçlü, güvenli ve modern bir WiFi Hotspot (Erişim Noktası) oluşturmanızı sağlayan hafif ve performanslı bir masaüstü uygulamasıdır.

---

## 🌟 Özellikler

- **🎨 Modern & Minimalist Arayüz**: Sabit `Gtk.Stack` sekmeli düzeni ile pencere zıplaması veya kayma yapmayan temiz görünüm.
- **⚡ Anında & Donmasız İşlem**: Arka plan thread mimarisi ve parolasız `sudo -n` entegrasyonu sayesinde donma veya gecikme yaşanmaz.
- **📱 Bağlı Cihaz Yönetimi**: Hotspot'a bağlanan cihazların Adı (Hostname), IP adresi ve MAC adresini tek tıkla panoya kopyalayabilme.
- **📱 Canlı QR Kod Üretici & İndirme**: Şifre yazmadan doğrudan bağlanmak için anlık QR kod üretimi ve **PNG/SVG** formatlarında bilgisayara kaydedebilme.
- **🟢🔴 Sistem Tepsisi (System Tray)**:
  - Duruma göre renk değiştiren ikon (Yayında: Yeşil, Kapalı: Kırmızı).
  - Pencere küçültüldüğünde alt görev çubuğundan tamamen kalkıp tepside bekleme.
  - Uygulamadan çıkış yapıldığında hotspot yayınını otomatik sonlandırma seçeneği.
- **📻 Gelişmiş Ağ Yapılandırması**:
  - Frekans Bandı Seçimi: `Otomatik (Auto)`, `2.4 GHz`, `5 GHz`.
  - Şifreli (WPA2) veya Açık Ağ (Şifresiz) seçeneği.
  - Şifre Göster/Gizle göz ikonu.
  - Gizli SSID (`--hidden`), Cihaz İzolasyonu (`--isolate-clients`), Sanal Arayüz Devre Dışı (`--no-virt`).
  - 802.11n, 802.11ac, 802.11ax standart desteği.
  - Özel Gateway IP ve MAC Adresi tanımlama.

---

## 📋 Bağımlılıklar (Requirements)

Uygulamanın çalışabilmesi için aşağıdaki paketlerin sisteminizde yüklü olması gerekir:

- `python3` & `python-gobject` (`python3-gi`)
- `linux-wifi-hotspot` (veya `create_ap`)
- `qrencode`
- `libayatana-appindicator3`

### 📦 Dağıtımlara Göre Paket Kurulumu:

#### Arch Linux / Manjaro:
```bash
sudo pacman -S qrencode linux-wifi-hotspot python-gobject
```

#### Ubuntu / Debian / Pop!_OS:
```bash
sudo apt update
sudo apt install qrencode linux-wifi-hotspot python3-gi gir1.2-ayatanaappindicator3-0.1
```

---

## 🚀 Hızlı Kurulum

Projeyi klonlayıp otomatik kurulum betiğini çalıştırabilirsiniz:

```bash
git clone https://github.com/KULLANICI_ADINIZ/netshare.git
cd netshare
chmod +x install.sh
./install.sh
```

Kurulum tamamlandıktan sonra terminalden `netshare` yazarak veya uygulama menünüzden **NetShare Pro** ikonuna tıklayarak uygulamayı başlatabilirsiniz.

---

## 🗑️ Kaldırma (Uninstall)

Uygulamayı sisteminizden kaldırmak için:

```bash
./uninstall.sh
```

---

## 📄 Lisans

Bu proje **MIT Lisansı** altında lisanslanmıştır. Detaylar için [LICENSE](LICENSE) dosyasına göz atabilirsiniz.
