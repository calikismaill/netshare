#!/usr/bin/env bash
#
# NetShare Pro — Automated Installer
#

set -e

RED='\030[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}===========================================${NC}"
echo -e "${BLUE}       NetShare Pro Kurulum Sihirbazı      ${NC}"
echo -e "${BLUE}===========================================${NC}"

INSTALL_DIR="$HOME/.local/share/netshare"
BIN_DIR="$HOME/.local/bin"
DESKTOP_DIR="$HOME/.local/share/applications"

# 1. Klasörleri Oluştur
mkdir -p "$INSTALL_DIR" "$BIN_DIR" "$DESKTOP_DIR"

# 2. Bağımlılık Kontrolü
echo -e "\n${GREEN}[1/4] Bağımlılıklar kontrol ediliyor...${NC}"

missing_deps=()
command -v python3 >/dev/null 2>&1 || missing_deps+=("python3")
command -v create_ap >/dev/null 2>&1 || missing_deps+=("linux-wifi-hotspot (create_ap)")
command -v qrencode >/dev/null 2>&1 || missing_deps+=("qrencode")

if [ ${#missing_deps[@]} -ne 0 ]; then
    echo -e "${RED}Eksik bağımlılıklar tespit edildi:${NC}"
    for dep in "${missing_deps[@]}"; do
        echo -e "  - $dep"
    done
    echo -e "\nLütfen sisteminiz için gerekli paketleri yükleyin:"
    echo -e "  Arch Linux: sudo pacman -S qrencode linux-wifi-hotspot python-gobject"
    echo -e "  Ubuntu/Debian: sudo apt install qrencode linux-wifi-hotspot python3-gi gir1.2-ayatanaappindicator3-0.1"
    exit 1
fi

# 3. Uygulama Dosyalarını Kopyala
echo -e "${GREEN}[2/4] Dosyalar kopyalanıyor...${NC}"
cp -f src/netshare.py "$INSTALL_DIR/netshare.py"
chmod +x "$INSTALL_DIR/netshare.py"

if [ -f assets/netshare-icon.svg ]; then
    cp -f assets/netshare-icon.svg "$INSTALL_DIR/netshare-icon.svg"
fi

# Bin sembolik bağıntı oluştur
ln -sf "$INSTALL_DIR/netshare.py" "$BIN_DIR/netshare"

# 4. Desktop Başlatıcısını Oluştur
echo -e "${GREEN}[3/4] Masaüstü kısayolu oluşturuluyor...${NC}"
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

# 5. Sudoers İzni (create_ap servisinin şifresiz çalışabilmesi için)
echo -e "${GREEN}[4/4] Servis izinleri yapılandırılıyor (Sudoers)...${NC}"
SUDOERS_FILE="/etc/sudoers.d/netshare"
SUDOERS_RULE="$USER ALL=(ALL) NOPASSWD: /usr/bin/systemctl * create_ap, /usr/bin/tee /etc/create_ap.conf, /usr/bin/create_ap *"

if [ ! -f "$SUDOERS_FILE" ]; then
    echo "Parolasız servis başlatma izni vermek için sudo şifreniz istenebilir:"
    echo "$SUDOERS_RULE" | sudo tee "$SUDOERS_FILE" >/dev/null
    sudo chmod 0440 "$SUDOERS_FILE"
    echo -e "${GREEN}✓ Sudoers kuralı başarıyla eklendi.${NC}"
else
    echo -e "${GREEN}✓ Sudoers kuralı zaten mevcut.${NC}"
fi

echo -e "\n${GREEN}===========================================${NC}"
echo -e "${GREEN}  NetShare Pro Kurulumu Başarıyla Tamamlandı! ${NC}"
echo -e "${GREEN}===========================================${NC}"
echo -e "Uygulamayı çalıştırmak için:"
echo -e "  - Terminalden: ${BLUE}netshare${NC}"
echo -e "  - Veya uygulama menünüzden NetShare Pro'yu aratabilirsiniz."
EOF
