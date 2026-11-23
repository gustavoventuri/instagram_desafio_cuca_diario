#!/data/data/com.termux/files/usr/bin/bash
# Roda o robo de respostas a cada 10 minutos (o script decide pela agenda).
cd "$(dirname "$0")"
while true; do
  node disparar.js >> saida.log 2>&1
  node responder.js >> saida.log 2>&1
  tail -n 2000 saida.log > saida.tmp && mv saida.tmp saida.log
  sleep 600
done
