#!/data/data/com.termux/files/usr/bin/bash
# Instala o robo de respostas do @quebra.cuca.diario no Termux.
# Uso: curl -fsSL https://raw.githubusercontent.com/gustavoventuri/instagram_desafio_cuca_diario/main/celular/instalar.sh | bash
set -e
RAW=https://raw.githubusercontent.com/gustavoventuri/instagram_desafio_cuca_diario/main/celular
DEST=$HOME/quebracuca
mkdir -p "$DEST"
for f in responder.js laco.sh .env.example; do curl -fsSL "$RAW/$f" -o "$DEST/$f"; done
chmod +x "$DEST/laco.sh"
[ -f "$DEST/.env" ] || cp "$DEST/.env.example" "$DEST/.env"
command -v node >/dev/null || pkg install -y nodejs
command -v tmux >/dev/null || pkg install -y tmux

# inicia junto com o celular (Termux:Boot), sem mexer no Skippy
mkdir -p "$HOME/.termux/boot"
cat > "$HOME/.termux/boot/quebracuca.sh" <<'BOOT'
#!/data/data/com.termux/files/usr/bin/bash
termux-wake-lock
sleep 30
tmux has-session -t quebracuca 2>/dev/null || tmux new-session -d -s quebracuca "$HOME/quebracuca/laco.sh"
BOOT
chmod +x "$HOME/.termux/boot/quebracuca.sh"

echo
echo "Instalado em $DEST"
echo "1) Edite o token:   nano $DEST/.env"
echo "2) Teste agora:     cd $DEST && node responder.js --agora"
echo "3) Ligue o robo:    tmux new-session -d -s quebracuca $DEST/laco.sh"
