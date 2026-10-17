#!/usr/bin/env bash
set -Eeuo pipefail

command="${1:-train}"
if (($# > 0)); then
  shift
fi

case "$command" in
  train)
    exec python /app/train.py "$@"
    ;;
  predict)
    exec python /app/predict.py "$@"
    ;;
  status)
    exec python -c 'import torch; print(f"PyTorch: {torch.__version__}"); print(f"CUDA disponible: {torch.cuda.is_available()}"); print("Dispositivo: {}".format(torch.cuda.get_device_name(0) if torch.cuda.is_available() else "CPU"))'
    ;;
  *)
    printf 'Comando desconocido: %s\nUso: train [opciones], predict [opciones] o status\n' "$command" >&2
    exit 2
    ;;
esac
