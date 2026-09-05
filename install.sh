#!/usr/bin/env bash
#
# NetShare Pro — Standalone Installer
#

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}===========================================${NC}"
echo -e "${BLUE}    NetShare Pro Bağımsız Kurulum Sihirbazı${NC}"
echo -e "${BLUE}===========================================${NC}"

INSTALL_DIR="$HOME/.local/share/netshare"
BIN_DIR="$HOME/.local/bin"
DESKTOP_DIR="$HOME/.local/share/applications"

# 1. Klasörleri Oluştur
mkdir -p "$INSTALL_DIR" "$BIN_DIR" "$DESKTOP_DIR"

# 2. Temel Sistem Bağımlılıkları Kontrolü
echo -e "\n${GREEN}[1/5] Sistem bağımlılıkları kontrol ediliyor...${NC}"

missing_deps=()
command -v python3 >/dev/null 2>&1 || missing_deps+=("python3")
command -v hostapd >/dev/null 2>&1 || missing_deps+=("hostapd")
command -v dnsmasq >/dev/null 2>&1 || missing_deps+=("dnsmasq")
command -v iptables >/dev/null 2>&1 || missing_deps+=("iptables")
command -v qrencode >/dev/null 2>&1 || missing_deps+=("qrencode")

if [ ${#missing_deps[@]} -ne 0 ]; then
    echo -e "${RED}Eksik temel paketler tespit edildi:${NC}"
    for dep in "${missing_deps[@]}"; do
        echo -e "  - $dep"
    done
    echo -e "\nLütfen sisteminiz için resmi depolardan paketleri yükleyin:"
    echo -e "  Arch Linux: sudo pacman -S hostapd dnsmasq iptables qrencode python-gobject"
    echo -e "  Ubuntu/Debian: sudo apt install hostapd dnsmasq iptables qrencode python3-gi gir1.2-ayatanaappindicator3-0.1"
    exit 1
fi

# 3. Arka Plan Motorunu (create_ap) Sisteme Kur
echo -e "${GREEN}[2/5] Standalone Hotspot Motoru (create_ap) kuruluyor...${NC}"
if [ ! -f /usr/bin/create_ap ] && [ ! -f /usr/local/bin/create_ap ]; then
    echo "create_ap motoru kuruluyor (sudo şifreniz istenebilir)..."
    sudo cp -f src/backend/create_ap /usr/local/bin/create_ap
    sudo chmod +x /usr/local/bin/create_ap
    sudo cp -f src/backend/create_ap.service /etc/systemd/system/create_ap.service
    sudo systemctl daemon-reload
    echo -e "${GREEN}✓ create_ap motoru ve systemd servisi kuruldu.${NC}"
else
    echo -e "${GREEN}✓ Hotspot motoru sisteminizde zaten mevcut.${NC}"
fi

# 4. Uygulama Dosyalarını Kopyala
echo -e "${GREEN}[3/5] NetShare Pro dosyaları kopyalanıyor...${NC}"
cp -f src/netshare.py "$INSTALL_DIR/netshare.py"
chmod +x "$INSTALL_DIR/netshare.py"

if [ -f assets/netshare-icon.svg ]; then
    cp -f assets/netshare-icon.svg "$INSTALL_DIR/netshare-icon.svg"
fi

ln -sf "$INSTALL_DIR/netshare.py" "$BIN_DIR/netshare"

# 5. Masaüstü Kısayolu
echo -e "${GREEN}[4/5] Masaüstü kısayolu oluşturuluyor...${NC}"
cat <<EOF > "$DESKTOP_DIR/netshare.desktop"
[Desktop Entry]
Name=NetShare Pro
Comment=WiFi Hotspot Manager
GenericName=WiFi Hotspot
Exec=python3 $INSTALL_DIR/netshare.py
Icon=$INSTALL_DIR/netshare-icon.svg
Terminal=false
Type=Application
Categories=Network;System;
Keywords=wifi;hotspot;access point;network;share;
StartupNotify=true
StartupWMClass=com.netshare.hotspot
EOF

chmod +x "$DESKTOP_DIR/netshare.desktop"

# 6. Sudoers İznini Yapılandır
echo -e "${GREEN}[5/5] Sudoers servis izinleri yapılandırılıyor...${NC}"
SUDOERS_FILE="/etc/sudoers.d/netshare"
SUDOERS_RULE="$USER ALL=(ALL) NOPASSWD: /usr/bin/systemctl * create_ap, /usr/bin/tee /etc/create_ap.conf, /usr/bin/create_ap *, /usr/local/bin/create_ap *"

if [ ! -f "$SUDOERS_FILE" ]; then
    echo "Parolasız servis başlatma izni eklendi:"
    echo "$SUDOERS_RULE" | sudo tee "$SUDOERS_FILE" >/dev/null
    sudo chmod 0440 "$SUDOERS_FILE"
    echo -e "${GREEN}✓ Sudoers izni tamamlandı.${NC}"
else
    echo -e "${GREEN}✓ Sudoers izni zaten mevcut.${NC}"
fi

echo -e "\n${GREEN}===========================================${NC}"
echo -e "${GREEN}  NetShare Pro %100 Bağımsız Olarak Kuruldu!  ${NC}"
echo -e "${GREEN}===========================================${NC}"
echo -e "Artık wihotspot veya harici GUI paketlerine ihtiyacınız yoktur."
echo -e "Uygulamayı çalıştırmak için:"
echo -e "  - Terminalden: ${BLUE}netshare${NC}"
echo -e "  - Veya uygulama menünüzden NetShare Pro'yu aratabilirsiniz."
EOF
