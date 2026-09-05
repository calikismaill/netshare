#!/usr/bin/env bash
#
# NetShare Pro — Uninstaller
#

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m'

echo -e "${RED}NetShare Pro Kaldırılıyor...${NC}"

rm -rf "$HOME/.local/share/netshare"
rm -f "$HOME/.local/bin/netshare"
rm -f "$HOME/.local/share/applications/netshare.desktop"

if [ -f "/etc/sudoers.d/netshare" ]; then
    echo "Sudoers iznini kaldırmak için şifreniz istenebilir:"
    sudo rm -f "/etc/sudoers.d/netshare"
fi

echo -e "${GREEN}NetShare Pro başarıyla kaldırıldı.${NC}"
